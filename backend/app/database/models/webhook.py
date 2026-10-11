"""Developer webhook models (R7).

Outbound, org-scoped webhooks let third-party systems react to OraOne events
(conversation created, document processed, workflow finished, …) instead of
polling. Each endpoint has its own signing ``secret``; deliveries are signed
with an HMAC-SHA256 signature so receivers can verify authenticity.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class WebhookEventType:
    """Catalogue of events an endpoint may subscribe to."""

    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_FINISHED = "conversation.finished"
    MESSAGE_CREATED = "message.created"
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    WEBSITE_CRAWLED = "website.crawled"
    WORKFLOW_FINISHED = "workflow.finished"
    INTEGRATION_SYNCED = "integration.synced"
    LEAD_GENERATED = "lead.generated"
    WIDGET_INSTALLED = "widget.installed"
    WIDGET_ESCALATION = "widget.escalation"

    ALL = (
        CONVERSATION_CREATED,
        CONVERSATION_FINISHED,
        MESSAGE_CREATED,
        DOCUMENT_UPLOADED,
        DOCUMENT_PROCESSED,
        WEBSITE_CRAWLED,
        WORKFLOW_FINISHED,
        INTEGRATION_SYNCED,
        LEAD_GENERATED,
        WIDGET_INSTALLED,
        WIDGET_ESCALATION,
    )


class WebhookStatus:
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"  # auto-disabled after repeated failures
    ALL = (ACTIVE, PAUSED, DISABLED)


class WebhookEndpoint(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "webhook_endpoints"
    __table_args__ = (
        Index("ix_webhook_endpoints_organization_id", "organization_id"),
        Index("ix_webhook_endpoints_status", "status"),
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
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    secret: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WebhookStatus.ACTIVE, server_default=WebhookStatus.ACTIVE
    )
    # Subscribed event types; empty list = all events.
    events: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    last_delivery_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="endpoint", cascade="all, delete-orphan", passive_deletes=True
    )


class WebhookDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        Index("ix_webhook_deliveries_endpoint_id", "endpoint_id"),
        Index("ix_webhook_deliveries_organization_id", "organization_id"),
        Index("ix_webhook_deliveries_event", "event"),
    )

    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    event: Mapped[str] = mapped_column(String(60), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    endpoint: Mapped["WebhookEndpoint"] = relationship(back_populates="deliveries")


class OutboxStatus:
    """Transactional-outbox row lifecycle — see app/services/webhook_outbox.py."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ALL = (PENDING, PROCESSING, COMPLETED, FAILED)


class WebhookOutbox(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Transactional outbox — guarantees "DB committed => event will be
    delivered", closing the classic gap where a webhook fired via
    fire-and-forget ``asyncio.create_task`` is silently lost if the process
    crashes between the business-data commit and the delivery attempt.

    Callers insert a row into *the same session/transaction* as the business
    data they're recording (see ``webhook_outbox.enqueue``), so the row only
    exists if that transaction actually committed. A separate background
    poller (``webhook_outbox.start_outbox_worker``) drains ``pending`` rows
    and hands them to the existing delivery machinery in
    ``app.services.webhook_service``.
    """

    __tablename__ = "webhook_outbox"
    __table_args__ = (
        Index("ix_webhook_outbox_status_created", "status", "created_at"),
        Index("ix_webhook_outbox_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    event: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OutboxStatus.PENDING, server_default=OutboxStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
