"""Org-scoped repository mixin (Phase 5).

`OrgScopedRepository` is a `BaseRepository` subclass that *always* filters
by `organization_id`. It is the single place where tenant scope is
enforced at the repository layer, so concrete repos can't accidentally
forget the filter on a one-off query.

This is also the seam we'll use to switch over to Postgres Row-Level
Security in Phase 6: once RLS policies are live, the `organization_id`
filter becomes belt-and-braces (RLS will enforce it at the DB level)
and the session-stamp set by ``apply_rls_on_session()`` in
``app.middleware.org_context`` takes over as the real source of truth.

Until then, every business-domain repo *must* extend this class and
*must* be constructed with an ``OrgContext`` (not just an
``AsyncSession``). Routes get the context from the
``get_current_organization`` dependency.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.base import BaseRepository, ModelT
from app.middleware.org_context import OrgContext


class OrgScopedRepository(BaseRepository[ModelT]):
    """BaseRepository variant that scopes every read/write to one org.

    Subclasses inherit ``get_in_org`` / ``list_in_org`` / soft-delete
    helpers that always pin the query to ``self.organization_id``.

    The concrete model must expose an ``organization_id`` column — this
    is asserted at construction time so misuse fails loudly.
    """

    def __init__(self, session: AsyncSession, ctx: OrgContext) -> None:
        super().__init__(session)
        if not hasattr(self.model, "organization_id"):
            raise TypeError(
                f"{self.model.__name__} has no `organization_id` column "
                f"and cannot be tenant-scoped."
            )
        self.ctx = ctx
        self.organization_id: uuid.UUID = ctx.organization_id

    # ---- read ----
    async def get_in_org(self, id_: uuid.UUID) -> Optional[ModelT]:
        """`session.get`-style fetch, but 404-able for cross-tenant ids.

        Returns ``None`` if the row exists but belongs to a different
        organization — never raises a leak.
        """
        q = select(self.model).where(self.model.id == id_).where(  # type: ignore[attr-defined]
            self.model.organization_id == self.organization_id  # type: ignore[attr-defined]
        )
        if hasattr(self.model, "deleted_at"):
            q = q.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return await self.session.scalar(q)

    async def list_in_org(
        self, *, limit: int = 100, offset: int = 0
    ) -> Sequence[ModelT]:
        q = (
            select(self.model)
            .where(self.model.organization_id == self.organization_id)  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        if hasattr(self.model, "deleted_at"):
            q = q.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        if hasattr(self.model, "created_at"):
            q = q.order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
        return (await self.session.scalars(q)).all()

    # ---- write ----
    async def add_for_org(self, obj: ModelT, *, flush: bool = True) -> ModelT:
        """Pin a fresh instance to this org before persisting.

        Refuses to insert a row whose ``organization_id`` was set to a
        different org by the caller — that's the only place where tenant
        spoofing could sneak in at the write path.
        """
        existing = getattr(obj, "organization_id", None)
        if existing not in (None, self.organization_id):
            raise PermissionError(
                f"Refusing to persist {self.model.__name__} into "
                f"organization {self.organization_id!r}: payload claims "
                f"organization {existing!r}."
            )
        obj.organization_id = self.organization_id  # type: ignore[attr-defined]
        self.session.add(obj)
        if flush:
            await self.session.flush()
        return obj

    async def soft_delete_in_org(self, id_: uuid.UUID) -> bool:
        """Mark a row as deleted, but only if it belongs to this org."""
        obj = await self.get_in_org(id_)
        if obj is None:
            return False
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]
            await self.session.flush()
            return True
        await self.session.delete(obj)
        await self.session.flush()
        return True
