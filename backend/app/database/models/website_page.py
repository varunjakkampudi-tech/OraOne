"""WebsitePage — one crawled URL belonging to a :class:`Website` (R3).

Holds the cleaned text + markdown for the page, a content checksum used
for change detection (incremental recrawls skip unchanged pages), and a
``version`` that increments whenever the content changes. The markdown is
chunked + embedded into ``document_chunks`` (linked via
``document_chunks.website_page_id``) so the page is retrievable by the RAG
engine just like an uploaded document.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.website import Website


class PageStatus:
    crawled = "crawled"      # fetched + extracted + indexed
    skipped = "skipped"      # unchanged since last crawl
    failed = "failed"        # fetch/extract error
    deleted = "deleted"      # gone upstream; removed from search
    ALL = {crawled, skipped, failed, deleted}


class WebsitePage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "website_pages"
    __table_args__ = (
        UniqueConstraint("website_id", "url", name="uq_website_pages_site_url"),
        Index("ix_website_pages_website_id", "website_id"),
        Index("ix_website_pages_organization_id", "organization_id"),
        Index("ix_website_pages_checksum", "checksum"),
        Index("ix_website_pages_status", "status"),
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
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(512))
    description: Mapped[Optional[str]] = mapped_column(String(1024))
    content: Mapped[Optional[str]] = mapped_column(Text)        # cleaned plain text
    markdown: Mapped[Optional[str]] = mapped_column(Text)       # markdown for LLMs
    checksum: Mapped[Optional[str]] = mapped_column(String(64))

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PageStatus.crawled, server_default=PageStatus.crawled
    )
    status_code: Mapped[Optional[int]] = mapped_column(Integer)
    language: Mapped[Optional[str]] = mapped_column(String(16))
    content_type: Mapped[Optional[str]] = mapped_column(String(120))
    classification: Mapped[Optional[str]] = mapped_column(String(40))  # docs/faq/blog/product/...
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_modified: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    page_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")

    website: Mapped["Website"] = relationship(back_populates="pages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WebsitePage {self.url} v{self.version}>"
