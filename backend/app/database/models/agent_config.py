"""AgentConfig — 1:1 sidecar holding the LLM config + JSONB extras."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.agent import Agent


class AgentConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_configs"
    __table_args__ = (
        UniqueConstraint("agent_id", name="uq_agent_configs_agent"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )

    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    temperature: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, default=0.70
    )
    voice: Mapped[Optional[str]] = mapped_column(String(80))
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="en-US")
    greeting: Mapped[Optional[str]] = mapped_column(Text)
    max_tokens: Mapped[int] = mapped_column(nullable=False, default=1024)

    # Flexible blob for everything else (Twilio number, webhook URLs, tool list, …)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    agent: Mapped["Agent"] = relationship(back_populates="config")
