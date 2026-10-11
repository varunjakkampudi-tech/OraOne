"""Usage metering models (Phase 12, Module 2).

Metered events (AI messages, workflow runs, API calls, documents processed)
are accumulated into per-organization, per-metric, per-period counters. The
``period`` column is a bucket key — ``YYYY-MM-DD`` for daily metrics and
``YYYY-MM`` for monthly metrics — so quota windows reset automatically
without a cron job.

Resource counts (users, agents, knowledge bases, ...) are *not* stored here;
they are counted live from their own tables at read time. Only cumulative
metered events live in this table.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UsageCounter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single accumulating counter for one (org, metric, period) bucket."""

    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "metric",
            "period",
            name="uq_usage_counters_org_metric_period",
        ),
        Index("ix_usage_counters_organization_id", "organization_id"),
        Index("ix_usage_counters_metric", "metric"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Metric key, e.g. "ai_messages", "workflow_runs", "api_calls".
    metric: Mapped[str] = mapped_column(String(60), nullable=False)
    # Bucket key: "YYYY-MM-DD" (daily metrics) or "YYYY-MM" (monthly metrics).
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UsageCounter org={self.organization_id} {self.metric}@{self.period}={self.value}>"
