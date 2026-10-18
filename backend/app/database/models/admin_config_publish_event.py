"""Audit record of one publish from the admin configuration console.

Holds key names and change types only. A value is never stored here, so the
history can be shown to any super-admin without exposing a secret.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class AdminConfigPublishEvent(UUIDPrimaryKeyMixin, Base):
    """One publish: who, when, why, and which keys changed."""

    __tablename__ = "admin_config_publish_events"

    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    published_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    published_by_email: Mapped[str] = mapped_column(String(320), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    # Each entry: {"name": "LOG_LEVEL", "change": "set" | "clear"}. No values.
    changes: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AdminConfigPublishEvent {self.environment} {self.published_at}>"
