"""Outbound calling campaigns and their per-lead attempts.

A ``CallCampaign`` is a named batch of leads to call in one project. Planning
creates one ``CallAttempt`` per lead: ``queued`` when the outreach policy allows
the call, or ``skipped`` with a plain-language ``skip_reason`` when it does not.
Every row carries ``organization_id`` and every query must filter on it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CampaignStatus:
    draft = "draft"
    running = "running"
    paused = "paused"
    completed = "completed"

    ALL = ("draft", "running", "paused", "completed")


class AttemptStatus:
    queued = "queued"
    calling = "calling"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"

    ALL = ("queued", "calling", "completed", "failed", "skipped")
    #: Attempts that count toward the per-lead daily cap.
    COUNTED = ("calling", "completed", "failed")


class CallCampaign(Base):
    __tablename__ = "call_campaigns"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'running', 'paused', 'completed')",
            name="ck_call_campaigns_status",
        ),
        Index("ix_call_campaigns_organization_id", "organization_id"),
        Index("ix_call_campaigns_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=CampaignStatus.draft,
        server_default=CampaignStatus.draft,
    )
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="UTC", server_default="UTC"
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CallAttempt(Base):
    __tablename__ = "call_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'calling', 'completed', 'failed', 'skipped')",
            name="ck_call_attempts_status",
        ),
        Index("ix_call_attempts_organization_id", "organization_id"),
        Index("ix_call_attempts_campaign_status", "campaign_id", "status"),
        Index("ix_call_attempts_lead_attempted", "lead_id", "attempted_at"),
        Index("ix_call_attempts_twilio_call_sid", "twilio_call_sid", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("call_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=AttemptStatus.queued,
        server_default=AttemptStatus.queued,
    )
    skip_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    twilio_call_sid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    attempted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
