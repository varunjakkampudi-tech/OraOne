"""CrawlFrontier — the distributed, durable URL queue for a crawl (R3+).

The frontier is what turns the single-process crawler into a **distributed,
resumable** one. Every URL a crawl discovers is recorded as a row here with a
``status`` state-machine (pending → claimed → done/error/skipped). Workers —
possibly several, possibly in different processes — pull work atomically with
``SELECT … FOR UPDATE SKIP LOCKED`` so the same URL is never fetched twice and
no central in-memory queue is required.

Because the frontier lives in Postgres (not RAM), a crawl can be **paused** and
**resumed** without losing its place, can survive a worker/restart, and can
scale to very large sites (100k+ URLs) without holding the whole frontier in
memory.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FrontierStatus:
    pending = "pending"      # waiting to be claimed
    claimed = "claimed"      # a worker is fetching it
    done = "done"            # fetched + processed
    error = "error"          # failed after retries
    skipped = "skipped"      # filtered out (robots/scope/etc.)
    ALL = {pending, claimed, done, error, skipped}
    TERMINAL = {done, error, skipped}


class CrawlFrontier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "crawl_frontier"
    __table_args__ = (
        # One row per URL per job — lets us dedupe with ON CONFLICT DO NOTHING.
        UniqueConstraint("job_id", "url", name="uq_crawl_frontier_job_url"),
        Index("ix_crawl_frontier_job_status", "job_id", "status"),
        Index("ix_crawl_frontier_website_id", "website_id"),
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
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    host: Mapped[Optional[str]] = mapped_column(String(255))
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=FrontierStatus.pending, server_default=FrontierStatus.pending
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    claimed_by: Mapped[Optional[str]] = mapped_column(String(64))
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error: Mapped[Optional[str]] = mapped_column(String(1000))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CrawlFrontier job={self.job_id} {self.status} {self.url}>"
