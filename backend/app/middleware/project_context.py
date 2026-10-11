"""Project-context middleware — resolves the *active project* for a request.

Sits on top of :mod:`app.middleware.org_context`. The org is resolved
server-side from membership (the tenant boundary); the **project** is the
sub-workspace the request operates on.

Resolution order:
  1. ``X-Project-Id`` request header, if present — validated to belong to
     the caller's organization and not soft-deleted (else 404).
  2. Otherwise the organization's ``is_default`` project.
  3. Otherwise the most recently created active project (defensive
     fallback for orgs created before the projects backfill ran).

Downstream endpoints depend on :func:`get_current_project` to get a
``ProjectContext`` carrying both the verified org and project ids.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.project import Project, ProjectStatus
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization

log = logging.getLogger("app.project_context")


@dataclass(frozen=True)
class ProjectContext:
    """Verified org + active-project scope for the current request."""

    user_id: uuid.UUID
    organization_id: uuid.UUID
    membership_role: str
    project_id: uuid.UUID
    project_slug: str
    is_default_project: bool

    @property
    def org(self) -> "OrgContext":  # convenience for code that wants org fields
        return OrgContext(
            user_id=self.user_id,
            cognito_sub="",
            organization_id=self.organization_id,
            membership_role=self.membership_role,
        )


async def _resolve_project(
    session: AsyncSession,
    organization_id: uuid.UUID,
    requested_id: Optional[str],
) -> Optional[Project]:
    """Pick the active project for this request (see module docstring)."""
    if requested_id:
        try:
            pid = uuid.UUID(requested_id)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Project-Id header.",
            )
        proj = await session.scalar(
            select(Project)
            .where(Project.id == pid)
            .where(Project.organization_id == organization_id)
            .where(Project.deleted_at.is_(None))
        )
        if proj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found in this organization.",
            )
        return proj

    # No header → default project, else newest active project.
    proj = await session.scalar(
        select(Project)
        .where(Project.organization_id == organization_id)
        .where(Project.deleted_at.is_(None))
        .where(Project.is_default.is_(True))
    )
    if proj is not None:
        return proj
    return await session.scalar(
        select(Project)
        .where(Project.organization_id == organization_id)
        .where(Project.deleted_at.is_(None))
        .where(Project.status == ProjectStatus.active)
        .order_by(Project.created_at.desc())
        .limit(1)
    )


async def get_current_project(
    request: Request,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
    x_project_id: Optional[str] = Header(default=None, alias="X-Project-Id"),
) -> ProjectContext:
    """FastAPI dependency that returns a verified ``ProjectContext``."""
    proj = await _resolve_project(session, ctx.organization_id, x_project_id)
    if proj is None:
        # Should never happen post-backfill, but never serve cross-tenant
        # data without a project scope.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No project exists for this organization. Create one via "
                "POST /api/projects, then retry."
            ),
        )

    pctx = ProjectContext(
        user_id=ctx.user_id,
        organization_id=ctx.organization_id,
        membership_role=ctx.membership_role,
        project_id=proj.id,
        project_slug=proj.slug,
        is_default_project=proj.is_default,
    )
    request.state.project_context = pctx
    log.info(
        "project_context org=%s project=%s default=%s path=%s",
        pctx.organization_id, pctx.project_id, pctx.is_default_project,
        request.url.path,
    )
    return pctx


async def get_current_project_id(
    pctx: ProjectContext = Depends(get_current_project),
) -> uuid.UUID:
    """Convenience: just the active project UUID."""
    return pctx.project_id
