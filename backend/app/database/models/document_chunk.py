"""DocumentChunk — one slice of a Document's text + extracted metadata.

Phase 9 adds the ``embedding`` column (pgvector ``vector(1024)``) so each
chunk can be retrieved by cosine similarity. The column is nullable:
chunks created before embeddings existed are back-filled when their
document is re-processed.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.providers.embeddings import EMBED_DIM

if TYPE_CHECKING:
    from app.database.models.document import Document


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_website_page_id", "website_page_id"),
        Index("ix_document_chunks_organization_id", "organization_id"),
        Index("ix_document_chunks_knowledge_base_id", "knowledge_base_id"),
        UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_doc_idx"
        ),
    )

    # A chunk belongs to EITHER an uploaded Document OR a crawled
    # WebsitePage (R3). ``document_id`` is therefore nullable now.
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
    )
    website_page_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("website_pages.id", ondelete="CASCADE"),
        nullable=True,
    )
    # Denormalised tenant scope (R4): every chunk carries its own org +
    # KB id so hybrid retrieval can filter cheaply without joining the
    # source table, and so website chunks (no Document) stay isolated.
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    knowledge_base_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=True,
    )
    # Denormalised project scope (mirrors knowledge_base_id's project) so
    # project-isolated retrieval can filter without a join.
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",  # actual DB column name
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    # Phase 9: pgvector embedding. Nullable so legacy chunks can be
    # back-filled on re-process. Dimensionality matches the active
    # embedding provider (Titan v2 / hashing fallback).
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(EMBED_DIM), nullable=True
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentChunk doc={self.document_id} idx={self.chunk_index}>"
