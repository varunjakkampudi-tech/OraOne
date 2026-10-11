"""WidgetEvent — an analytics event emitted by an embedded widget (R6).

Events power the widget dashboard (opens, messages, lead captures,
escalations, bookings, errors). They are append-only and tenant-scoped via
``organization_id`` for cheap aggregation.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WidgetEventType:
    loaded = "loaded"
    opened = "opened"
    closed = "closed"
    message = "message"
    answer = "answer"
    lead = "lead"
    escalation = "escalation"
    booking = "booking"
    feedback = "feedback"
    upload = "upload"
    error = "error"
    ALL = {
        loaded, opened, closed, message, answer, lead,
        escalation, booking, feedback, upload, error,
    }


class WidgetEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "widget_events"
    __table_args__ = (
        Index("ix_widget_events_widget_id", "widget_id"),
        Index("ix_widget_events_organization_id", "organization_id"),
        Index("ix_widget_events_event", "event"),
        Index("ix_widget_events_created_at", "created_at"),
    )

    widget_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("widgets.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("widget_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )

    event: Mapped[str] = mapped_column(String(40), nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WidgetEvent {self.event}>"
