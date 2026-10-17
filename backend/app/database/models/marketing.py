"""Marketing campaigns and their per-lead recipients.

A ``MarketingCampaign`` sends one message (email, SMS or WhatsApp) to a chosen
list of leads. Planning creates one ``MarketingRecipient`` per lead: ``queued``
when the outreach policy allows the message, or ``skipped`` with a plain-language
``skip_reason``. Sending moves each queued recipient to ``sent`` or ``failed``.
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


class MarketingChannel:
    email = "email"
    sms = "sms"
    whatsapp = "whatsapp"

    ALL = ("email", "sms", "whatsapp")


class MarketingCampaignStatus:
    draft = "draft"
    scheduled = "scheduled"
    sending = "sending"
    completed = "completed"
    cancelled = "cancelled"

    ALL = ("draft", "scheduled", "sending", "completed", "cancelled")
    #: Statuses from which a campaign may be sent or cancelled.
    EDITABLE = ("draft", "scheduled")


class MarketingRecipientStatus:
    queued = "queued"
    sent = "sent"
    skipped = "skipped"
    failed = "failed"

    ALL = ("queued", "sent", "skipped", "failed")


class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'sms', 'whatsapp')",
            name="ck_marketing_campaigns_channel",
        ),
        CheckConstraint(
            "status IN ('draft', 'scheduled', 'sending', 'completed', 'cancelled')",
            name="ck_marketing_campaigns_status",
        ),
        Index("ix_marketing_campaigns_organization_id", "organization_id"),
        Index("ix_marketing_campaigns_project_id", "project_id"),
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
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=MarketingCampaignStatus.draft,
        server_default=MarketingCampaignStatus.draft,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    sent_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    skipped_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class MarketingRecipient(Base):
    __tablename__ = "marketing_recipients"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'sent', 'skipped', 'failed')",
            name="ck_marketing_recipients_status",
        ),
        Index("ix_marketing_recipients_organization_id", "organization_id"),
        Index("ix_marketing_recipients_campaign_status", "campaign_id", "status"),
        Index("ix_marketing_recipients_lead_sent", "lead_id", "sent_at"),
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
        ForeignKey("marketing_campaigns.id", ondelete="CASCADE"),
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
        default=MarketingRecipientStatus.queued,
        server_default=MarketingRecipientStatus.queued,
    )
    skip_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
