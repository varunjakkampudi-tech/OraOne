"""Feature requests, bug reports and product feedback submitted by customers.

Powers the in-product "Feedback" board where customers submit ideas, report
bugs and upvote what matters to them.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FeatureRequestType:
    FEATURE = "feature"
    BUG = "bug"
    HELP = "help"
    FEEDBACK = "feedback"
    ALL = (FEATURE, BUG, HELP, FEEDBACK)


class FeatureRequestPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"
    ALL = (LOW, MEDIUM, HIGH, URGENT)


class FeatureRequestStatus:
    OPEN = "open"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DECLINED = "declined"
    ALL = (OPEN, PLANNED, IN_PROGRESS, COMPLETED, DECLINED)


class FeatureRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer-submitted idea, bug report or piece of feedback."""

    __tablename__ = "feature_requests"
    __table_args__ = (
        Index("ix_feature_requests_org", "organization_id"),
        Index("ix_feature_requests_status", "status"),
        Index("ix_feature_requests_type", "type"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=FeatureRequestType.FEATURE,
        server_default=FeatureRequestType.FEATURE,
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default=FeatureRequestPriority.MEDIUM,
        server_default=FeatureRequestPriority.MEDIUM,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=FeatureRequestStatus.OPEN,
        server_default=FeatureRequestStatus.OPEN,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    votes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    voter_ids: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
