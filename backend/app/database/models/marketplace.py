"""Marketplace models (Phase Z).

The marketplace catalogue itself is curated in code
(:mod:`app.services.marketplace`) so it needs no table. We only persist what
a tenant has **installed** — one row per install, scoped to the org/project,
optionally linked to the Agent it provisioned.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InstallStatus:
    installed = "installed"
    removed = "removed"
    ALL = {installed, removed}


class MarketplaceInstallation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A catalogue listing a tenant has installed into a project."""

    __tablename__ = "marketplace_installations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    installed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    listing_slug: Mapped[str] = mapped_column(String(120), nullable=False)
    listing_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="agent_template")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=InstallStatus.installed)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_marketplace_installations_organization_id", "organization_id"),
        Index("ix_marketplace_installations_listing_slug", "listing_slug"),
    )
