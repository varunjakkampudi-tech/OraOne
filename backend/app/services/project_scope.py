"""Resolve the project a customer-facing request belongs to.

Every knowledge lookup and visitor-memory operation must run inside exactly one
project. Callers pass the project they were given (a widget, an API key, a
message channel, or the dashboard's project header). When a resource predates
projects and has no project, the organization's default project is used. This
is the same rule the project-context middleware applies to dashboard requests.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.project import Project


class ProjectScopeError(RuntimeError):
    """The organization has no usable project to scope a request to."""


async def default_project_id(
    session: AsyncSession, organization_id: uuid.UUID
) -> uuid.UUID:
    """The organization's default project, else its newest active project."""
    project_id = await session.scalar(
        select(Project.id)
        .where(Project.organization_id == organization_id)
        .where(Project.deleted_at.is_(None))
        .where(Project.is_default.is_(True))
        .limit(1)
    )
    if project_id is None:
        project_id = await session.scalar(
            select(Project.id)
            .where(Project.organization_id == organization_id)
            .where(Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
            .limit(1)
        )
    if project_id is None:
        raise ProjectScopeError("organization has no project")
    return project_id


async def resolve_project_id(
    session: AsyncSession,
    organization_id: uuid.UUID,
    project_id: uuid.UUID | None,
) -> uuid.UUID:
    """Use the explicit project when given, else the organization default."""
    if project_id is not None:
        return project_id
    return await default_project_id(session, organization_id)
