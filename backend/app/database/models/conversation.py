"""Conversation — one customer↔agent thread across any channel."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.agent import Agent
    from app.database.models.message import Message
    from app.database.models.user import User


class ConversationChannel(str, enum.Enum):
    chat = "chat"
    whatsapp = "whatsapp"
    sms = "sms"
    email = "email"
    messenger = "messenger"
    instagram = "instagram"
    telegram = "telegram"
    slack = "slack"
    teams = "teams"
    mobile = "mobile"
    desktop = "desktop"


class ConversationStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    qualified = "qualified"
    failed = "failed"
    lost = "lost"


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_organization_id", "organization_id"),
        Index("ix_conversations_agent_id", "agent_id"),
        Index("ix_conversations_status", "status"),
        Index("ix_conversations_started_at", "started_at"),
        Index("ix_conversations_user_id", "user_id"),
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
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )

    channel: Mapped[ConversationChannel] = mapped_column(
        Enum(ConversationChannel, name="conversation_channel"), nullable=False
    )
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status"),
        nullable=False,
        default=ConversationStatus.active,
    )

    # Phase 8 — AI chat-thread fields. Nullable so existing CRM
    # conversations (created without a logged-in owner) keep working.
    # An AI chat thread is a conversation with ``user_id`` set.
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[Optional[str]] = mapped_column(String(255))
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    # Customer identity (denormalised — a `contacts` table can come later)
    customer_name: Mapped[Optional[str]] = mapped_column(String(160))
    customer_email: Mapped[Optional[str]] = mapped_column(String(255))
    customer_phone: Mapped[Optional[str]] = mapped_column(String(40))

    # Unified cross-channel identity. Links this thread to the persistent
    # VisitorProfile so the agent shares memory across chat / whatsapp / forms.
    # Nullable so legacy CRM conversations keep working.
    visitor_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("visitor_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[Optional[int]] = mapped_column()

    summary: Mapped[Optional[str]] = mapped_column(String(2000))
    recording_url: Mapped[Optional[str]] = mapped_column(String(500))
    transcript_url: Mapped[Optional[str]] = mapped_column(String(500))

    extra: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # ── R1: Enterprise chat organization & sharing ──
    # Flags drive the sidebar grouping (Pinned / Favorites / Archived).
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversation_folders.id", ondelete="SET NULL"),
        nullable=True,
    )
    tags: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Public read-only sharing: a random token unlocks an unauthenticated
    # transcript view. ``None`` == not shared.
    share_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    shared_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Conversation {self.id} {self.channel} {self.status}>"
