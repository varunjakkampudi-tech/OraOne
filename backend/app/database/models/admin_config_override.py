"""Encrypted configuration values written from the admin configuration console.

One row per (environment, key). ``value_encrypted`` is produced by
:func:`app.core.crypto.encrypt`; plaintext is never stored. Clearing an
override deletes the row, so the environment's own value applies again.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class AdminConfigOverride(UUIDPrimaryKeyMixin, Base):
    """One encrypted console-managed configuration value for one environment."""

    __tablename__ = "admin_config_overrides"
    __table_args__ = (
        UniqueConstraint(
            "environment", "name", name="uq_admin_config_overrides_env_name"
        ),
    )

    environment: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
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
        return f"<AdminConfigOverride {self.environment}:{self.name}>"
