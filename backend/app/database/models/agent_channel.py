"""Agent channel bindings — which delivery channel(s) an Agent serves.

Shared omnichannel infrastructure used by the Chat Platform (website widget,
WhatsApp, SMS, email, API). A single :class:`~app.database.models.agent.Agent`
can be bound to multiple channels via one ``agent_channels`` row per channel.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChannelType:
    chat = "chat"
    whatsapp = "whatsapp"
    email = "email"
    api = "api"
    ALL = {chat, whatsapp, email, api}


class ChannelStatus:
    active = "active"
    paused = "paused"
    disabled = "disabled"
    ALL = {active, paused, disabled}


class AgentChannel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Which channel(s) an Agent serves."""

    __tablename__ = "agent_channels"
    __table_args__ = (
        UniqueConstraint("agent_id", "channel", name="uq_agent_channels_agent_channel"),
        Index("ix_agent_channels_agent_id", "agent_id"),
        Index("ix_agent_channels_organization_id", "organization_id"),
        Index("ix_agent_channels_channel", "channel"),
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
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default=ChannelType.chat)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ChannelStatus.active, server_default=ChannelStatus.active
    )
    # Channel-specific binding (e.g. phone number for SMS/WhatsApp) + free config.
    phone_number: Mapped[Optional[str]] = mapped_column(String(32))
    provider: Mapped[Optional[str]] = mapped_column(String(40))
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
