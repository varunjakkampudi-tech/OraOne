"""Public widget API (R6) — unauthenticated, domain-restricted.

These endpoints back the embedded chat experience. They are reachable
without a logged-in user (visitors are anonymous), so every request is
guarded by:
* the widget's **published** status,
* an optional **domain allow-list** (Origin/Referer must match),
* a per-visitor **rate limit**,
* strict **input length** caps.

Answers are produced by the Enterprise RAG engine (R4), grounded in the
widget's knowledge base, and degrade to extractive answers when the AI
provider is offline.
"""
from __future__ import annotations

import asyncio
import json
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
from app.services import widget_service
from app.services import lead_service
from app.services import visitor_service
from app.services.rag_answer import answer_query

public_router = APIRouter(prefix="/api/widget", tags=["widget-public"])

_MAX_CONTEXT_KEYS = {"name", "email", "company", "plan", "language", "url", "page_title", "userId"}


# ─────────────────── guards ───────────────────

async def _load_live_widget(
    session: AsyncSession,
    public_key: str,
    *,
    origin: Optional[str],
    referer: Optional[str],
    require_published: bool = True,
) -> Widget:
    widget = await widget_service.get_widget_by_key(session, public_key)
    if widget is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Widget not found.")
    if require_published and widget.status != WidgetStatus.published:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Widget is not live.")
    domains = await widget_service.widget_domains(session, widget.id)
    host = widget_service.origin_host(origin, referer)
    if not widget_service.domain_allowed(domains, host):
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


def _sanitize_context(ctx: dict) -> dict:
    if not isinstance(ctx, dict):
        return {}
    return {
        k: (str(v)[:300] if v is not None else None)
        for k, v in ctx.items()
        if k in _MAX_CONTEXT_KEYS
    }


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
        if not widget_service.domain_allowed(domains, host):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "This widget is not authorized for this domain.",
            )
    return WidgetPublicConfig(**widget_service.public_config_dict(widget, []))


# ─────────────────── session ───────────────────

async def _get_or_create_session(
    session: AsyncSession,
    widget: Widget,
    *,
    visitor_id: str,
    user_context: dict,
    referer: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> WidgetSession:
    ws = await session.scalar(
        select(WidgetSession)
        .where(WidgetSession.widget_id == widget.id)
        .where(WidgetSession.visitor_id == visitor_id)
        .order_by(WidgetSession.started_at.desc())
        .limit(1)
    )
    if ws is None:
        ws = WidgetSession(
            widget_id=widget.id,
            organization_id=widget.organization_id,
            visitor_id=visitor_id,
            user_context=_sanitize_context(user_context),
            referer=(referer or "")[:2048] or None,
            user_agent=(user_agent or "")[:512] or None,
            last_active_at=widget_service.now_utc(),
        )
        session.add(ws)
        await session.flush()
    else:
        if user_context:
            ws.user_context = {**(ws.user_context or {}), **_sanitize_context(user_context)}
        ws.last_active_at = widget_service.now_utc()
    return ws


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
    visitor_id = (payload.visitor_id or f"v_{uuid.uuid4().hex[:16]}").strip()[:80]
    ws = await _get_or_create_session(
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
    if ws.conversation_id is not None:
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
    if agent_id is not None:
        agent_row = await session.scalar(
            select(Agent).options(selectinload(Agent.config)).where(Agent.id == agent_id)
        )
        if agent_row is not None:
            if agent_row.status != AgentStatus.active:
                return {
                    "answer": _AGENT_UNAVAILABLE_MESSAGE,
                    "sources": [],
                    "confidence": 0.0,
                    "related_questions": [],
                    "grounded": False,
                    "conversation_id": ws.conversation_id,
                    "message_id": None,
                }
            cfg = agent_row.config
            agent_persona = cfg.system_prompt if cfg else None
            agent_model = agent_row.model

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
    digest: Optional[str] = None
    profile = None
    if conversation is not None:
        ctx = ws.user_context or {}
        profile = await visitor_service.upsert_profile(
            session,
            organization_id=widget.organization_id,
            visitor_key=ws.visitor_id,
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

    kb_ids = [widget.knowledge_base_id] if widget.knowledge_base_id else None
    result = await answer_query(
        session,
        text,
        widget.organization_id,
        knowledge_base_ids=kb_ids,
        top_k=5,
        extra_context=digest,
        persona=agent_persona,
        model=agent_model,
    )

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
            },
        )
        session.add(answer_msg)
        conversation.last_message_at = widget_service.now_utc()

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
    _check_rate(widget, payload.visitor_id)
    text = payload.message.strip()
    if not text:
        raise HTTPException(422, "Message is empty.")

    ws = await _get_or_create_session(
        session,
        widget,
        visitor_id=payload.visitor_id,
        user_context=payload.user_context,
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
        session_id=ws.id,
        conversation_id=out["conversation_id"],
        message_id=out["message_id"],
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
    _check_rate(widget, payload.visitor_id)
    text = payload.message.strip()
    if not text:
        raise HTTPException(422, "Message is empty.")

    ws = await _get_or_create_session(
        session,
        widget,
        visitor_id=payload.visitor_id,
        user_context=payload.user_context,
        referer=referer,
        user_agent=request.headers.get("user-agent"),
    )
    out = await _persist_and_answer(session, widget, ws, text)
    await session.commit()

    async def event_stream():
        # Emit a 'meta' frame, then the answer in word chunks, then 'done'.
        yield f"data: {json.dumps({'type': 'meta', 'session_id': str(ws.id)})}\n\n"
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
            "conversation_id": str(out["conversation_id"]) if out["conversation_id"] else None,
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
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetOk:
    widget = await _load_live_widget(
        session, payload.public_key, origin=origin, referer=referer
    )
    _check_rate(widget, payload.visitor_id)
    if not (payload.email or payload.phone):
        raise HTTPException(422, "Provide at least an email or phone.")

    ws = await _get_or_create_session(
        session, widget, visitor_id=payload.visitor_id, user_context={}
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


@public_router.post(
    "/escalate", response_model=WidgetOk, summary="Escalate to a human"
)
async def widget_escalate(
    payload: WidgetEscalateRequest,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetOk:
    widget = await _load_live_widget(
        session, payload.public_key, origin=origin, referer=referer
    )
    _check_rate(widget, payload.visitor_id)
    ws = await _get_or_create_session(
        session, widget, visitor_id=payload.visitor_id, user_context={}
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
    await session.commit()
    return WidgetOk(detail="Escalation requested.")


@public_router.post(
    "/feedback", response_model=WidgetOk, summary="Submit CSAT feedback"
)
async def widget_feedback(
    payload: WidgetFeedbackRequest,
    origin: Optional[str] = Header(default=None),
    referer: Optional[str] = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WidgetOk:
    widget = await _load_live_widget(
        session, payload.public_key, origin=origin, referer=referer
    )
    ws = await session.scalar(
        select(WidgetSession)
        .where(WidgetSession.widget_id == widget.id)
        .where(WidgetSession.visitor_id == payload.visitor_id)
        .order_by(WidgetSession.started_at.desc())
        .limit(1)
    )
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
    event = payload.event if payload.event in WidgetEventType.ALL else WidgetEventType.opened
    ws = None
    if payload.session_id is not None:
        ws = await session.get(WidgetSession, payload.session_id)
    await widget_service.log_event(
        session,
        widget=widget,
        event=event,
        session_id=ws.id if ws else None,
        metadata=payload.metadata or {},
    )
    await session.commit()
    return WidgetOk()
