"""AgentPromptVersion — immutable snapshot of an agent's prompt/config.

Each time a user *publishes* a new version of an agent's brain (system
prompt, temperature, model knobs, tone, …) the previous state is frozen
as a numbered version row. This powers the version history timeline, the
prompt diff viewer (#8) and one-click rollback (#7).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AgentPromptVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_prompt_versions"
    __table_args__ = (
        Index("ix_agent_prompt_versions_agent", "agent_id", "version"),
        Index("ix_agent_prompt_versions_org", "organization_id"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    label: Mapped[Optional[str]] = mapped_column(String(160))
    note: Mapped[Optional[str]] = mapped_column(Text)

    # Frozen snapshot of the agent_config at publish time.
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    temperature: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    voice: Mapped[Optional[str]] = mapped_column(String(80))
    language: Mapped[Optional[str]] = mapped_column(String(16))
    greeting: Mapped[Optional[str]] = mapped_column(Text)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AgentPromptVersion agent={self.agent_id} v{self.version}>"
