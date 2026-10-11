"""CrawlJob & CrawlLog — observability for a website crawl run (R3).

``CrawlJob`` tracks one crawl execution (queued → crawling → … →
completed/failed) with live progress counters. ``CrawlLog`` records a
per-URL line so the UI can show exactly what happened to each page.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CrawlJobStatus:
    queued = "queued"
    crawling = "crawling"
    extracting = "extracting"
    embedding = "embedding"
    completed = "completed"
    failed = "failed"
    paused = "paused"
    cancelled = "cancelled"
    ALL = {queued, crawling, extracting, embedding, completed, failed, paused, cancelled}
    TERMINAL = {completed, failed, cancelled}


class CrawlTrigger:
    manual = "manual"
    scheduled = "scheduled"
    ALL = {manual, scheduled}


class CrawlJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crawl_jobs"
    __table_args__ = (
        Index("ix_crawl_jobs_website_id", "website_id"),
        Index("ix_crawl_jobs_organization_id", "organization_id"),
        Index("ix_crawl_jobs_status", "status"),
    )

    website_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=CrawlJobStatus.queued, server_default=CrawlJobStatus.queued
    )
    trigger: Mapped[str] = mapped_column(
        String(16), nullable=False, default=CrawlTrigger.manual, server_default=CrawlTrigger.manual
    )

    pages_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    pages_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    pages_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    pages_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    chunks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    # ── distributed engine telemetry (R3+) ──
    worker_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    frontier_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error: Mapped[Optional[str]] = mapped_column(String(1000))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CrawlJob site={self.website_id} status={self.status}>"


class CrawlLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crawl_logs"
    __table_args__ = (
        Index("ix_crawl_logs_job_id", "job_id"),
        Index("ix_crawl_logs_website_id", "website_id"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crawl_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    website_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[Optional[str]] = mapped_column(String(2048))
    status: Mapped[Optional[str]] = mapped_column(String(40))
    level: Mapped[str] = mapped_column(String(10), nullable=False, default="info", server_default="info")
    message: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CrawlLog job={self.job_id} {self.level} {self.url}>"
