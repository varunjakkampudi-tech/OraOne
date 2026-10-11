"""API key models (Phase 12, Module 9).

Programmatic access to the platform is authenticated with org-scoped API
keys. The full secret is shown to the user exactly once at creation time;
we persist only a SHA-256 hash plus a non-secret ``prefix`` used for lookup
and display. Keys carry a list of ``scopes`` that gate which external
endpoints they may call.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """An organization-scoped API key. ``deleted_at`` marks a revoked key."""

    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("prefix", name="uq_api_keys_prefix"),
        Index("ix_api_keys_organization_id", "organization_id"),
        Index("ix_api_keys_prefix", "prefix"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Public, non-secret identifier (e.g. "sk_ora_ab12cd34"). Used to look
    # up the row before verifying the hash; safe to display.
    prefix: Mapped[str] = mapped_column(String(40), nullable=False)
    # SHA-256 hex digest of the full secret.
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scopes: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ApiKey {self.prefix} org={self.organization_id}>"
