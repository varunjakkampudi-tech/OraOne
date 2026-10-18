"""Escalation — a visitor question the assistant could not answer (human handoff).

Each handoff becomes one persistent row, scoped to an organization and project.
The row carries its own state: who owns it, whether the team has been told, and
how many delivery attempts have been made. A handoff therefore survives a
restart, an SMTP outage, or a worker crash, and it is visible in the dashboard
whether or not the notification went out.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EscalationStatus:
    open = "open"
    assigned = "assigned"
    resolved = "resolved"
    ALL = {open, assigned, resolved}


class NotifyStatus:
    pending = "pending"
    sent = "sent"
    failed = "failed"
    dead_letter = "dead_letter"
    no_recipients = "no_recipients"


class Escalation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "escalations"
    __table_args__ = (
        Index(
            "ix_escalations_org_project_status",
            "organization_id",
            "project_id",
            "status",
        ),
        Index("ix_escalations_notify_due", "notify_status", "next_attempt_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
    )
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    # Scrubbed, length-capped visitor question. Never a raw transcript.
    question: Mapped[str] = mapped_column(Text, nullable=False)

    contact_name: Mapped[Optional[str]] = mapped_column(String(160))
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(40))
    has_contact: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EscalationStatus.open
    )
    assigned_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # When a person on the team first replied to the customer for this escalation.
    first_reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Team response target. Overdue means open past this time and not resolved.
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Internal notes for the team: [{"at": iso, "user_id": str, "text": str}].
    # Never sent to the visitor.
    internal_notes: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    notify_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NotifyStatus.pending
    )
    notify_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Team addresses that already received the alert. A retry sends only to the rest.
    notified_addresses: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Error class only (for example "delivery_failed"), never an address or body.
    last_error: Mapped[Optional[str]] = mapped_column(String(80))
