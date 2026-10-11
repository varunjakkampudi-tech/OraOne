"""White-label branding (Phase 12, Module 15).

One row per organization holds the customer-facing brand identity used to
white-label the dashboard and any public-facing surfaces (chat widget,
invite pages). Premium controls (hiding the "Powered by" mark, custom
domains) are gated by plan at the service layer.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrgBranding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-org white-label brand settings."""

    __tablename__ = "org_branding"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_org_branding_org"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    brand_name: Mapped[Optional[str]] = mapped_column(String(120))
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    icon_url: Mapped[Optional[str]] = mapped_column(String(500))
    primary_color: Mapped[str] = mapped_column(
        String(9), nullable=False, default="#4F46E5", server_default="#4F46E5"
    )
    accent_color: Mapped[str] = mapped_column(
        String(9), nullable=False, default="#06B6D4", server_default="#06B6D4"
    )
    support_email: Mapped[Optional[str]] = mapped_column(String(160))
    support_url: Mapped[Optional[str]] = mapped_column(String(500))
    custom_domain: Mapped[Optional[str]] = mapped_column(String(255))
    hide_powered_by: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrgBranding org={self.organization_id}>"
