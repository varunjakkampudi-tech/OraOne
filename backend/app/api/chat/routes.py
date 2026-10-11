"""AI Chat & Agent Runtime API (Phase 8).

Mounted at ``/api/conversations`` — distinct from the CRM-oriented
``/api/v2/conversations`` surface from Phase 5. These endpoints power the
end-user chat experience: thread CRUD, message send (which invokes the
agent runtime), and live SSE streaming.

Isolation model
---------------
Every conversation here is an *owned* AI chat thread: it carries both an
``organization_id`` (tenant boundary) and a ``user_id`` (owner). Reads
and writes require BOTH to match the caller, so there is no cross-tenant
*and* no cross-user leakage.
"""
from __future__ import annotations

import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.conversation import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
)
from app.database.models.conversation_folder import ConversationFolder
from app.database.models.message import Message, MessageSender
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.providers import AIProviderError, estimate_tokens
from app.providers.base import ChatMessage
from app.schemas.chat import (
    ChatConversationOut,
    ChatMessageOut,
    ConversationCreate,
    ConversationPatch,
    ConversationRename,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    MessageSend,
    SendMessageResult,
    ShareResult,
    SuggestedQuestions,
)
from app.services.agent_runtime import AgentRuntime, sender_to_role
from app.services import rag_service
from app.services import usage_service
from app.services.audit import audit

log = logging.getLogger("app.api.chat")

router = APIRouter(prefix="/api/conversations", tags=["chat"])


# ─────────────────────────── helpers ───────────────────────────

def _msg_out(m: Message) -> ChatMessageOut:
    return ChatMessageOut(
        id=m.id,
        conversation_id=m.conversation_id,
        role=sender_to_role(m.sender),
        content=m.message,
        token_count=m.token_count,
        metadata=m.metadata_ or {},
        created_at=m.created_at,
    )


async def _load_thread(
    session: AsyncSession, ctx: OrgContext, conversation_id: uuid.UUID
) -> Optional[Conversation]:
    """Owner + tenant scoped fetch. Returns ``None`` to 404 on any miss."""
    q = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.organization_id == ctx.organization_id)
        .where(Conversation.user_id == ctx.user_id)
        .where(Conversation.deleted_at.is_(None))
    )
    return await session.scalar(q)


def _audit(action: str, ctx: OrgContext, *, resource_id: str, meta: Optional[dict] = None) -> None:
    audit(
        action,
        resource="conversation",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=resource_id,
        meta=meta,
    )


# ─────────────────────── conversation CRUD ─────────────────────

@router.post("", response_model=ChatConversationOut, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Conversation:
    runtime = AgentRuntime(session, ctx)
    agent = await runtime.load_agent(payload.agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent not found in your organization.")

    conv = Conversation(
        organization_id=ctx.organization_id,
        agent_id=payload.agent_id,
        user_id=ctx.user_id,
        channel=ConversationChannel.chat,
        status=ConversationStatus.active,
        title=payload.title or "New Conversation",
        started_at=datetime.now(timezone.utc),
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    _audit("create", ctx, resource_id=str(conv.id), meta={"agent_id": str(payload.agent_id)})
    return conv


@router.get("", response_model=list[ChatConversationOut])
async def list_conversations(
    agent_id: Optional[uuid.UUID] = Query(default=None),
    folder_id: Optional[uuid.UUID] = Query(default=None),
    q: Optional[str] = Query(default=None, max_length=200, description="Search title + message content."),
    archived: Optional[bool] = Query(default=None, description="Filter by archived flag; omit for all."),
    favorite: Optional[bool] = Query(default=None),
    pinned: Optional[bool] = Query(default=None),
    sort: str = Query(default="recent", pattern="^(recent|created|title)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> list[Conversation]:
    q_stmt = (
        select(Conversation)
        .where(Conversation.organization_id == ctx.organization_id)
        .where(Conversation.user_id == ctx.user_id)
        .where(Conversation.deleted_at.is_(None))
    )
    if agent_id is not None:
        q_stmt = q_stmt.where(Conversation.agent_id == agent_id)
    if folder_id is not None:
        q_stmt = q_stmt.where(Conversation.folder_id == folder_id)
    if archived is not None:
        q_stmt = q_stmt.where(Conversation.is_archived.is_(archived))
    if favorite is not None:
        q_stmt = q_stmt.where(Conversation.is_favorite.is_(favorite))
    if pinned is not None:
        q_stmt = q_stmt.where(Conversation.is_pinned.is_(pinned))
    if q:
        term = f"%{q.strip()}%"
        # Match the thread title OR any message body inside the thread.
        msg_match = exists().where(
            (Message.conversation_id == Conversation.id) & (Message.message.ilike(term))
        )
        q_stmt = q_stmt.where(or_(Conversation.title.ilike(term), msg_match))

    if sort == "created":
        q_stmt = q_stmt.order_by(Conversation.is_pinned.desc(), Conversation.created_at.desc())
    elif sort == "title":
        q_stmt = q_stmt.order_by(Conversation.is_pinned.desc(), Conversation.title.asc())
    else:  # recent — last activity first, falling back to created_at
        q_stmt = q_stmt.order_by(
            Conversation.is_pinned.desc(),
            func.coalesce(Conversation.last_message_at, Conversation.created_at).desc(),
        )

    q_stmt = q_stmt.limit(limit).offset(offset)
    return list((await session.scalars(q_stmt)).all())


@router.get("/{conversation_id}", response_model=ChatConversationOut)
async def get_conversation(
    conversation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Conversation:
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    return conv


@router.put("/{conversation_id}", response_model=ChatConversationOut)
async def rename_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationRename,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Conversation:
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    conv.title = payload.title
    await session.commit()
    await session.refresh(conv)
    _audit("update", ctx, resource_id=str(conv.id), meta={"title": payload.title})
    return conv


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_conversation(
    conversation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Response:
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    conv.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    _audit("delete", ctx, resource_id=str(conversation_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{conversation_id}", response_model=ChatConversationOut)
async def patch_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationPatch,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Conversation:
    """Flexible partial update: pin/archive/favorite, move to folder,
    set tags, rename, or change status — any subset in one call."""
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")

    changed: dict = {}
    if payload.title is not None:
        conv.title = payload.title
        changed["title"] = payload.title
    if payload.is_pinned is not None:
        conv.is_pinned = payload.is_pinned
        changed["is_pinned"] = payload.is_pinned
    if payload.is_archived is not None:
        conv.is_archived = payload.is_archived
        changed["is_archived"] = payload.is_archived
    if payload.is_favorite is not None:
        conv.is_favorite = payload.is_favorite
        changed["is_favorite"] = payload.is_favorite
    if payload.tags is not None:
        # Normalise: trim, drop blanks, dedupe, cap length.
        cleaned = []
        for t in payload.tags:
            t = (t or "").strip()[:40]
            if t and t not in cleaned:
                cleaned.append(t)
        conv.tags = cleaned[:20]
        changed["tags"] = conv.tags
    if payload.status is not None:
        try:
            conv.status = ConversationStatus(payload.status)
            changed["status"] = payload.status
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid status: {payload.status}") from e
    if payload.clear_folder:
        conv.folder_id = None
        changed["folder_id"] = None
    elif payload.folder_id is not None:
        folder = await session.scalar(
            select(ConversationFolder)
            .where(ConversationFolder.id == payload.folder_id)
            .where(ConversationFolder.organization_id == ctx.organization_id)
            .where(ConversationFolder.user_id == ctx.user_id)
        )
        if folder is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
        conv.folder_id = folder.id
        changed["folder_id"] = str(folder.id)

    await session.commit()
    await session.refresh(conv)
    _audit("update", ctx, resource_id=str(conv.id), meta=changed)
    return conv


# ───────────────────────── export ──────────────────────────────

@router.get("/{conversation_id}/export")
async def export_conversation(
    conversation_id: uuid.UUID,
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    """Download a transcript as Markdown or JSON."""
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    rows = list(
        (
            await session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            )
        ).all()
    )
    title = conv.title or "Conversation"
    _audit("export", ctx, resource_id=str(conversation_id), meta={"format": format})

    if format == "json":
        body = {
            "title": title,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "messages": [
                {
                    "role": sender_to_role(m.sender),
                    "content": m.message,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in rows
            ],
        }
        return Response(
            content=json.dumps(body, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="conversation-{conversation_id}.json"'},
        )

    lines = [f"# {title}", ""]
    for m in rows:
        role = sender_to_role(m.sender)
        who = {"user": "You", "assistant": "Assistant", "system": "System"}.get(role, role.title())
        ts = m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else ""
        lines.append(f"### {who}  \n*{ts}*\n")
        lines.append(m.message or "")
        lines.append("")
    md = "\n".join(lines)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="conversation-{conversation_id}.md"'},
    )


# ───────────────────────── sharing ─────────────────────────────

def _share_url(token: str) -> str:
    return f"/share/{token}"


@router.post("/{conversation_id}/share", response_model=ShareResult)
async def enable_share(
    conversation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> ShareResult:
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    if not conv.share_token:
        conv.share_token = secrets.token_urlsafe(24)
        conv.shared_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(conv)
    _audit("share_enabled", ctx, resource_id=str(conversation_id))
    return ShareResult(
        share_token=conv.share_token,
        shared_at=conv.shared_at,
        share_url=_share_url(conv.share_token),
        is_shared=True,
    )


@router.delete("/{conversation_id}/share", response_model=ShareResult)
async def disable_share(
    conversation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> ShareResult:
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    conv.share_token = None
    conv.shared_at = None
    await session.commit()
    _audit("share_disabled", ctx, resource_id=str(conversation_id))
    return ShareResult(is_shared=False)


# ──────────────────── suggested questions ──────────────────────

_FALLBACK_QUESTIONS = [
    "Can you summarize the key points so far?",
    "What should I do next?",
    "Can you explain that in more detail?",
]


@router.get("/{conversation_id}/suggested-questions", response_model=SuggestedQuestions)
async def suggested_questions(
    conversation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SuggestedQuestions:
    """Propose follow-up questions based on the last assistant turn.
    Falls back to deterministic prompts when the AI provider is down."""
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")

    last_assistant = await session.scalar(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .where(Message.sender == MessageSender.agent)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    if last_assistant is None:
        return SuggestedQuestions(questions=list(_FALLBACK_QUESTIONS))

    runtime = AgentRuntime(session, ctx)
    agent = await runtime.load_agent(conv.agent_id)
    prompt = (
        "Based on the assistant's last message below, propose exactly three short, "
        "distinct follow-up questions a user might ask next. Return one per line, no numbering.\n\n"
        f"Assistant: {last_assistant.message[:1500]}"
    )
    try:
        if agent is None:
            raise RuntimeError("agent unavailable")
        ai = await runtime.generate_reply(
            agent, [ChatMessage(role="user", content=prompt)]
        )
        qs = [
            line.strip(" -•\t")
            for line in (ai.content or "").splitlines()
            if line.strip(" -•\t")
        ][:3]
        if not qs:
            raise RuntimeError("empty completion")
    except Exception as e:  # noqa: BLE001 — graceful degradation
        log.info("suggested_questions fallback: %s", e)
        qs = list(_FALLBACK_QUESTIONS)
    return SuggestedQuestions(questions=qs)


# ─────────────────────────── regenerate ────────────────────────

@router.post("/{conversation_id}/regenerate", response_model=SendMessageResult)
async def regenerate_last(
    conversation_id: uuid.UUID,
    use_knowledge: bool = Query(default=True),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SendMessageResult:
    """Re-run the model on the most recent user turn, replacing the last
    assistant reply."""
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")

    last_user = await session.scalar(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .where(Message.sender == MessageSender.customer)
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    if last_user is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nothing to regenerate yet.")

    runtime = AgentRuntime(session, ctx)
    agent = await runtime.load_agent(conv.agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "The agent for this conversation is unavailable.")

    # Drop the trailing assistant message(s) that followed the last user turn.
    later_assistants = list(
        (
            await session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .where(Message.sender == MessageSender.agent)
                .where(Message.created_at >= last_user.created_at)
            )
        ).all()
    )
    for m in later_assistants:
        await session.delete(m)
    await session.flush()

    messages, retrieved = await runtime.build_payload(
        agent,
        conversation_id,
        last_user.message,
        history_limit=20,
        use_knowledge=use_knowledge,
    )
    sources = rag_service.dedupe_sources(retrieved)
    try:
        ai = await runtime.generate_reply(agent, messages)
    except AIProviderError as e:
        raise _provider_http_error(e) from e

    assistant_msg = Message(
        conversation_id=conversation_id,
        sender=MessageSender.agent,
        message=ai.content,
        token_count=ai.usage.total_tokens,
        metadata_={
            "model": ai.model,
            "provider": runtime.provider.name,
            "regenerated": True,
            "usage": ai.usage.as_dict(),
            "context_chunks": len(retrieved),
            "sources": sources,
        },
    )
    session.add(assistant_msg)
    conv.last_message_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(assistant_msg)
    await session.refresh(last_user)
    _audit("regenerated", ctx, resource_id=str(conversation_id))
    return SendMessageResult(
        conversation_id=conversation_id,
        title=conv.title,
        user_message=_msg_out(last_user),
        assistant_message=_msg_out(assistant_msg),
        usage=ai.usage.as_dict(),
        context_used=len(retrieved),
        sources=sources,
    )


# ───────────────────────── messages ────────────────────────────

@router.get("/{conversation_id}/messages", response_model=list[ChatMessageOut])
async def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=200, ge=1, le=1000),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> list[ChatMessageOut]:
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    q = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    rows = list((await session.scalars(q)).all())
    return [_msg_out(m) for m in rows]


async def _persist_user_message(
    session: AsyncSession, conversation_id: uuid.UUID, content: str
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        sender=MessageSender.customer,
        message=content,
        token_count=estimate_tokens(content),
        metadata_={},
    )
    session.add(msg)
    await session.flush()
    return msg


def _provider_http_error(e: AIProviderError) -> HTTPException:
    """Map a normalised provider error to a graceful HTTP response."""
    mapping = {
        "timeout": status.HTTP_504_GATEWAY_TIMEOUT,
        "rate_limit": status.HTTP_429_TOO_MANY_REQUESTS,
        "auth": status.HTTP_502_BAD_GATEWAY,
        "context_overflow": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        "network": status.HTTP_502_BAD_GATEWAY,
        "provider": status.HTTP_502_BAD_GATEWAY,
    }
    code = mapping.get(e.code, status.HTTP_502_BAD_GATEWAY)
    return HTTPException(code, detail={"error": e.code, "message": str(e)})


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResult,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageSend,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SendMessageResult:
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")

    runtime = AgentRuntime(session, ctx)
    agent = await runtime.load_agent(conv.agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "The agent for this conversation is unavailable.")

    # Build the model payload from history BEFORE persisting the new user
    # turn, so the current message isn't duplicated in the prompt.
    is_first = (
        await session.scalar(
            select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        )
    ) == 0

    messages, retrieved = await runtime.build_payload(
        agent,
        conversation_id,
        payload.content,
        history_limit=payload.history_limit,
        use_knowledge=payload.use_knowledge,
    )
    sources = rag_service.dedupe_sources(retrieved)

    _audit("message_sent", ctx, resource_id=str(conversation_id), meta={"chars": len(payload.content)})

    # Phase 12 Module 2: enforce the plan's daily AI-message quota.
    await usage_service.enforce_quota(session, ctx.organization_id, "ai_messages")

    try:
        ai = await runtime.generate_reply(agent, messages)
    except AIProviderError as e:
        log.warning("provider error code=%s: %s", e.code, e)
        raise _provider_http_error(e) from e

    # Persist user turn first (so its timestamp precedes the assistant's).
    user_msg = await _persist_user_message(session, conversation_id, payload.content)

    assistant_msg = Message(
        conversation_id=conversation_id,
        sender=MessageSender.agent,
        message=ai.content,
        token_count=ai.usage.total_tokens,
        metadata_={
            "model": ai.model,
            "provider": runtime.provider.name,
            "finish_reason": ai.finish_reason,
            "usage": ai.usage.as_dict(),
            "context_chunks": len(retrieved),
            "sources": sources,
        },
    )
    session.add(assistant_msg)
    await session.flush()

    # Thread bookkeeping: bump activity + auto-title on first turn.
    conv.last_message_at = datetime.now(timezone.utc)
    if is_first:
        conv.title = await runtime.generate_title(payload.content)
    await session.commit()
    await session.refresh(user_msg)
    await session.refresh(assistant_msg)
    await session.refresh(conv)

    # Phase 12 Module 2: record one AI message against the daily meter.
    await usage_service.record_usage(session, ctx.organization_id, "ai_messages", 1)

    _audit(
        "response_generated",
        ctx,
        resource_id=str(conversation_id),
        meta={"usage": ai.usage.as_dict(), "model": ai.model},
    )

    return SendMessageResult(
        conversation_id=conversation_id,
        title=conv.title,
        user_message=_msg_out(user_msg),
        assistant_message=_msg_out(assistant_msg),
        usage=ai.usage.as_dict(),
        context_used=len(retrieved),
        sources=sources,
    )


# ───────────────────────── streaming (SSE) ─────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/{conversation_id}/stream")
async def stream_message(
    conversation_id: uuid.UUID,
    payload: MessageSend,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    conv = await _load_thread(session, ctx, conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")

    runtime = AgentRuntime(session, ctx)
    agent = await runtime.load_agent(conv.agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "The agent for this conversation is unavailable.")

    is_first = (
        await session.scalar(
            select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        )
    ) == 0

    messages, retrieved = await runtime.build_payload(
        agent,
        conversation_id,
        payload.content,
        history_limit=payload.history_limit,
        use_knowledge=payload.use_knowledge,
    )
    sources = rag_service.dedupe_sources(retrieved)

    async def event_stream() -> AsyncIterator[str]:
        _audit("streaming_started", ctx, resource_id=str(conversation_id))
        yield _sse("start", {"conversation_id": str(conversation_id)})

        # Persist the user turn up-front so it survives a mid-stream
        # disconnect (reconnect-safe).
        user_msg = await _persist_user_message(session, conversation_id, payload.content)
        await session.commit()
        yield _sse("user_saved", {"id": str(user_msg.id)})

        acc: list[str] = []
        try:
            async for piece in runtime.stream_reply(agent, messages):
                acc.append(piece)
                yield _sse("token", {"delta": piece})
        except AIProviderError as e:
            log.warning("stream provider error code=%s: %s", e.code, e)
            yield _sse("error", {"error": e.code, "message": str(e)})
        except Exception as e:  # noqa: BLE001 — never crash the stream
            log.exception("unexpected stream failure")
            yield _sse("error", {"error": "unknown", "message": "Streaming failed."})
        finally:
            content = "".join(acc)
            if content:
                prompt_tokens = sum(estimate_tokens(m.content) for m in messages)
                completion_tokens = estimate_tokens(content)
                total = prompt_tokens + completion_tokens
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    sender=MessageSender.agent,
                    message=content,
                    token_count=total,
                    metadata_={
                        "provider": runtime.provider.name,
                        "streamed": True,
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total,
                        },
                        "context_chunks": len(retrieved),
                        "sources": sources,
                    },
                )
                session.add(assistant_msg)
                conv.last_message_at = datetime.now(timezone.utc)
                if is_first:
                    conv.title = await runtime.generate_title(payload.content)
                await session.commit()
                await session.refresh(assistant_msg)
                _audit(
                    "streaming_completed",
                    ctx,
                    resource_id=str(conversation_id),
                    meta={"total_tokens": total},
                )
                yield _sse(
                    "done",
                    {
                        "message_id": str(assistant_msg.id),
                        "title": conv.title,
                        "content": content,
                        "usage": assistant_msg.metadata_["usage"],
                        "context_used": len(retrieved),
                        "sources": sources,
                    },
                )
            else:
                yield _sse("done", {"content": "", "usage": {}, "context_used": 0, "sources": []})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering for live SSE
        },
    )
