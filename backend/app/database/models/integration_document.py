"""IntegrationDocument — the per-integration sync manifest (Phase 10).

Tracks exactly which Drive (or other provider) folders/files the user has
chosen to sync, plus the sync state of each file. This is what powers the
"Synced Items" management UI and incremental sync:

* ``is_folder=True``  → a folder the user selected (everything inside it
  is synced, recursively).
* ``is_folder=False`` → a file; ``status``/``checksum``/``last_synced``
  track whether it has been downloaded + embedded, and ``document_id``
  links to the embedded :class:`Document`.

Status is a plain string (not a PG enum) to keep migrations simple.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.integration import Integration
    from app.database.models.document import Document


# Status values for a manifest file row.
class IntegrationDocStatus:
    pending = "pending"   # selected, not yet synced
    synced = "synced"     # downloaded + embedded
    failed = "failed"     # last sync errored
    skipped = "skipped"   # excluded by a filter (type/size/…)
    removed = "removed"   # deselected or deleted upstream


class IntegrationDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "integration_documents"
    __table_args__ = (
        UniqueConstraint("integration_id", "external_id", name="uq_integration_documents_ext"),
        Index("ix_integration_documents_integration_id", "integration_id"),
        Index("ix_integration_documents_organization_id", "organization_id"),
        Index("ix_integration_documents_selected", "integration_id", "selected"),
    )

    integration_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Denormalised for cheap tenant-scoped queries.
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(160))
    path: Mapped[Optional[str]] = mapped_column(Text)
    parent_external_id: Mapped[Optional[str]] = mapped_column(String(255))

    is_folder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # True = the user wants this item synced. Toggled when items are
    # added/removed from the selection.
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=IntegrationDocStatus.pending
    )
    checksum: Mapped[Optional[str]] = mapped_column(String(80))
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    external_modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_synced: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Link to the embedded content document (set once a file is synced).
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    integration: Mapped["Integration"] = relationship()
    document: Mapped[Optional["Document"]] = relationship()
