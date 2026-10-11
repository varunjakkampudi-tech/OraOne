"""Projects API — the workspace hierarchy between Organization and resources.

* ``GET    /api/projects``            — list projects in the org (+ counts).
* ``POST   /api/projects``            — create a project (owner/admin).
* ``GET    /api/projects/{id}``       — fetch one project (+ counts).
* ``PATCH  /api/projects/{id}``       — update name/desc/color/icon/status.
* ``DELETE /api/projects/{id}``       — soft-delete (blocked for default /
                                        non-empty projects).

The *active* project for resource endpoints is resolved separately by
``app.middleware.project_context.get_current_project`` from the
``X-Project-Id`` header.
"""
from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.api_key import ApiKey
from app.database.models.conversation import Conversation
from app.database.models.integration import Integration
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.project import Project, ProjectStatus
from app.database.models.website import Website
from app.database.models.widget import Widget
from app.database.models.workflow import Workflow
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_role,
)
from app.schemas.projects import (
    ProjectCreate,
    ProjectListResponse,
    ProjectRead,
    ProjectUpdate,
)
from app.services.audit import audit

router = APIRouter(tags=["projects"])

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Resource models counted per project. Deleting a project is blocked while
# any of these still reference it.
_COUNT_MODELS: dict[str, type] = {
    "agents": Agent,
    "knowledge_bases": KnowledgeBase,
    "conversations": Conversation,
    "workflows": Workflow,
    "websites": Website,
    "widgets": Widget,
    "integrations": Integration,
    "api_keys": ApiKey,
}


def _slugify(value: str) -> str:
    s = _SLUG_RE.sub("-", (value or "").strip().lower()).strip("-")
    return s[:80] or "project"


async def _resource_counts(
    session: AsyncSession, project_id: uuid.UUID
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, model in _COUNT_MODELS.items():
        q = (
            select(func.count())
            .select_from(model)
            .where(model.project_id == project_id)
        )
        if hasattr(model, "deleted_at"):
            q = q.where(model.deleted_at.is_(None))
        counts[key] = int(await session.scalar(q) or 0)
    return counts


def _to_read(p: Project, counts: dict[str, int] | None = None) -> ProjectRead:
    read = ProjectRead.model_validate(p)
    if counts is not None:
        read.resource_counts = counts
    return read


async def _unique_slug(
    session: AsyncSession, org_id: uuid.UUID, desired: str
) -> str:
    """Return ``desired`` or ``desired-2`` / ``-3`` … if it collides."""
    base = _slugify(desired)
    candidate = base
    suffix = 2
    while True:
        clash = await session.scalar(
            select(Project.id)
            .where(Project.organization_id == org_id)
            .where(Project.slug == candidate)
            .where(Project.deleted_at.is_(None))
        )
        if clash is None:
            return candidate
        candidate = f"{base[:76]}-{suffix}"
        suffix += 1


@router.get("/api/projects", response_model=ProjectListResponse)
async def list_projects(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    rows = (
        await session.scalars(
            select(Project)
            .where(Project.organization_id == ctx.organization_id)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.is_default.desc(), Project.created_at.asc())
        )
    ).all()
    items = [_to_read(p, await _resource_counts(session, p.id)) for p in rows]
    return ProjectListResponse(items=items, total=len(items))


@router.post(
    "/api/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    payload: ProjectCreate,
    ctx: OrgContext = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_db),
) -> ProjectRead:
    slug = await _unique_slug(session, ctx.organization_id, payload.slug or payload.name)
    proj = Project(
        organization_id=ctx.organization_id,
        name=payload.name.strip(),
        slug=slug,
        description=payload.description,
        color=payload.color,
        icon=payload.icon,
        is_default=False,
        status=ProjectStatus.active,
        created_by_user_id=ctx.user_id,
    )
    session.add(proj)
    await session.flush()
    await session.commit()
    await session.refresh(proj)
    audit(
        "create",
        resource="project",
        resource_id=str(proj.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"name": proj.name, "slug": proj.slug},
    )
    return _to_read(proj, {k: 0 for k in _COUNT_MODELS})


@router.get("/api/projects/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> ProjectRead:
    proj = await session.scalar(
        select(Project)
        .where(Project.id == project_id)
        .where(Project.organization_id == ctx.organization_id)
        .where(Project.deleted_at.is_(None))
    )
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return _to_read(proj, await _resource_counts(session, proj.id))


@router.patch("/api/projects/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    ctx: OrgContext = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_db),
) -> ProjectRead:
    proj = await session.scalar(
        select(Project)
        .where(Project.id == project_id)
        .where(Project.organization_id == ctx.organization_id)
        .where(Project.deleted_at.is_(None))
    )
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    if payload.name is not None:
        proj.name = payload.name.strip()
    if payload.description is not None:
        proj.description = payload.description
    if payload.color is not None:
        proj.color = payload.color
    if payload.icon is not None:
        proj.icon = payload.icon
    if payload.status is not None:
        if proj.is_default and payload.status == "archived":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The default project cannot be archived.",
            )
        proj.status = ProjectStatus(payload.status)
    if payload.settings is not None:
        proj.settings = payload.settings

    await session.commit()
    await session.refresh(proj)
    audit(
        "update",
        resource="project",
        resource_id=str(proj.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"name": proj.name, "status": proj.status.value},
    )
    return _to_read(proj, await _resource_counts(session, proj.id))


@router.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: uuid.UUID,
    ctx: OrgContext = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    proj = await session.scalar(
        select(Project)
        .where(Project.id == project_id)
        .where(Project.organization_id == ctx.organization_id)
        .where(Project.deleted_at.is_(None))
    )
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    if proj.is_default:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The default project cannot be deleted.",
        )

    counts = await _resource_counts(session, proj.id)
    in_use = {k: v for k, v in counts.items() if v > 0}
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Project is not empty. Move or delete its resources first: "
                + ", ".join(f"{k}={v}" for k, v in in_use.items())
            ),
        )

    from datetime import datetime, timezone

    proj.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    audit(
        "delete",
        resource="project",
        resource_id=str(proj.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        before={"name": proj.name, "slug": proj.slug},
    )
    return {"status": "deleted", "id": str(proj.id)}
