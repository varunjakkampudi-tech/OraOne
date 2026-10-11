"""Integration — third-party connections owned by an organization
(e.g. Meta WhatsApp Business, SendGrid, Salesforce…)."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.organization import Organization
    from app.database.models.knowledge_base import KnowledgeBase
    from app.database.models.sync_job import SyncJob


class IntegrationType(str, enum.Enum):
    sms = "sms"
    email = "email"
    whatsapp = "whatsapp"
    crm = "crm"
    calendar = "calendar"
    storage = "storage"
    analytics = "analytics"
    other = "other"


class IntegrationStatus(str, enum.Enum):
    disconnected = "disconnected"
    connected = "connected"
    syncing = "syncing"
    error = "error"


class ConnectionType(str, enum.Enum):
    oauth = "oauth"
    api_key = "api_key"
    mock = "mock"  # local/dev: deterministic demo data, no real provider


class SyncSchedule(str, enum.Enum):
    manual = "manual"
    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"


class Integration(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "provider", name="uq_integrations_org_provider"
        ),
        Index("ix_integrations_organization_id", "organization_id"),
        Index("ix_integrations_status", "status"),
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

    provider: Mapped[str] = mapped_column(String(60), nullable=False)
    # Five-category grouping for the UI (communication / documents /
    # documentation / development / crm). Stored as a free string so we
    # never need an ALTER TYPE to add a new category.
    category: Mapped[Optional[str]] = mapped_column(String(40))
    type: Mapped[IntegrationType] = mapped_column(
        Enum(IntegrationType, name="integration_type"), nullable=False
    )
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus, name="integration_status"),
        nullable=False,
        default=IntegrationStatus.disconnected,
    )

    connection_type: Mapped[ConnectionType] = mapped_column(
        Enum(ConnectionType, name="integration_connection_type"),
        nullable=False,
        default=ConnectionType.oauth,
    )

    # ── OAuth / credentials (encrypted at rest via app.core.crypto) ──
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    # Display only — e.g. the connected Google account email / Slack workspace.
    external_account: Mapped[Optional[str]] = mapped_column(String(255))

    # Where synced documents land. Created on first connect if absent.
    knowledge_base_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
    )
    sync_schedule: Mapped[SyncSchedule] = mapped_column(
        Enum(SyncSchedule, name="integration_sync_schedule"),
        nullable=False,
        default=SyncSchedule.manual,
    )

    # Non-sensitive settings (selected folder ids, toggles, cursors…).
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(String(1000))

    organization: Mapped["Organization"] = relationship(back_populates="integrations")
    knowledge_base: Mapped[Optional["KnowledgeBase"]] = relationship()
    sync_jobs: Mapped[list["SyncJob"]] = relationship(
        back_populates="integration", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Integration {self.provider} ({self.status})>"
