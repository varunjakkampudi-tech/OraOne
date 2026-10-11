"""SyncJob — one execution of an integration's sync (Phase 10).

Each manual or scheduled sync creates a ``sync_jobs`` row so the UI can
show history, progress, and failures. ``documents_synced`` counts how
many remote documents were imported/updated in this run.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.integration import Integration
    from app.database.models.sync_log import SyncLog


class SyncJobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class SyncTrigger(str, enum.Enum):
    manual = "manual"
    scheduled = "scheduled"
    oauth = "oauth"  # first sync right after connecting


class SyncJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sync_jobs"
    __table_args__ = (
        Index("ix_sync_jobs_integration_id", "integration_id"),
        Index("ix_sync_jobs_organization_id", "organization_id"),
        Index("ix_sync_jobs_status", "status"),
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

    status: Mapped[SyncJobStatus] = mapped_column(
        Enum(SyncJobStatus, name="sync_job_status"),
        nullable=False,
        default=SyncJobStatus.queued,
    )
    trigger: Mapped[SyncTrigger] = mapped_column(
        Enum(SyncTrigger, name="sync_trigger"),
        nullable=False,
        default=SyncTrigger.manual,
    )

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    documents_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    documents_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(String(2000))

    integration: Mapped["Integration"] = relationship(back_populates="sync_jobs")
    logs: Mapped[list["SyncLog"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SyncJob {self.id} {self.status}>"
