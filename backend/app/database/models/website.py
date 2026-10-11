"""Website — a crawl source that turns an entire site into KB knowledge (R3).

A ``Website`` belongs to a :class:`KnowledgeBase` (and therefore an
organization). Crawling it produces :class:`WebsitePage` rows whose
extracted markdown is chunked + embedded into ``document_chunks`` exactly
like an uploaded document, so website content is searchable through the
same Enterprise RAG engine (R4).

Statuses are plain strings (not DB enums) to keep the crawl state machine
flexible without enum migrations.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.website_page import WebsitePage


class WebsiteStatus:
    pending = "pending"      # created, not yet crawled
    crawling = "crawling"    # a crawl job is in flight
    ready = "ready"          # crawled + indexed
    failed = "failed"        # last crawl failed
    paused = "paused"        # crawling paused by user
    ALL = {pending, crawling, ready, failed, paused}


class CrawlMode:
    entire = "entire"        # whole site under base_url
    single = "single"        # just the base_url page
    folder = "folder"        # only the base_url path prefix
    sitemap = "sitemap"      # only URLs listed in sitemap.xml
    ALL = {entire, single, folder, sitemap}


class CrawlFrequency:
    manual = "manual"
    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    ALL = {manual, hourly, daily, weekly, monthly}


class Website(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "websites"
    __table_args__ = (
        Index("ix_websites_organization_id", "organization_id"),
        Index("ix_websites_knowledge_base_id", "knowledge_base_id"),
        Index("ix_websites_status", "status"),
        Index("ix_websites_next_crawl_at", "next_crawl_at"),
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
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WebsiteStatus.pending, server_default=WebsiteStatus.pending
    )

    # ── crawl scope / settings ──
    crawl_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CrawlMode.entire, server_default=CrawlMode.entire
    )
    max_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=5, server_default="5")
    max_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=500, server_default="500")
    crawl_frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CrawlFrequency.manual, server_default=CrawlFrequency.manual
    )
    respect_robots: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # ── distributed crawl tuning (R3+) ──
    # Render JavaScript with a headless browser when available (graceful
    # fallback to static HTML when no renderer is installed).
    render_js: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Politeness: minimum delay between requests to the same host (ms).
    crawl_delay_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Worker parallelism. 0 = adaptive (the engine tunes itself).
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    include_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    exclude_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    allowed_domains: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    # Optional auth for protected sites: {type, username, password, token, header, value}
    auth_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    # ── telemetry ──
    pages_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_crawl_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error: Mapped[Optional[str]] = mapped_column(String(1000))

    pages: Mapped[list["WebsitePage"]] = relationship(
        back_populates="website", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Website {self.base_url} status={self.status}>"
