"""Project-scoped repository mixin.

Extends :class:`OrgScopedRepository` to additionally pin every query to a
single ``project_id``. Use this for resources that live inside a project
(agents, knowledge bases, conversations, workflows, websites, widgets,
integrations, webhooks, api keys, …).

The concrete model must expose both ``organization_id`` and ``project_id``
columns — asserted at construction so misuse fails loudly.
"""
from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.org_scoped import OrgScopedRepository
from app.database.repositories.base import ModelT
from app.middleware.project_context import ProjectContext


class ProjectScopedRepository(OrgScopedRepository[ModelT]):
    """OrgScopedRepository variant that also scopes to one project."""

    def __init__(self, session: AsyncSession, pctx: ProjectContext) -> None:
        # Build the org-scoped base from the project context's org fields.
        super().__init__(session, pctx.org)
        if not hasattr(self.model, "project_id"):
            raise TypeError(
                f"{self.model.__name__} has no `project_id` column and "
                f"cannot be project-scoped."
            )
        self.pctx = pctx
        self.project_id: uuid.UUID = pctx.project_id

    # ---- read ----
    async def get_in_project(self, id_: uuid.UUID) -> Optional[ModelT]:
        q = (
            select(self.model)
            .where(self.model.id == id_)  # type: ignore[attr-defined]
            .where(self.model.organization_id == self.organization_id)  # type: ignore[attr-defined]
            .where(self.model.project_id == self.project_id)  # type: ignore[attr-defined]
        )
        if hasattr(self.model, "deleted_at"):
            q = q.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return await self.session.scalar(q)

    async def list_in_project(
        self, *, limit: int = 100, offset: int = 0
    ) -> Sequence[ModelT]:
        q = (
            select(self.model)
            .where(self.model.organization_id == self.organization_id)  # type: ignore[attr-defined]
            .where(self.model.project_id == self.project_id)  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        if hasattr(self.model, "deleted_at"):
            q = q.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        if hasattr(self.model, "created_at"):
            q = q.order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
        return (await self.session.scalars(q)).all()

    # ---- write ----
    async def add_for_project(self, obj: ModelT, *, flush: bool = True) -> ModelT:
        """Pin a fresh instance to this org + project before persisting."""
        existing_proj = getattr(obj, "project_id", None)
        if existing_proj not in (None, self.project_id):
            raise PermissionError(
                f"Refusing to persist {self.model.__name__} into project "
                f"{self.project_id!r}: payload claims project {existing_proj!r}."
            )
        obj.project_id = self.project_id  # type: ignore[attr-defined]
        return await self.add_for_org(obj, flush=flush)
