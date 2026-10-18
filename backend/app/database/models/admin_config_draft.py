"""Pending configuration change saved from the admin console (not yet active).

One row per (environment, key). ``action`` is ``set`` with an encrypted value,
or ``clear`` with no value. Publishing copies drafts into
``admin_config_overrides`` and deletes them. Discarding deletes the row.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class AdminConfigDraft(UUIDPrimaryKeyMixin, Base):
    """One unpublished console change for one environment and key."""

    __tablename__ = "admin_config_drafts"
    __table_args__ = (
        UniqueConstraint("environment", "name", name="uq_admin_config_drafts_env_name"),
    )

    environment: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    value_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AdminConfigDraft {self.environment}:{self.name}:{self.action}>"
