"""Agent CRUD API — Phase 6.

Replaces the legacy Mongo-backed ``/api/agents`` routes in ``server.py``
with the Postgres system-of-record. All endpoints are:

* Organization-scoped (Phase 5 ``OrgContext`` is the only source of truth).
* Soft-delete aware (``deleted_at``).
* Paginated (``limit`` / ``offset``).
* Searchable (``q`` matches name + description).
* Filterable (``type``, ``status``, ``model``).
* Audit-logged (one record per write).
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.agent import Agent, AgentStatus, AgentType
from app.database.models.agent_config import AgentConfig
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_role,
)
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.agents import (
    AgentCreate,
    AgentListResponse,
    AgentRead,
    AgentUpdate,
)
from app.services.audit import audit
from app.services import usage_service
from app.services import agent_lifecycle
from app.services import agent_website_service


router = APIRouter(prefix="/api/agents", tags=["agents"])


# ─────────────────────────── helpers ───────────────────────────

# Default knobs for newly-created AgentConfig sidecars when the caller
# doesn't override them. Mirrors the column defaults so the response
# shape is consistent whether or not config fields were posted.
_DEFAULT_TEMPERATURE = 0.70
_DEFAULT_LANGUAGE = "en-US"


def _to_read_model(agent: Agent) -> AgentRead:
    """Flatten Agent + AgentConfig into the single response shape."""
    cfg = agent.config  # 1:1 relationship — may be None on legacy rows
    return AgentRead(
        id=agent.id,
        organization_id=agent.organization_id,
        name=agent.name,
        description=agent.description,
        type=agent.type.value,
        status=agent.status.value,
        model=agent.model,
        avatar_url=agent.avatar_url,
        system_prompt=cfg.system_prompt if cfg else None,
        temperature=float(cfg.temperature) if cfg else _DEFAULT_TEMPERATURE,
        voice=cfg.voice if cfg else None,
        language=cfg.language if cfg else _DEFAULT_LANGUAGE,
        greeting=cfg.greeting if cfg else None,
        max_tokens=cfg.max_tokens if cfg else 1024,
        website_url=(cfg.config.get("website_url") if cfg and isinstance(cfg.config, dict) else None),
        is_ready=agent_lifecycle.is_ready(agent),
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def _snapshot(agent: Agent) -> dict:
    cfg = agent.config
    return {
        "name": agent.name,
        "type": agent.type.value,
        "status": agent.status.value,
        "model": agent.model,
        "description": agent.description,
        "system_prompt": cfg.system_prompt if cfg else None,
        "temperature": float(cfg.temperature) if cfg else None,
        "voice": cfg.voice if cfg else None,
        "language": cfg.language if cfg else None,
    }


def _parse_enum(enum_cls, value, *, field: str):
    try:
        return enum_cls(value)
    except ValueError as e:
        valid = ", ".join(repr(m.value) for m in enum_cls)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field} {value!r}. Allowed: {valid}.",
        ) from e


async def _load_for_org(
    session: AsyncSession, *, agent_id: uuid.UUID, organization_id: uuid.UUID
) -> Optional[Agent]:
    """Fetch a non-deleted Agent + its config, scoped to the org."""
    q = (
        select(Agent)
        .options(selectinload(Agent.config))
        .where(Agent.id == agent_id)
        .where(Agent.organization_id == organization_id)
        .where(Agent.deleted_at.is_(None))
    )
    return await session.scalar(q)


# ─────────────────────────── routes ────────────────────────────

@router.get(
    "",
    response_model=AgentListResponse,
    summary="List agents",
    description=(
        "Paginated list of agents in the caller's organization. "
        "Supports free-text search across `name` and `description`, "
        "and exact filters for `type`, `status`, and `model`. "
        "Soft-deleted agents are excluded."
    ),
)
async def list_agents(
    q: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Search by name or description (case-insensitive, substring).",
    ),
    type_: Optional[str] = Query(default=None, alias="type", description="Filter by AgentType."),
    status_: Optional[str] = Query(default=None, alias="status", description="Filter by AgentStatus."),
    model: Optional[str] = Query(default=None, description="Filter by LLM model (exact match)."),
    limit: int = Query(default=20, ge=1, le=100, description="Page size (1-100)."),
    offset: int = Query(default=0, ge=0, description="Page offset."),
    sort: str = Query(
        default="-created_at",
        pattern="^-?(created_at|updated_at|name)$",
        description="Sort field. Prefix with `-` for descending.",
    ),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> AgentListResponse:
    ctx = pctx.org
    base_filters = [
        Agent.organization_id == ctx.organization_id,
        Agent.project_id == pctx.project_id,
        Agent.deleted_at.is_(None),
    ]
    if type_:
        base_filters.append(Agent.type == _parse_enum(AgentType, type_, field="type"))
    if status_:
        base_filters.append(
            Agent.status == _parse_enum(AgentStatus, status_, field="status")
        )
    if model:
        base_filters.append(Agent.model == model)
    if q:
        like = f"%{q.strip()}%"
        base_filters.append(or_(Agent.name.ilike(like), Agent.description.ilike(like)))

    total = await session.scalar(
        select(func.count(Agent.id)).where(*base_filters)
    ) or 0

    # Sort
    sort_field = sort.lstrip("-")
    sort_dir = desc if sort.startswith("-") else asc
    col = {
        "created_at": Agent.created_at,
        "updated_at": Agent.updated_at,
        "name": Agent.name,
    }[sort_field]

    rows = (
        await session.scalars(
            select(Agent)
            .options(selectinload(Agent.config))
            .where(*base_filters)
            .order_by(sort_dir(col))
            .limit(limit)
            .offset(offset)
        )
    ).all()

    audit(
        "read",
        resource="agent",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={
            "q": q, "type": type_, "status": status_, "model": model,
            "limit": limit, "offset": offset, "sort": sort, "returned": len(rows),
            "total": total,
        },
    )

    return AgentListResponse(
        items=[_to_read_model(a) for a in rows],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=AgentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an agent",
    description="Create a new agent and its 1:1 `agent_configs` sidecar in a single transaction.",
)
async def create_agent(
    payload: AgentCreate,
    background: BackgroundTasks,
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> AgentRead:
    ctx = pctx.org
    agent_type = _parse_enum(AgentType, payload.type, field="type")
    agent_status = (
        _parse_enum(AgentStatus, payload.status, field="status")
        if payload.status else AgentStatus.draft
    )

    # Phase 12 Module 2: enforce the plan's agent quota before creating.
    await usage_service.enforce_quota(session, ctx.organization_id, "agents")

    agent = Agent(
        organization_id=ctx.organization_id,
        project_id=pctx.project_id,
        name=payload.name,
        description=payload.description,
        type=agent_type,
        status=agent_status,
        model=payload.model or "gpt-4o-mini",
        avatar_url=payload.avatar_url,
        created_by_user_id=ctx.user_id,
    )
    session.add(agent)
    await session.flush()  # populate agent.id

    cfg = AgentConfig(
        agent_id=agent.id,
        system_prompt=payload.system_prompt,
        temperature=payload.temperature if payload.temperature is not None else _DEFAULT_TEMPERATURE,
        voice=payload.voice,
        language=payload.language or _DEFAULT_LANGUAGE,
        greeting=payload.greeting,
        max_tokens=payload.max_tokens if payload.max_tokens is not None else 1024,
        config={"website_url": payload.website_url.strip()} if payload.website_url else {},
    )
    session.add(cfg)
    await session.flush()
    # Make the relationship visible to the response serializer in this txn.
    agent.config = cfg

    await session.commit()
    # Re-load to get DB-side defaults (created_at, updated_at).
    agent = await _load_for_org(session, agent_id=agent.id, organization_id=ctx.organization_id)
    assert agent is not None

    # If a website was supplied at creation, start crawling it into a knowledge
    # base right away so the agent begins learning from the site immediately.
    # Best-effort: agent creation must never fail because the crawl couldn't
    # start. update_agent's activation path dedupes on the same site, so an
    # agent created here and activated later won't crawl twice.
    if payload.website_url and payload.website_url.strip():
        try:
            await agent_website_service.provision_website_crawl(
                session, agent, payload.website_url.strip(), background
            )
        except Exception as exc:  # noqa: BLE001 — creation must survive crawl setup errors
            import logging

            logging.getLogger("app.agents").warning(
                "website crawl provisioning failed for new agent %s: %s", agent.id, exc
            )
        agent = await _load_for_org(session, agent_id=agent.id, organization_id=ctx.organization_id)
        assert agent is not None

    audit(
        "create",
        resource="agent",
        resource_id=str(agent.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after=_snapshot(agent),
    )
    return _to_read_model(agent)


@router.get(
    "/models",
    summary="List AI models this organization can assign to an agent",
)
async def list_agent_models(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Member-readable model picker source for the agent builder.

    Returns the org's usable models (entitled by plan and not org-disabled)
    plus the policy default. Adding a model to the backend catalogue makes it
    appear here automatically — no per-agent config migration needed.
    """
    from app.services import model_router_service

    view = await model_router_service.router_view(session, ctx.organization_id)
    models = [
        {
            "id": m["id"],
            "label": m["label"],
            "provider": m["provider"],
            "tier": m["tier"],
            "enabled": bool(m["enabled"]),
        }
        for m in view["models"]
        if m["enabled"]
    ]
    return {"models": models, "default_model": view["default_model"]}


@router.get(
    "/{agent_id}",
    response_model=AgentRead,
    summary="Get one agent",
)
async def get_agent(
    agent_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> AgentRead:
    agent = await _load_for_org(session, agent_id=agent_id, organization_id=ctx.organization_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")
    return _to_read_model(agent)


@router.put(
    "/{agent_id}",
    response_model=AgentRead,
    summary="Update an agent",
    description=(
        "Partial update — any omitted field is left unchanged. "
        "Updates to `system_prompt`, `temperature`, `voice`, `language`, "
        "`greeting`, or `max_tokens` are applied to the 1:1 `agent_configs` row."
    ),
)
async def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    background: BackgroundTasks,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> AgentRead:
    agent = await _load_for_org(session, agent_id=agent_id, organization_id=ctx.organization_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    before = _snapshot(agent)
    previous_status = agent.status

    # Agent fields
    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description
    if payload.type is not None:
        agent.type = _parse_enum(AgentType, payload.type, field="type")
    if payload.model is not None:
        agent.model = payload.model
    if payload.avatar_url is not None:
        agent.avatar_url = payload.avatar_url

    # Status is applied AFTER config changes below, so an activation request
    # that arrives together with a freshly-set system prompt is judged against
    # the new config.
    requested_status = (
        _parse_enum(AgentStatus, payload.status, field="status")
        if payload.status is not None
        else None
    )

    # Config fields — ensure the sidecar exists for legacy rows.
    cfg = agent.config
    cfg_changed = (
        payload.system_prompt is not None
        or payload.temperature is not None
        or payload.voice is not None
        or payload.language is not None
        or payload.greeting is not None
        or payload.max_tokens is not None
        or payload.website_url is not None
    )
    if cfg_changed and cfg is None:
        cfg = AgentConfig(agent_id=agent.id)
        session.add(cfg)
        agent.config = cfg
    if cfg is not None:
        if payload.system_prompt is not None:
            cfg.system_prompt = payload.system_prompt
        if payload.temperature is not None:
            cfg.temperature = payload.temperature
        if payload.voice is not None:
            cfg.voice = payload.voice
        if payload.language is not None:
            cfg.language = payload.language
        if payload.greeting is not None:
            cfg.greeting = payload.greeting
        if payload.max_tokens is not None:
            cfg.max_tokens = payload.max_tokens
        if payload.website_url is not None:
            # Reassign (not mutate) so SQLAlchemy flags the JSONB dirty.
            cfg.config = {**(cfg.config or {}), "website_url": payload.website_url.strip()}

    # Apply the requested status now that config reflects this update.
    # An agent can only become Active once it meets the minimum requirements.
    if requested_status is not None:
        if requested_status == AgentStatus.active and not agent_lifecycle.is_ready(agent):
            missing = agent_lifecycle.missing_requirements(agent)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Agent is incomplete — add "
                    + ", ".join(missing)
                    + " before activating."
                ),
            )
        agent.status = requested_status

    await session.commit()
    agent = await _load_for_org(session, agent_id=agent.id, organization_id=ctx.organization_id)
    assert agent is not None

    # On the draft/paused → active transition, auto-crawl the agent's website
    # (if any) into a knowledge base. Best-effort: never blocks activation.
    became_active = (
        requested_status == AgentStatus.active and previous_status != AgentStatus.active
    )
    if became_active and agent.config and isinstance(agent.config.config, dict):
        site = agent.config.config.get("website_url")
        if site:
            try:
                await agent_website_service.provision_website_crawl(
                    session, agent, site, background
                )
            except Exception as exc:  # noqa: BLE001 — deploy must survive crawl setup errors
                import logging

                logging.getLogger("app.agents").warning(
                    "website crawl provisioning failed for agent %s: %s", agent.id, exc
                )
            agent = await _load_for_org(session, agent_id=agent.id, organization_id=ctx.organization_id)
            assert agent is not None

    audit(
        "update",
        resource="agent",
        resource_id=str(agent_id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        before=before,
        after=_snapshot(agent),
    )
    return _to_read_model(agent)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Soft-delete an agent",
    description="Sets `deleted_at`. Owner / admin role required.",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def delete_agent(
    agent_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Response:
    agent = await _load_for_org(session, agent_id=agent_id, organization_id=ctx.organization_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found.")

    from datetime import datetime, timezone
    before = _snapshot(agent)
    agent.deleted_at = datetime.now(timezone.utc)
    await session.commit()

    audit(
        "delete",
        resource="agent",
        resource_id=str(agent_id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        before=before,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
