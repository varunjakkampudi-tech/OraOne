"""Lead — a sales/contact lead captured from a conversation, widget or manually.

A lead is the business outcome of an AI conversation: when a visitor shares
contact details (or the agent qualifies intent) we materialise a first-class
``leads`` row so the sales team can track, score and convert it. Leads are
tenant-scoped via ``organization_id`` and belong to a ``project`` like every
other resource in OraOne.

Previously leads only existed as append-only ``widget_events`` of type
``lead`` — good for analytics counts, useless for a CRM workflow. This model
gives leads identity, status, scoring and assignment.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text, Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    won = "won"
    lost = "lost"


class LeadTemperature(str, enum.Enum):
    """Sales temperature derived from score/intent (hot → warm → cold)."""

    hot = "hot"
    warm = "warm"
    cold = "cold"


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_organization_id", "organization_id"),
        Index("ix_leads_project_id", "project_id"),
        Index("ix_leads_status", "status"),
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_email", "email"),
        Index("ix_leads_conversation_id", "conversation_id"),
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

    # Optional provenance — where the lead came from.
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    widget_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("widgets.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Contact / CRM fields.
    name: Mapped[Optional[str]] = mapped_column(String(160))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(40))
    company: Mapped[Optional[str]] = mapped_column(String(200))

    # What the lead is interested in + the message that triggered capture.
    intent: Mapped[Optional[str]] = mapped_column(String(255))
    message: Mapped[Optional[str]] = mapped_column(Text)

    # Pipeline.
    source: Mapped[str] = mapped_column(
        String(40), nullable=False, default="widget", server_default="widget"
    )
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status"),
        nullable=False,
        default=LeadStatus.new,
        server_default=LeadStatus.new.value,
    )
    temperature: Mapped[LeadTemperature] = mapped_column(
        Enum(LeadTemperature, name="lead_temperature"),
        nullable=False,
        default=LeadTemperature.warm,
        server_default=LeadTemperature.warm.value,
    )
    score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    extra: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Lead {self.name or self.email or self.id} [{self.status}]>"
