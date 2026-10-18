"""Public widget API (R6) — unauthenticated, domain-restricted.

These endpoints back the embedded chat experience. They are reachable
without a logged-in user (visitors are anonymous), so every request is
guarded by:
* the widget's **public key** (required; unknown keys are 404),
* the widget's **published** status,
* an optional **domain allow-list** (Origin/Referer must match). This is a
  browser courtesy check only: Origin is client-controlled outside browsers,
  so it is never the authentication control,
* a per-**client IP** and per-widget rate limit (chat-start, chat, stream,
  lead, escalate, event, feedback), so rotating ``visitor_id`` values does not
  bypass throttling, plus the existing per-visitor message limit,
* a per-**visitor session token**: the server issues a random token when a
  visitor session is created and stores only its SHA-256 digest. Transcript,
  escalation and lead-update calls must present it in ``X-Widget-Session``,
* strict **input length** caps.

Answers are produced by the Enterprise RAG engine (R4), grounded in the
widget's knowledge base, and degrade to extractive answers when the AI
provider is offline.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.conversation import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
)
from app.database.models.message import Message, MessageSender
from app.database.models.agent import Agent, AgentStatus
from app.database.models.widget import Widget, WidgetStatus
from app.database.models.widget_event import WidgetEventType
from app.database.models.widget_session import WidgetSession
from app.database.session import get_db
from app.middleware.rate_limit import _client_ip
from app.schemas.widget import (
    WidgetChatRequest,
    WidgetChatResponse,
    WidgetChatSource,
    WidgetEscalateRequest,
    WidgetEventRequest,
    WidgetFeedbackRequest,
    WidgetLeadRequest,
    WidgetOk,
    WidgetPublicConfig,
    WidgetSessionRead,
    WidgetSessionStart,
)
from app.services import assistant_profiles
from app.services import widget_service
from app.services import escalation_service
from app.services import lead_service
from app.services import visitor_service
from app.services.rag_answer import answer_query

public_router = APIRouter(prefix="/api/widget", tags=["widget-public"])

_MAX_CONTEXT_KEYS = {
    "name",
    "email",
    "company",
    "plan",
    "language",
    "url",
    "page_title",
    "userId",
}


# ─────────────────── guards ───────────────────


async def _load_live_widget(
    session: AsyncSession,
    public_key: str,
    *,
    origin: Optional[str],
    referer: Optional[str],
    require_published: bool = True,
) -> Widget:
    """Resolve a live widget by its public key and apply the domain check.

    The public key is required and is the widget identifier. The domain check
    reads Origin/Referer, which only browsers set honestly: any other client
    can forge them. It is kept as a browser-side guard, not as authentication.
    Visitor data is protected by the per-visitor session token instead.
    """
    widget = await widget_service.get_widget_by_key(session, public_key)
    if widget is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Widget not found.")
    if require_published and widget.status != WidgetStatus.published:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Widget is not live.")
    domains = await widget_service.widget_domains(session, widget.id)
    host = widget_service.origin_host(origin, referer)
    if not widget_service.domain_allowed(
        domains, host, require_allow_list=widget_service.domains_required()
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This widget is not authorized for this domain.",
        )
    return widget


def _check_rate(widget: Widget, visitor_id: str) -> None:
    limit = int((widget.settings or {}).get("rate_limit_per_min", 20) or 20)
    if widget_service.rate_limited(
        f"{widget.public_key}:{visitor_id}", limit=limit, window_seconds=60
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many messages — please slow down.",
        )


def _ip_rate_limit_per_min() -> int:
    try:
        return int(os.environ.get("WIDGET_IP_RATE_LIMIT_PER_MIN", "60"))
    except ValueError:
        return 60


def _check_ip_rate(request: Request, widget: Widget, route: str) -> None:
    """Throttle one client IP per widget key and route, independent of visitor_id.

    Visitor ids are client-chosen, so a per-visitor limit alone can be bypassed
    by rotating ids. The client IP honours TRUSTED_PROXY_IPS exactly like the
    global middleware. Call this before any write so rejected requests create
    nothing.
    """
    key = f"ip:{_client_ip(request)}:{widget.public_key}:{route}"
    if widget_service.rate_limited(
        key, limit=max(1, _ip_rate_limit_per_min()), window_seconds=60
    ):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many requests — please slow down.",
        )


# ─────────────────── visitor session tokens ───────────────────

# Header carrying the visitor session token on every public call after start.
SESSION_HEADER = "X-Widget-Session"
_SESSION_DENIED = "A valid widget session token is required."


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _session_token_matches(ws: WidgetSession, presented: Optional[str]) -> bool:
    """True only when the presented token hashes to the visitor's stored digest.

    Rows without a digest (created before the token rollout) never match, so
    legacy visitors fail closed.
    """
    if not ws.session_token_hash or not presented:
        return False
    return hmac.compare_digest(ws.session_token_hash, _hash_session_token(presented))


def _presented_token(request: Request) -> Optional[str]:
    value = request.headers.get(SESSION_HEADER)
    return value.strip() if value and value.strip() else None


def _sanitize_context(ctx: dict) -> dict:
    if not isinstance(ctx, dict):
        return {}
    return {
        k: (str(v)[:300] if v is not None else None)
        for k, v in ctx.items()
        if k in _MAX_CONTEXT_KEYS
    }


def _effective_knowledge_base_ids(
    agent: Optional[Agent], widget: Widget
) -> Optional[list[uuid.UUID]]:
    """Resolve public-widget retrieval scope from agent and widget bindings.

    A public visitor never reaches every knowledge base by default. With no
    binding at all, the widget's own KB is used, or retrieval is empty until the
    owner binds one. Once an agent has an explicit binding, the widget can only
    narrow it. A mismatch or explicit empty binding fails closed as well.
    """
    widget_id = widget.knowledge_base_id
    cfg = agent.config if agent is not None else None
    config = cfg.config if cfg is not None else None
    if not isinstance(config, dict) or "knowledge_base_ids" not in config:
        return [widget_id] if widget_id else []

    raw = config.get("knowledge_base_ids")
    if not isinstance(raw, list):
        return []
    agent_ids: list[uuid.UUID] = []
    for value in raw:
        try:
            agent_ids.append(uuid.UUID(str(value)))
        except (TypeError, ValueError, AttributeError):
            return []

    if not widget_id:
        return agent_ids
    return [widget_id] if widget_id in agent_ids else []


# ─────────────────── config ───────────────────


@public_router.get(
    "/config",
    response_model=WidgetPublicConfig,
    summary="Sanitized loader config (no secrets) by public key",
)
async def widget_config(
    key: str,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetPublicConfig:
    # Config is readable for draft/published so the dashboard can preview;
    # the chat endpoints enforce 'published'. Domain check still applies
    # when an allow-list is present and a published widget is requested.
    widget = await widget_service.get_widget_by_key(session, key)
    if widget is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Widget not found.")
    if widget.status == WidgetStatus.published:
        domains = await widget_service.widget_domains(session, widget.id)
        host = widget_service.origin_host(origin, referer)
        if not widget_service.domain_allowed(
            domains, host, require_allow_list=widget_service.domains_required()
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "This widget is not authorized for this domain.",
            )
    return WidgetPublicConfig(**widget_service.public_config_dict(widget, []))


# ─────────────────── session ───────────────────


async def _find_visitor_session(
    session: AsyncSession, widget: Widget, visitor_id: str
) -> Optional[WidgetSession]:
    return await session.scalar(
        select(WidgetSession)
        .where(WidgetSession.widget_id == widget.id)
        .where(WidgetSession.visitor_id == visitor_id)
        .order_by(WidgetSession.started_at.desc())
        .limit(1)
    )


async def _create_visitor_session(
    session: AsyncSession,
    widget: Widget,
    *,
    visitor_id: str,
    user_context: dict,
    referer: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> tuple[WidgetSession, str]:
    """Create a visitor session and return it with its token (shown once)."""
    token = secrets.token_urlsafe(32)
    ws = WidgetSession(
        widget_id=widget.id,
        organization_id=widget.organization_id,
        visitor_id=visitor_id,
        user_context=_sanitize_context(user_context),
        referer=(referer or "")[:2048] or None,
        user_agent=(user_agent or "")[:512] or None,
        last_active_at=widget_service.now_utc(),
        session_token_hash=_hash_session_token(token),
    )
    session.add(ws)
    await session.flush()
    return ws, token


def _refresh_visitor_session(ws: WidgetSession, user_context: dict) -> None:
    if user_context:
        ws.user_context = {
            **(ws.user_context or {}),
            **_sanitize_context(user_context),
        }
    ws.last_active_at = widget_service.now_utc()


async def _authorized_visitor_session(
    session: AsyncSession, widget: Widget, visitor_id: str, presented: Optional[str]
) -> WidgetSession:
    """Return the visitor's session only when the caller holds its token.

    A missing visitor and a wrong token produce the same response, so the
    endpoint does not reveal which visitor ids exist.
    """
    ws = await _find_visitor_session(session, widget, visitor_id)
    if ws is None or not _session_token_matches(ws, presented):
        raise HTTPException(status.HTTP_403_FORBIDDEN, _SESSION_DENIED)
    return ws


async def _chat_visitor_session(
    session: AsyncSession,
    widget: Widget,
    *,
    visitor_id: str,
    user_context: dict,
    presented: Optional[str],
    referer: Optional[str],
    user_agent: Optional[str],
) -> tuple[WidgetSession, Optional[str]]:
    """Chat entry: a new visitor gets a token; an existing one must present it."""
    ws = await _find_visitor_session(session, widget, visitor_id)
    if ws is None:
        return await _create_visitor_session(
            session,
            widget,
            visitor_id=visitor_id,
            user_context=user_context,
            referer=referer,
            user_agent=user_agent,
        )
    if not _session_token_matches(ws, presented):
        raise HTTPException(status.HTTP_403_FORBIDDEN, _SESSION_DENIED)
    _refresh_visitor_session(ws, user_context)
    return ws, None


@public_router.post(
    "/session",
    response_model=WidgetSessionRead,
    summary="Start or restore a visitor session (persists conversation)",
)
async def start_session(
    payload: WidgetSessionStart,
    request: Request,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetSessionRead:
    widget = await _load_live_widget(
        session, payload.public_key, origin=origin, referer=referer
    )
    _check_ip_rate(request, widget, "session")
    requested_id = (payload.visitor_id or "").strip()[:80]
    existing = (
        await _find_visitor_session(session, widget, requested_id)
        if requested_id
        else None
    )
    session_token: Optional[str] = None
    if existing is not None and _session_token_matches(
        existing, _presented_token(request)
    ):
        # Restore the caller's own visitor: transcript is returned below.
        ws = existing
        _refresh_visitor_session(ws, payload.user_context)
    else:
        # Unknown, legacy, or unauthenticated visitor ids never reveal a
        # transcript; a fresh visitor is started instead.
        visitor_id = (
            requested_id
            if existing is None and requested_id
            else f"v_{uuid.uuid4().hex[:16]}"
        )
        ws, session_token = await _create_visitor_session(
            session,
            widget,
            visitor_id=visitor_id,
            user_context=payload.user_context,
            referer=referer,
            user_agent=request.headers.get("user-agent"),
        )
    await widget_service.log_event(
        session, widget=widget, event=WidgetEventType.loaded, session_id=ws.id
    )

    # Restore prior transcript if a conversation is attached.
    messages: list[dict] = []
    if session_token is None and ws.conversation_id is not None:
        rows = (
            await session.scalars(
                select(Message)
                .where(Message.conversation_id == ws.conversation_id)
                .order_by(Message.created_at.asc())
                .limit(100)
            )
        ).all()
        messages = [
            {
                "role": "assistant" if m.sender == MessageSender.agent else "user",
                "content": m.message,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in rows
            if m.sender in (MessageSender.agent, MessageSender.customer)
        ]

    await session.commit()
    return WidgetSessionRead(
        session_id=ws.id,
        visitor_id=ws.visitor_id,
        conversation_id=ws.conversation_id,
        messages=messages,
        session_token=session_token,
    )


# ─────────────────── chat core ───────────────────

# Shown to visitors when a widget is live but its agent is paused/draft/
# archived. The model is never invoked in this case.
_AGENT_UNAVAILABLE_MESSAGE = (
    "This AI assistant is temporarily unavailable. Please check back soon."
)


async def _persist_and_answer(
    session: AsyncSession,
    widget: Widget,
    ws: WidgetSession,
    text: str,
) -> dict:
    """Persist the user message, run RAG, persist the answer. Returns payload."""
    agent_id = await widget_service.resolve_agent_id(session, widget)

    # Cloud-service behaviour: a widget can stay published while its agent is
    # paused. In that case reply with a friendly notice and never call the
    # model.
    agent_persona: Optional[str] = None
    agent_model: Optional[str] = None
    agent_profile: Optional[str] = None
    agent_contact: Optional[str] = None
    agent_row: Optional[Agent] = None
    if agent_id is not None:
        agent_row = await session.scalar(
            select(Agent)
            .options(selectinload(Agent.config))
            .where(Agent.id == agent_id)
        )
        if agent_row is not None:
            if agent_row.status != AgentStatus.active:
                return {
                    "answer": _AGENT_UNAVAILABLE_MESSAGE,
                    "sources": [],
                    "confidence": 0.0,
                    "related_questions": [],
                    "grounded": False,
                    "generated": False,
                    "conversation_id": ws.conversation_id,
                    "message_id": None,
                }
            cfg = agent_row.config
            agent_persona = cfg.system_prompt if cfg else None
            agent_model = agent_row.model
            cfg_extras = cfg.config if cfg else None
            agent_profile = assistant_profiles.resolve_profile(cfg_extras, "chat")
            agent_contact = assistant_profiles.contact_hint(cfg_extras)

    conversation: Optional[Conversation] = None
    conversation_is_new = False
    if agent_id is not None:
        if ws.conversation_id is not None:
            conversation = await session.get(Conversation, ws.conversation_id)
        if conversation is None:
            conversation = Conversation(
                organization_id=widget.organization_id,
                project_id=widget.project_id,
                agent_id=agent_id,
                channel=ConversationChannel.chat,
                status=ConversationStatus.active,
                title=(text[:60] or "Widget chat"),
                started_at=widget_service.now_utc(),
                customer_name=(ws.user_context or {}).get("name"),
                customer_email=(ws.user_context or {}).get("email"),
                extra={"source": "widget", "widget_id": str(widget.id)},
            )
            session.add(conversation)
            await session.flush()
            ws.conversation_id = conversation.id
            conversation_is_new = True

    # Unified cross-channel identity: recognise this visitor, fold in any
    # new identity/context, and prime the answer with what we already know.
    from app.services.project_scope import resolve_project_id

    project_id = await resolve_project_id(
        session, widget.organization_id, widget.project_id
    )
    digest: Optional[str] = None
    profile = None
    if conversation is not None:
        ctx = ws.user_context or {}
        profile = await visitor_service.upsert_profile(
            session,
            organization_id=widget.organization_id,
            project_id=project_id,
            # Namespaced by widget: the same visitor id on two widgets is two visitors.
            visitor_key=f"{widget.id}:{ws.visitor_id}",
            channel="chat",
            name=ctx.get("name"),
            email=ctx.get("email"),
            phone=ctx.get("phone"),
            context=ctx,
        )
        visitor_service.link_conversation(profile, conversation, channel="chat")
        digest = visitor_service.build_memory_digest(profile, current_channel="chat")

    user_msg: Optional[Message] = None
    if conversation is not None:
        user_msg = Message(
            conversation_id=conversation.id,
            sender=MessageSender.customer,
            message=text,
        )
        session.add(user_msg)

    # Every visitor who starts a conversation becomes a lead — even one "just
    # checking" with no contact details — so the whole thread is captured in the
    # CRM. Only on the first message; a later lead-form submit enriches it.
    if conversation is not None and conversation_is_new:
        ctx = ws.user_context or {}
        await lead_service.upsert_conversation_lead(
            session,
            organization_id=widget.organization_id,
            project_id=widget.project_id,
            conversation_id=conversation.id,
            agent_id=agent_id,
            widget_id=widget.id,
            name=ctx.get("name"),
            email=ctx.get("email"),
            phone=ctx.get("phone"),
            intent=(text or "")[:255] or None,
            message=text,
            source="chat",
        )

    kb_ids = _effective_knowledge_base_ids(agent_row, widget)
    result = await answer_query(
        session,
        text,
        widget.organization_id,
        project_id=project_id,
        knowledge_base_ids=kb_ids,
        top_k=5,
        extra_context=digest,
        persona=agent_persona,
        model=agent_model,
        assistant_profile=agent_profile,
        business_contact=agent_contact,
    )
    handoff = bool(result.get("handoff"))
    if handoff:
        # Promise follow-up only when the visitor left a way to be reached.
        ctx_contact = ws.user_context or {}
        result["answer"] = escalation_service.handoff_reply(
            result.get("answer", ""),
            contact_known=escalation_service.has_contact(
                ctx_contact.get("email"), ctx_contact.get("phone")
            ),
        )

    # False when the reply is a fallback (no model produced it). Carried to the response and metadata.
    generated = bool(result.get("generated", False))
    answer_msg: Optional[Message] = None
    if conversation is not None:
        answer_msg = Message(
            conversation_id=conversation.id,
            sender=MessageSender.agent,
            message=result["answer"],
            metadata_={
                "grounded": result.get("grounded"),
                "confidence": result.get("confidence"),
                "model": result.get("model"),
                "generated": generated,
                "handoff": handoff,
            },
        )
        session.add(answer_msg)
        conversation.last_message_at = widget_service.now_utc()
        if handoff:
            # No supporting passage: the question goes to the team as a lead note.
            ctx = ws.user_context or {}
            await lead_service.upsert_conversation_lead(
                session,
                organization_id=widget.organization_id,
                project_id=widget.project_id,
                conversation_id=conversation.id,
                agent_id=agent_id,
                widget_id=widget.id,
                name=ctx.get("name"),
                email=ctx.get("email"),
                phone=ctx.get("phone"),
                intent=(text or "")[:255] or None,
                message=text,
                source="chat",
            )
            await escalation_service.create_escalation(
                session,
                organization_id=widget.organization_id,
                project_id=project_id,
                channel="chat",
                question=text or "",
                conversation_id=conversation.id,
                name=ctx.get("name"),
                email=ctx.get("email"),
                phone=ctx.get("phone"),
            )

    if profile is not None:
        visitor_service.append_memory(profile, channel="chat", role="user", text=text)
        visitor_service.append_memory(
            profile, channel="chat", role="assistant", text=result.get("answer", "")
        )

    ws.message_count = (ws.message_count or 0) + 1
    ws.last_active_at = widget_service.now_utc()

    await widget_service.log_event(
        session,
        widget=widget,
        event=WidgetEventType.message,
        session_id=ws.id,
        metadata={"q": text[:200]},
    )
    await widget_service.log_event(
        session,
        widget=widget,
        event=WidgetEventType.answer,
        session_id=ws.id,
        metadata={
            "grounded": result.get("grounded"),
            "confidence": result.get("confidence"),
        },
    )

    sources = [
        WidgetChatSource(
            type=s.get("type", "document"),
            title=s.get("title") or s.get("document"),
            url=s.get("url"),
            page=s.get("page"),
            score=s.get("score"),
        ).model_dump()
        for s in (result.get("sources") or [])
    ]

    await session.flush()
    return {
        "answer": result["answer"],
        "sources": sources,
        "confidence": result.get("confidence", 0.0),
        "related_questions": result.get("related_questions", []),
        "grounded": result.get("grounded", False),
        "generated": generated,
        "conversation_id": ws.conversation_id,
        "message_id": answer_msg.id if answer_msg is not None else None,
    }


@public_router.post(
    "/chat",
    response_model=WidgetChatResponse,
    summary="Send a message; get a grounded AI answer",
)
async def widget_chat(
    payload: WidgetChatRequest,
    request: Request,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetChatResponse:
    widget = await _load_live_widget(
        session, payload.public_key, origin=origin, referer=referer
    )
    _check_ip_rate(request, widget, "chat")
    _check_rate(widget, payload.visitor_id)
    text = payload.message.strip()
    if not text:
        raise HTTPException(422, "Message is empty.")

    ws, session_token = await _chat_visitor_session(
        session,
        widget,
        visitor_id=payload.visitor_id,
        user_context=payload.user_context,
        presented=_presented_token(request),
        referer=referer,
        user_agent=request.headers.get("user-agent"),
    )
    out = await _persist_and_answer(session, widget, ws, text)
    await session.commit()
    return WidgetChatResponse(
        answer=out["answer"],
        sources=[WidgetChatSource(**s) for s in out["sources"]],
        confidence=out["confidence"],
        related_questions=out["related_questions"],
        grounded=out["grounded"],
        generated=out.get("generated", False),
        session_id=ws.id,
        conversation_id=out["conversation_id"],
        message_id=out["message_id"],
        session_token=session_token,
    )


@public_router.post(
    "/stream",
    summary="Send a message; stream the grounded AI answer over SSE",
)
async def widget_stream(
    payload: WidgetChatRequest,
    request: Request,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
):
    widget = await _load_live_widget(
        session, payload.public_key, origin=origin, referer=referer
    )
    _check_ip_rate(request, widget, "stream")
    _check_rate(widget, payload.visitor_id)
    text = payload.message.strip()
    if not text:
        raise HTTPException(422, "Message is empty.")

    ws, session_token = await _chat_visitor_session(
        session,
        widget,
        visitor_id=payload.visitor_id,
        user_context=payload.user_context,
        presented=_presented_token(request),
        referer=referer,
        user_agent=request.headers.get("user-agent"),
    )
    out = await _persist_and_answer(session, widget, ws, text)
    await session.commit()

    async def event_stream():
        # Emit a 'meta' frame, then the answer in word chunks, then 'done'.
        # The session token is included only when this request created the session.
        meta = {"type": "meta", "session_id": str(ws.id)}
        if session_token is not None:
            meta["session_token"] = session_token
        yield f"data: {json.dumps(meta)}\n\n"
        words = out["answer"].split(" ")
        buf = ""
        for i, w in enumerate(words):
            buf += (" " if buf else "") + w
            if i % 4 == 0 or i == len(words) - 1:
                yield f"data: {json.dumps({'type': 'delta', 'text': buf})}\n\n"
                buf = ""
                await asyncio.sleep(0.02)
        done = {
            "type": "done",
            "answer": out["answer"],
            "sources": out["sources"],
            "confidence": out["confidence"],
            "related_questions": out["related_questions"],
            "grounded": out["grounded"],
            "generated": out.get("generated", False),
            "conversation_id": str(out["conversation_id"])
            if out["conversation_id"]
            else None,
            "message_id": str(out["message_id"]) if out["message_id"] else None,
        }
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─────────────────── lead / escalate / feedback / event ───────────────────


@public_router.post("/lead", response_model=WidgetOk, summary="Capture a lead")
async def widget_lead(
    payload: WidgetLeadRequest,
    request: Request,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetOk:
    widget = await _load_live_widget(
        session, payload.public_key, origin=origin, referer=referer
    )
    _check_ip_rate(request, widget, "lead")
    _check_rate(widget, payload.visitor_id)
    if not (payload.email or payload.phone):
        raise HTTPException(422, "Provide at least an email or phone.")

    # Rejected requests must not create or enrich a lead, so the token is
    # checked before any write.
    ws = await _authorized_visitor_session(
        session, widget, payload.visitor_id, _presented_token(request)
    )
    conversation_id = ws.conversation_id
    if ws.conversation_id is not None:
        conv = await session.get(Conversation, ws.conversation_id)
        if conv is not None:
            conv.customer_name = payload.name or conv.customer_name
            conv.customer_email = payload.email or conv.customer_email
            conv.customer_phone = payload.phone or conv.customer_phone
            conv.status = ConversationStatus.qualified

    # Enrich the conversation's lead with the submitted contact details (or
    # create one if the visitor never chatted first). Deduped on the
    # conversation so we never end up with two leads for one visitor.
    await lead_service.upsert_conversation_lead(
        session,
        organization_id=widget.organization_id,
        project_id=widget.project_id,
        conversation_id=conversation_id,
        agent_id=widget.agent_id,
        widget_id=widget.id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        message=payload.message,
        source="widget",
    )

    await widget_service.log_event(
        session,
        widget=widget,
        event=WidgetEventType.lead,
        session_id=ws.id,
        metadata={
            "name": payload.name,
            "email": payload.email,
            "phone": payload.phone,
            "company": payload.company,
            "message": (payload.message or "")[:500],
        },
    )
    await session.commit()
    return WidgetOk(detail="Lead captured.")


@public_router.post("/escalate", response_model=WidgetOk, summary="Escalate to a human")
async def widget_escalate(
    payload: WidgetEscalateRequest,
    request: Request,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetOk:
    widget = await _load_live_widget(
        session, payload.public_key, origin=origin, referer=referer
    )
    _check_ip_rate(request, widget, "escalate")
    _check_rate(widget, payload.visitor_id)
    ws = await _authorized_visitor_session(
        session, widget, payload.visitor_id, _presented_token(request)
    )
    ws.escalated = True
    if ws.conversation_id is not None:
        conv = await session.get(Conversation, ws.conversation_id)
        if conv is not None:
            conv.status = ConversationStatus.active
            conv.extra = {**(conv.extra or {}), "escalated": True}
    await widget_service.log_event(
        session,
        widget=widget,
        event=WidgetEventType.escalation,
        session_id=ws.id,
        metadata={
            "reason": (payload.reason or "")[:500],
            "name": payload.name,
            "email": payload.email,
        },
    )
    # The manual request joins the same queue as automatic handoffs, so the team
    # works one list whichever way the visitor reached a person.
    from app.services.project_scope import resolve_project_id

    project_id = await resolve_project_id(
        session, widget.organization_id, widget.project_id
    )
    await escalation_service.create_escalation(
        session,
        organization_id=widget.organization_id,
        project_id=project_id,
        channel="chat",
        question=(payload.reason or "").strip()
        or "Visitor asked to speak to a person.",
        conversation_id=ws.conversation_id,
        name=payload.name,
        email=payload.email,
    )
    await session.commit()
    return WidgetOk(detail="Escalation requested.")


@public_router.post(
    "/feedback", response_model=WidgetOk, summary="Submit CSAT feedback"
)
async def widget_feedback(
    payload: WidgetFeedbackRequest,
    request: Request,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetOk:
    widget = await _load_live_widget(
        session, payload.public_key, origin=origin, referer=referer
    )
    _check_ip_rate(request, widget, "feedback")
    # Feedback is stored either way; it is linked to a visitor session only
    # when the caller proves it holds that session's token.
    ws = await _find_visitor_session(session, widget, payload.visitor_id)
    if ws is not None and not _session_token_matches(ws, _presented_token(request)):
        ws = None
    await widget_service.log_event(
        session,
        widget=widget,
        event=WidgetEventType.feedback,
        session_id=ws.id if ws else None,
        metadata={
            "rating": payload.rating,
            "comment": (payload.comment or "")[:500],
            "message_id": str(payload.message_id) if payload.message_id else None,
        },
    )
    await session.commit()
    return WidgetOk(detail="Thanks for the feedback.")


@public_router.post(
    "/event", response_model=WidgetOk, summary="Record an analytics event"
)
async def widget_event(
    payload: WidgetEventRequest,
    request: Request,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetOk:
    widget = await _load_live_widget(
        session,
        payload.public_key,
        origin=origin,
        referer=referer,
        require_published=False,
    )
    _check_ip_rate(request, widget, "event")
    event = (
        payload.event
        if payload.event in WidgetEventType.ALL
        else WidgetEventType.opened
    )
    # Link the event to a session only with that visitor's token.
    ws = None
    if payload.session_id is not None and payload.visitor_id:
        candidate = await session.scalar(
            select(WidgetSession)
            .where(WidgetSession.id == payload.session_id)
            .where(WidgetSession.widget_id == widget.id)
            .where(WidgetSession.visitor_id == payload.visitor_id)
        )
        if candidate is not None and _session_token_matches(
            candidate, _presented_token(request)
        ):
            ws = candidate
    await widget_service.log_event(
        session,
        widget=widget,
        event=event,
        session_id=ws.id if ws else None,
        metadata=payload.metadata or {},
    )
    await session.commit()
    return WidgetOk()
