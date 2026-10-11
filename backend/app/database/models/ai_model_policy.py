"""AI model routing policy (Phase 12, Module 13).

One row per organization captures how the model router should behave: the
preferred default model, an ordered fallback chain, and any models the org
has explicitly disabled. Entitlement (which models a plan *may* use) is
derived from the billing plan + catalogue, not stored here.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AIModelPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-org model routing preferences."""

    __tablename__ = "ai_model_policies"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_ai_model_policies_org"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    default_model: Mapped[str] = mapped_column(String(80), nullable=False)
    fallback_models: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    disabled_models: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AIModelPolicy org={self.organization_id} default={self.default_model}>"
