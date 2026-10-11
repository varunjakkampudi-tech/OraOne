"""Tenant-scoped business API (Phase 5).

All routes here resolve their tenant from the authenticated identity via
``get_current_organization`` — never from the request body, query string,
or headers. Repositories used here MUST be the ``OrgScoped*`` variants.

Mounted under ``/api/v2`` so the legacy MongoDB-backed routes in
``server.py`` keep working until Phase 2 migrates them.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent  # noqa: F401 — used by OrgScopedAgentRepository in conversation create-path
from app.database.models.conversation import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
)
from app.database.models.integration import (
    Integration,
    IntegrationStatus,
    IntegrationType,
)
from app.database.models.message import Message, MessageSender
from app.database.repositories.agent_repository import OrgScopedAgentRepository
from app.database.repositories.conversation_repository import (
    OrgScopedConversationRepository,
)
from app.database.repositories.integration_repository import (
    OrgScopedIntegrationRepository,
)
from app.database.repositories.message_repository import OrgScopedMessageRepository
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_role,
)
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import usage_service
from app.schemas.v2 import (
    ConversationIn,
    ConversationOut,
    IntegrationIn,
    IntegrationOut,
    MessageIn,
    MessageOut,
)

router = APIRouter(prefix="/api/v2", tags=["v2"])


# ─────────────────── Observability helpers ───────────────────

def _message_out(m: Message) -> MessageOut:
    """Project a Message ORM row to MessageOut, surfacing the observability
    fields stored inside ``metadata_`` (model, token split, cost, latency,
    citations)."""
    meta = m.metadata_ if isinstance(m.metadata_, dict) else {}
    citations = meta.get("citations") or meta.get("sources") or []
    if not isinstance(citations, list):
        citations = []
    return MessageOut(
        id=m.id,
        conversation_id=m.conversation_id,
        sender=m.sender.value if hasattr(m.sender, "value") else str(m.sender),
        message=m.message,
        audio_url=m.audio_url,
        created_at=m.created_at,
        token_count=m.token_count,
        model=meta.get("model"),
        prompt_tokens=meta.get("prompt_tokens"),
        completion_tokens=meta.get("completion_tokens"),
        total_tokens=meta.get("total_tokens"),
        cost_usd=meta.get("cost_usd"),
        latency_ms=meta.get("latency_ms"),
        confidence=meta.get("confidence"),
        grounded=meta.get("grounded"),
        citations=citations,
    )


async def _usage_rollups(
    session: AsyncSession, conv_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict]:
    """One grouped query → message_count + total_tokens per conversation.
    Cost / latency / models come from the conversation's stored rollup."""
    if not conv_ids:
        return {}
    rows = await session.execute(
        select(
            Message.conversation_id,
            func.count().label("cnt"),
            func.coalesce(func.sum(Message.token_count), 0).label("tokens"),
        )
        .where(Message.conversation_id.in_(conv_ids))
        .group_by(Message.conversation_id)
    )
    return {
        r.conversation_id: {"message_count": int(r.cnt), "total_tokens": int(r.tokens or 0)}
        for r in rows
    }


def _conversation_out(c: Conversation, rollup: Optional[dict]) -> ConversationOut:
    rollup = rollup or {}
    stored = c.extra.get("usage", {}) if isinstance(c.extra, dict) else {}
    models = list(stored.get("models", []))
    return ConversationOut(
        id=c.id,
        organization_id=c.organization_id,
        agent_id=c.agent_id,
        channel=c.channel.value if hasattr(c.channel, "value") else str(c.channel),
        status=c.status.value if hasattr(c.status, "value") else str(c.status),
        title=c.title,
        customer_name=c.customer_name,
        customer_email=c.customer_email,
        customer_phone=c.customer_phone,
        started_at=c.started_at,
        ended_at=c.ended_at,
        last_message_at=c.last_message_at,
        duration_seconds=c.duration_seconds,
        summary=c.summary,
        created_at=c.created_at,
        message_count=rollup.get("message_count", stored.get("message_count", 0)),
        total_tokens=rollup.get("total_tokens", stored.get("total_tokens", 0)),
        total_cost_usd=round(float(stored.get("total_cost_usd", 0.0)), 6),
        avg_latency_ms=stored.get("last_latency_ms"),
        models=models,
        last_model=stored.get("last_model"),
    )


# ─────────────────────────── Whoami ───────────────────────────

@router.get("/me/organization")
async def whoami(ctx: OrgContext = Depends(get_current_organization)) -> dict:
    """Echo back the server-resolved org context (handy for debugging)."""
    return {
        "user_id": str(ctx.user_id),
        "organization_id": str(ctx.organization_id),
        "membership_role": ctx.membership_role,
    }


# ─────────────────────────── Agents ───────────────────────────
# Agent CRUD lives at /api/agents (Phase 6) — see app.api.agents.routes.


# ───────────────────── Conversations ─────────────────────

@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    agent_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    ctx = pctx.org
    parsed_status = ConversationStatus(status_filter) if status_filter else None
    repo = OrgScopedConversationRepository(session, ctx)
    convs = await repo.list_filtered(
        status=parsed_status, agent_id=agent_id, project_id=pctx.project_id,
        limit=limit, offset=offset,
    )
    rollups = await _usage_rollups(session, [c.id for c in convs])
    return [_conversation_out(c, rollups.get(c.id)) for c in convs]


@router.post(
    "/conversations",
    response_model=ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationIn,
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> Conversation:
    ctx = pctx.org
    # Verify the agent belongs to the caller's org before creating the thread.
    agent_repo = OrgScopedAgentRepository(session, ctx)
    if await agent_repo.get_in_org(payload.agent_id) is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Agent not found in your organization.",
        )

    try:
        channel = ConversationChannel(payload.channel)
        conv_status = ConversationStatus(payload.status)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e

    conv = Conversation(
        agent_id=payload.agent_id,
        project_id=pctx.project_id,
        channel=channel,
        status=conv_status,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
        started_at=payload.started_at or datetime.now(timezone.utc),
        summary=payload.summary,
        extra=payload.extra,
    )
    repo = OrgScopedConversationRepository(session, ctx)
    await repo.add_for_org(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> ConversationOut:
    repo = OrgScopedConversationRepository(session, ctx)
    conv = await repo.get_in_org(conversation_id)
    if conv is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    rollups = await _usage_rollups(session, [conv.id])
    return _conversation_out(conv, rollups.get(conv.id))


# ─────────────────────── Messages ───────────────────────

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
)
async def list_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=500, ge=1, le=1000),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    # Pre-check the conversation belongs to the caller's org. Without this,
    # a 404 would leak existence/non-existence semantics; with it, we get
    # consistent 404 for both "doesn't exist" and "exists but not yours".
    conv_repo = OrgScopedConversationRepository(session, ctx)
    if await conv_repo.get_in_org(conversation_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")

    msg_repo = OrgScopedMessageRepository(session, ctx)
    msgs = await msg_repo.list_in_conversation(conversation_id, limit=limit)
    return [_message_out(m) for m in msgs]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    conversation_id: uuid.UUID,
    payload: MessageIn,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Message:
    try:
        sender = MessageSender(payload.sender)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e

    msg = Message(
        sender=sender,
        message=payload.message,
        audio_url=payload.audio_url,
        metadata_=payload.metadata,
    )
    repo = OrgScopedMessageRepository(session, ctx)
    try:
        await repo.add_to_conversation(msg, conversation_id)
    except PermissionError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    await session.commit()
    await session.refresh(msg)
    return _message_out(msg)


# ───────────────────── Integrations ─────────────────────

@router.get("/integrations", response_model=list[IntegrationOut])
async def list_integrations(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> list[Integration]:
    repo = OrgScopedIntegrationRepository(session, ctx)
    return list(await repo.list_in_org())


@router.post(
    "/integrations",
    response_model=IntegrationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def create_integration(
    payload: IntegrationIn,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Integration:
    try:
        itype = IntegrationType(payload.type)
        istatus = IntegrationStatus(payload.status)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e

    # Phase 12 Module 2: enforce the plan's integration quota before creating.
    await usage_service.enforce_quota(session, ctx.organization_id, "integrations")

    repo = OrgScopedIntegrationRepository(session, ctx)
    if await repo.get_by_provider(payload.provider) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Integration '{payload.provider}' already exists for this organization.",
        )

    integration = Integration(
        provider=payload.provider,
        type=itype,
        status=istatus,
        config=payload.config,
    )
    await repo.add_for_org(integration)
    await session.commit()
    await session.refresh(integration)
    return integration


@router.delete(
    "/integrations/{integration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def delete_integration(
    integration_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Response:
    repo = OrgScopedIntegrationRepository(session, ctx)
    ok = await repo.soft_delete_in_org(integration_id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Integration not found.")
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
