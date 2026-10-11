"""Agent — an AI worker owned by an organization.

`type` covers both channels (chat/whatsapp) and purposes (sales/support).
Model + system_prompt are the hot-path fields kept on the agent row itself;
deeper, optional config lives in the 1:1 `agent_configs` sidecar.
"""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.organization import Organization
    from app.database.models.user import User
    from app.database.models.agent_config import AgentConfig
    from app.database.models.conversation import Conversation


class AgentType(str, enum.Enum):
    chat = "chat"
    whatsapp = "whatsapp"
    sales = "sales"
    support = "support"


class AgentStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    archived = "archived"


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_organization_id", "organization_id"),
        Index("ix_agents_status", "status"),
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

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    type: Mapped[AgentType] = mapped_column(
        Enum(AgentType, name="agent_type"), nullable=False
    )
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status"),
        nullable=False,
        default=AgentStatus.draft,
    )

    # Hot-path config kept on the agent row
    model: Mapped[str] = mapped_column(
        String(80), nullable=False, default="gpt-4o-mini"
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="agents")
    created_by: Mapped[Optional["User"]] = relationship()
    config: Mapped[Optional["AgentConfig"]] = relationship(
        back_populates="agent", uselist=False, cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Agent {self.name} ({self.type})>"
