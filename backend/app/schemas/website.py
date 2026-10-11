"""Pydantic schemas for the Website Crawling API (R3)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ──────────────── Websites ────────────────

class WebsiteCreate(BaseModel):
    knowledge_base_id: uuid.UUID
    base_url: str = Field(..., min_length=3, max_length=2048)
    name: Optional[str] = Field(default=None, max_length=200)
    crawl_mode: str = Field(default="entire", description="entire | single | folder | sitemap")
    max_depth: int = Field(default=5, ge=0, le=10)
    max_pages: int = Field(default=500, ge=1, le=100_000)
    crawl_frequency: str = Field(default="manual", description="manual | hourly | daily | weekly | monthly")
    respect_robots: bool = True
    render_js: bool = Field(default=False, description="Render JavaScript with a headless browser when available")
    crawl_delay_ms: int = Field(default=0, ge=0, le=60_000, description="Politeness delay between requests to the same host")
    max_concurrency: int = Field(default=0, ge=0, le=16, description="Parallel workers (0 = adaptive)")
    include_paths: list[str] = Field(default_factory=list)
    exclude_paths: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    auth_config: dict[str, Any] = Field(default_factory=dict)


class WebsiteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    crawl_mode: Optional[str] = None
    max_depth: Optional[int] = Field(default=None, ge=0, le=10)
    max_pages: Optional[int] = Field(default=None, ge=1, le=100_000)
    crawl_frequency: Optional[str] = None
    respect_robots: Optional[bool] = None
    render_js: Optional[bool] = None
    crawl_delay_ms: Optional[int] = Field(default=None, ge=0, le=60_000)
    max_concurrency: Optional[int] = Field(default=None, ge=0, le=16)
    include_paths: Optional[list[str]] = None
    exclude_paths: Optional[list[str]] = None
    allowed_domains: Optional[list[str]] = None
    auth_config: Optional[dict[str, Any]] = None


class WebsiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    name: str
    base_url: str
    status: str
    crawl_mode: str
    max_depth: int
    max_pages: int
    crawl_frequency: str
    respect_robots: bool
    render_js: bool = False
    crawl_delay_ms: int = 0
    max_concurrency: int = 0
    include_paths: list[str] = Field(default_factory=list)
    exclude_paths: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    auth_config: dict[str, Any] = Field(default_factory=dict)
    pages_count: int = 0
    last_crawled_at: Optional[datetime] = None
    next_crawl_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WebsiteListResponse(BaseModel):
    items: list[WebsiteRead]
    total: int
    limit: int
    offset: int


# ──────────────── Pages ────────────────

class WebsitePageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    website_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: str
    status_code: Optional[int] = None
    language: Optional[str] = None
    classification: Optional[str] = None
    word_count: Optional[int] = None
    chunk_count: Optional[int] = None
    depth: Optional[int] = None
    version: int = 1
    last_crawled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WebsitePageDetail(WebsitePageRead):
    markdown: Optional[str] = None
    content: Optional[str] = None


class WebsitePageListResponse(BaseModel):
    items: list[WebsitePageRead]
    total: int
    limit: int
    offset: int


# ──────────────── Crawl jobs & logs ────────────────

class CrawlJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    website_id: uuid.UUID
    status: str
    trigger: str
    pages_total: int = 0
    pages_completed: int = 0
    pages_failed: int = 0
    pages_skipped: int = 0
    chunks_created: int = 0
    worker_count: int = 1
    concurrency: int = 0
    frontier_size: int = 0
    heartbeat_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CrawlJobListResponse(BaseModel):
    items: list[CrawlJobRead]
    total: int
    limit: int
    offset: int


class CrawlLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    website_id: uuid.UUID
    url: Optional[str] = None
    status: Optional[str] = None
    level: str
    message: Optional[str] = None
    created_at: datetime


class CrawlLogListResponse(BaseModel):
    items: list[CrawlLogRead]
    total: int


class WebsiteAnalytics(BaseModel):
    website_id: uuid.UUID
    status: str
    pages_total: int
    pages_indexed: int
    pages_failed: int
    pages_skipped: int
    chunks_total: int
    word_count_total: int
    by_classification: dict[str, int] = Field(default_factory=dict)
    last_crawled_at: Optional[datetime] = None
    next_crawl_at: Optional[datetime] = None
    last_job: Optional[CrawlJobRead] = None
