"""Inbound provider-message receipts: one row per (agent, provider message id).

Provider webhooks are redelivered (Telegram retries on timeout; Meta and Twilio retry on
non-2xx). The inbound pipeline claims the provider's message id with a unique insert
before it generates any reply, so a redelivered webhook is acknowledged without a second
conversation turn or a second reply.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChannelInboundReceipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A provider message id already processed for one agent."""

    __tablename__ = "channel_inbound_receipts"
    __table_args__ = (
        UniqueConstraint(
            "agent_id", "message_key", name="uq_channel_inbound_receipts_agent_key"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Provider-namespaced id, e.g. "telegram:123456" or "twilio:SM...".
    message_key: Mapped[str] = mapped_column(String(255), nullable=False)
