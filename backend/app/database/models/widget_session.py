"""WidgetSession — one visitor's chat session on an embedded widget (R6).

A session ties an anonymous (or identified) visitor to a backing
:class:`Conversation`. ``visitor_id`` is a stable client token stored in
the browser so conversations persist across reloads. ``user_context`` holds
the non-sensitive identity/page context the host page passed via
``OraOne.init({...})`` (name, email, plan, current URL, …).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.widget import Widget


class WidgetSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "widget_sessions"
    __table_args__ = (
        Index("ix_widget_sessions_widget_id", "widget_id"),
        Index("ix_widget_sessions_visitor_id", "visitor_id"),
        Index("ix_widget_sessions_organization_id", "organization_id"),
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
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    visitor_id: Mapped[str] = mapped_column(String(80), nullable=False)
    # Non-sensitive identity + page context from OraOne.init({...}).
    user_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    referer: Mapped[Optional[str]] = mapped_column(String(2048))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Denormalised counters for cheap analytics.
    message_count: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    escalated: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )

    widget: Mapped["Widget"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WidgetSession {self.visitor_id}>"
