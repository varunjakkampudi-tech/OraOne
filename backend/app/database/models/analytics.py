"""Analytics & observability models (R8).

The analytics layer is primarily computed *live* from the system-of-record
(conversations, messages, documents, widgets, sync jobs, workflow runs).
These tables capture things that are otherwise lossy:

* ``analytics_events`` — an append-only event stream (the BI event bus sink).
* ``daily_metrics``    — pre-rolled daily aggregates for fast time-series.
* ``cost_reports``     — per-provider/model token + cost rollups.
* ``answer_feedback``  — 👍/👎 feedback on individual answers.
"""
from __future__ import annotations

import uuid
from datetime import date as date_t, datetime
from typing import Any, Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AnalyticsEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_events_organization_id", "organization_id"),
        Index("ix_analytics_events_event_type", "event_type"),
        Index("ix_analytics_events_entity", "entity"),
        Index("ix_analytics_events_created_at", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )


class DailyMetric(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (
        Index("ix_daily_metrics_org_date", "organization_id", "date"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date_t] = mapped_column(Date, nullable=False)
    messages: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    conversations: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    active_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )


class CostReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cost_reports"
    __table_args__ = (
        Index("ix_cost_reports_org_date", "organization_id", "date"),
        Index("ix_cost_reports_provider", "provider"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date_t] = mapped_column(Date, nullable=False)
    provider: Mapped[str] = mapped_column(String(60), nullable=False, default="bedrock")
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    requests: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")


class AnswerFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "answer_feedback"
    __table_args__ = (
        Index("ix_answer_feedback_organization_id", "organization_id"),
        Index("ix_answer_feedback_conversation_id", "conversation_id"),
        Index("ix_answer_feedback_rating", "rating"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True
    )
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 1 = up, -1 = down, or 1..5
    reason: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
