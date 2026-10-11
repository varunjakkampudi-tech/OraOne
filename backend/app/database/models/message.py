"""Message — a single utterance inside a Conversation."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.conversation import Conversation


class MessageSender(str, enum.Enum):
    agent = "agent"
    customer = "customer"
    system = "system"
    tool = "tool"


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    sender: Mapped[MessageSender] = mapped_column(
        Enum(MessageSender, name="message_sender"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Phase 8 — total tokens attributed to this message (prompt+completion
    # split is kept inside ``metadata_`` for billing). Nullable for legacy /
    # human-authored rows where no model accounting applies.
    token_count: Mapped[Optional[int]] = mapped_column(Integer)

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",  # column name in DB
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Message {self.sender}: {self.message[:30]!r}>"
