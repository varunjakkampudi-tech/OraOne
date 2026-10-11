"""DocumentVersion — immutable snapshot of a document's stored file (R2).

Each time a document is re-uploaded (same filename in the same KB) the
previous storage key + checksum are preserved as a version row so users
can see the history and the system can detect duplicate content via the
SHA-256 checksum.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        Index("ix_document_versions_document", "document_id"),
        Index("ix_document_versions_checksum", "checksum"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum: Mapped[Optional[str]] = mapped_column(String(64))
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    filename: Mapped[Optional[str]] = mapped_column(String(255))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentVersion doc={self.document_id} v{self.version}>"
