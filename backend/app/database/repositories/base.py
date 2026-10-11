"""Base async repository with common CRUD helpers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic CRUD repository.

    Subclasses set `model` to a concrete SQLAlchemy model class. Methods
    here are intentionally minimal — domain-specific lookups belong on
    subclasses.
    """

    model: Type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- read ----
    async def get(self, id_: uuid.UUID) -> Optional[ModelT]:
        return await self.session.get(self.model, id_)

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        q = select(self.model).limit(limit).offset(offset)
        # Exclude soft-deleted rows when the column exists.
        if hasattr(self.model, "deleted_at"):
            q = q.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return (await self.session.scalars(q)).all()

    # ---- write ----
    async def add(self, obj: ModelT, *, flush: bool = True) -> ModelT:
        self.session.add(obj)
        if flush:
            await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        """Soft-delete if the model has `deleted_at`, else hard-delete."""
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]
            await self.session.flush()
            return
        await self.session.delete(obj)
        await self.session.flush()

    async def hard_delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()
