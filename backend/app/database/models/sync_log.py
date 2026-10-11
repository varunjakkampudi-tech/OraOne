"""SyncLog — a single structured event emitted during a sync (Phase 10).

Persisted (in addition to the stdlib audit logger) so the integration
details page can render a human-readable timeline:
``Connected → Download → Chunk → Embedding → Completed`` with levels.
"""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.sync_job import SyncJob


class SyncLogLevel(str, enum.Enum):
    info = "info"
    warning = "warning"
    error = "error"


class SyncLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sync_logs"
    __table_args__ = (
        Index("ix_sync_logs_job_id", "job_id"),
        Index("ix_sync_logs_integration_id", "integration_id"),
        Index("ix_sync_logs_organization_id", "organization_id"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sync_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    integration_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    event: Mapped[str] = mapped_column(String(80), nullable=False)
    level: Mapped[SyncLogLevel] = mapped_column(
        Enum(SyncLogLevel, name="sync_log_level"),
        nullable=False,
        default=SyncLogLevel.info,
    )
    message: Mapped[Optional[str]] = mapped_column(Text)

    job: Mapped["SyncJob"] = relationship(back_populates="logs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SyncLog {self.event} {self.level}>"
