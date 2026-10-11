"""Widget admin API (R6) — org-scoped, authenticated CRUD + analytics.

Create a widget in the dashboard, bind an agent + knowledge base,
customize branding/behavior, pin allowed domains, publish, and read
usage analytics. The public loader/chat surface lives in ``public.py``.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Float, cast, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.agent import Agent, AgentStatus
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.widget import (
    Widget,
    WidgetAuthMode,
    WidgetPosition,
    WidgetStatus,
    WidgetType,
    _gen_public_key,
)
from app.database.models.widget_domain import WidgetDomain
from app.database.models.widget_event import WidgetEvent, WidgetEventType
from app.database.models.widget_session import WidgetSession
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_role,
)
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.widget import (
    WidgetAnalytics,
    WidgetCreate,
    WidgetListResponse,
    WidgetRead,
    WidgetUpdate,
)
from app.services import widget_service
from app.services import agent_lifecycle
from app.services.audit import audit

router = APIRouter(prefix="/api/widgets", tags=["widgets"])


# ─────────────────── helpers ───────────────────

async def _widget_for_org(
    session: AsyncSession, *, widget_id: uuid.UUID, organization_id: uuid.UUID
) -> Optional[Widget]:
    return await session.scalar(
        select(Widget)
        .where(Widget.id == widget_id)
        .where(Widget.organization_id == organization_id)
        .where(Widget.deleted_at.is_(None))
    )


async def _read(session: AsyncSession, widget: Widget) -> WidgetRead:
    domains = await widget_service.widget_domains(session, widget.id)
    sessions_count = int(
        await session.scalar(
            select(func.count(WidgetSession.id)).where(
                WidgetSession.widget_id == widget.id
            )
        )
        or 0
    )
    data = {
        **widget.__dict__,
        "domains": domains,
        "embed_snippet": widget_service.build_embed_snippet(widget.public_key),
        "sessions_count": sessions_count,
    }
    return WidgetRead.model_validate(data)


def _validate_enums(*, widget_type=None, position=None, auth_mode=None, status_=None):
    if widget_type is not None and widget_type not in WidgetType.ALL:
        raise HTTPException(422, f"Invalid widget_type {widget_type!r}.")
    if position is not None and position not in WidgetPosition.ALL:
        raise HTTPException(422, f"Invalid position {position!r}.")
    if auth_mode is not None and auth_mode not in WidgetAuthMode.ALL:
        raise HTTPException(422, f"Invalid auth_mode {auth_mode!r}.")
    if status_ is not None and status_ not in WidgetStatus.ALL:
        raise HTTPException(422, f"Invalid status {status_!r}.")


async def _validate_refs(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    agent_id: Optional[uuid.UUID],
    knowledge_base_id: Optional[uuid.UUID],
) -> None:
    if agent_id is not None:
        ok = await session.scalar(
            select(Agent.id)
            .where(Agent.id == agent_id)
            .where(Agent.organization_id == organization_id)
            .where(Agent.deleted_at.is_(None))
        )
        if not ok:
            raise HTTPException(422, "agent_id not found in this organization.")
    if knowledge_base_id is not None:
        ok = await session.scalar(
            select(KnowledgeBase.id)
            .where(KnowledgeBase.id == knowledge_base_id)
            .where(KnowledgeBase.organization_id == organization_id)
            .where(KnowledgeBase.deleted_at.is_(None))
        )
        if not ok:
            raise HTTPException(422, "knowledge_base_id not found in this organization.")


async def _set_domains(
    session: AsyncSession, widget: Widget, domains: list[str]
) -> None:
    normalized = sorted(
        {d for d in (widget_service.normalize_domain(x) for x in domains) if d}
    )
    await session.execute(
        delete(WidgetDomain).where(WidgetDomain.widget_id == widget.id)
    )
    for d in normalized:
        session.add(WidgetDomain(widget_id=widget.id, domain=d))


# ─────────────────── CRUD ───────────────────

@router.post(
    "",
    response_model=WidgetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a widget",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def create_widget(
    payload: WidgetCreate,
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> WidgetRead:
    ctx = pctx.org
    _validate_enums(
        widget_type=payload.widget_type,
        position=payload.position,
        auth_mode=payload.auth_mode,
    )
    await _validate_refs(
        session,
        organization_id=ctx.organization_id,
        agent_id=payload.agent_id,
        knowledge_base_id=payload.knowledge_base_id,
    )

    widget = Widget(
        organization_id=ctx.organization_id,
        project_id=pctx.project_id,
        public_key=_gen_public_key(),
        name=payload.name,
        widget_type=payload.widget_type,
        position=payload.position,
        auth_mode=payload.auth_mode,
        agent_id=payload.agent_id,
        knowledge_base_id=payload.knowledge_base_id,
        theme=payload.theme.model_dump(),
        settings=payload.settings.model_dump(),
        status=WidgetStatus.draft,
    )
    session.add(widget)
    await session.flush()
    await _set_domains(session, widget, payload.domains)
    await session.commit()
    await session.refresh(widget)

    audit(
        "create",
        resource="widget",
        resource_id=str(widget.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"name": widget.name, "public_key": widget.public_key},
    )
    return await _read(session, widget)


@router.get("", response_model=WidgetListResponse, summary="List widgets")
async def list_widgets(
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> WidgetListResponse:
    ctx = pctx.org
    stmt = (
        select(Widget)
        .where(Widget.organization_id == ctx.organization_id)
        .where(Widget.project_id == pctx.project_id)
        .where(Widget.deleted_at.is_(None))
    )
    if q:
        stmt = stmt.where(Widget.name.ilike(f"%{q}%"))
    total = int(
        await session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        or 0
    )
    rows = (
        await session.scalars(stmt.order_by(Widget.created_at.desc()).limit(limit))
    ).all()
    items = [await _read(session, w) for w in rows]
    return WidgetListResponse(items=items, total=total)


@router.get("/{widget_id}", response_model=WidgetRead, summary="Get a widget")
async def get_widget(
    widget_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WidgetRead:
    widget = await _widget_for_org(
        session, widget_id=widget_id, organization_id=ctx.organization_id
    )
    if widget is None:
        raise HTTPException(404, "Widget not found.")
    return await _read(session, widget)


@router.put(
    "/{widget_id}",
    response_model=WidgetRead,
    summary="Update a widget",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def update_widget(
    widget_id: uuid.UUID,
    payload: WidgetUpdate,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WidgetRead:
    widget = await _widget_for_org(
        session, widget_id=widget_id, organization_id=ctx.organization_id
    )
    if widget is None:
        raise HTTPException(404, "Widget not found.")

    _validate_enums(
        widget_type=payload.widget_type,
        position=payload.position,
        auth_mode=payload.auth_mode,
        status_=payload.status,
    )
    await _validate_refs(
        session,
        organization_id=ctx.organization_id,
        agent_id=payload.agent_id,
        knowledge_base_id=payload.knowledge_base_id,
    )

    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "widget_type", "position", "auth_mode", "status"):
        if field in data and data[field] is not None:
            setattr(widget, field, data[field])
    if "agent_id" in data:
        widget.agent_id = data["agent_id"]
    if "knowledge_base_id" in data:
        widget.knowledge_base_id = data["knowledge_base_id"]
    if payload.theme is not None:
        widget.theme = payload.theme.model_dump()
    if payload.settings is not None:
        widget.settings = payload.settings.model_dump()
    if payload.domains is not None:
        await _set_domains(session, widget, payload.domains)

    await session.commit()
    await session.refresh(widget)
    audit(
        "update",
        resource="widget",
        resource_id=str(widget.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return await _read(session, widget)


@router.delete(
    "/{widget_id}",
    response_model=dict,
    summary="Delete a widget",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def delete_widget(
    widget_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    widget = await _widget_for_org(
        session, widget_id=widget_id, organization_id=ctx.organization_id
    )
    if widget is None:
        raise HTTPException(404, "Widget not found.")
    widget.deleted_at = widget_service.now_utc()
    widget.status = WidgetStatus.paused
    await session.commit()
    audit(
        "delete",
        resource="widget",
        resource_id=str(widget.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return {"detail": "Widget deleted."}


# ─────────────────── publish / key rotation ───────────────────

@router.post(
    "/{widget_id}/publish",
    response_model=WidgetRead,
    summary="Publish (or unpublish) a widget",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def publish_widget(
    widget_id: uuid.UUID,
    publish: bool = Query(default=True),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WidgetRead:
    widget = await _widget_for_org(
        session, widget_id=widget_id, organization_id=ctx.organization_id
    )
    if widget is None:
        raise HTTPException(404, "Widget not found.")
    widget.status = WidgetStatus.published if publish else WidgetStatus.paused
    widget.published_at = widget_service.now_utc() if publish else widget.published_at

    # Cloud-service behaviour: publishing a channel deploys its agent. If the
    # widget is bound to a ready agent that is still draft/paused, flip it to
    # active so the live widget actually answers — no separate "Start" step.
    if publish and widget.agent_id is not None:
        agent = await session.scalar(
            select(Agent)
            .options(selectinload(Agent.config))
            .where(Agent.id == widget.agent_id)
        )
        if (
            agent is not None
            and agent.deleted_at is None
            and agent.status in (AgentStatus.draft, AgentStatus.paused)
            and agent_lifecycle.is_ready(agent)
        ):
            agent.status = AgentStatus.active

    await session.commit()
    await session.refresh(widget)
    audit(
        "publish" if publish else "unpublish",
        resource="widget",
        resource_id=str(widget.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return await _read(session, widget)


@router.post(
    "/{widget_id}/regenerate-key",
    response_model=WidgetRead,
    summary="Rotate the widget's public embed key",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def regenerate_key(
    widget_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WidgetRead:
    widget = await _widget_for_org(
        session, widget_id=widget_id, organization_id=ctx.organization_id
    )
    if widget is None:
        raise HTTPException(404, "Widget not found.")
    widget.public_key = _gen_public_key()
    await session.commit()
    await session.refresh(widget)
    audit(
        "regenerate_key",
        resource="widget",
        resource_id=str(widget.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return await _read(session, widget)


# ─────────────────── analytics ───────────────────

@router.get(
    "/{widget_id}/analytics",
    response_model=WidgetAnalytics,
    summary="Usage analytics for a widget",
)
async def widget_analytics(
    widget_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WidgetAnalytics:
    widget = await _widget_for_org(
        session, widget_id=widget_id, organization_id=ctx.organization_id
    )
    if widget is None:
        raise HTTPException(404, "Widget not found.")

    sessions = int(
        await session.scalar(
            select(func.count(WidgetSession.id)).where(
                WidgetSession.widget_id == widget.id
            )
        )
        or 0
    )
    conversations = int(
        await session.scalar(
            select(func.count(WidgetSession.id))
            .where(WidgetSession.widget_id == widget.id)
            .where(WidgetSession.conversation_id.isnot(None))
        )
        or 0
    )
    messages = int(
        await session.scalar(
            select(func.coalesce(func.sum(WidgetSession.message_count), 0)).where(
                WidgetSession.widget_id == widget.id
            )
        )
        or 0
    )

    # Event counts grouped by type.
    rows = (
        await session.execute(
            select(WidgetEvent.event, func.count(WidgetEvent.id))
            .where(WidgetEvent.widget_id == widget.id)
            .group_by(WidgetEvent.event)
        )
    ).all()
    by_event = {ev: int(cnt) for ev, cnt in rows}

    # Average CSAT from feedback events.
    avg_csat = await session.scalar(
        select(func.avg(cast(WidgetEvent.event_metadata["rating"].astext, Float)))
        .where(WidgetEvent.widget_id == widget.id)
        .where(WidgetEvent.event == WidgetEventType.feedback)
    )

    return WidgetAnalytics(
        widget_id=widget.id,
        status=widget.status,
        sessions=sessions,
        conversations=conversations,
        messages=messages,
        opens=by_event.get(WidgetEventType.opened, 0),
        leads=by_event.get(WidgetEventType.lead, 0),
        escalations=by_event.get(WidgetEventType.escalation, 0),
        bookings=by_event.get(WidgetEventType.booking, 0),
        errors=by_event.get(WidgetEventType.error, 0),
        avg_csat=round(float(avg_csat), 2) if avg_csat is not None else None,
        by_event=by_event,
        top_questions=[],
    )
