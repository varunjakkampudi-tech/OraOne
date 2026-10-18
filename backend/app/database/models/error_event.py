"""Structured record of a 5xx response or unhandled exception.

Written by ``app.middleware.request_context`` and read by the admin log viewer.
Every text column holds scrubbed content only (see ``app.core.log_redaction``):
no email addresses, tokens, query strings or concrete request paths.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class ErrorEvent(UUIDPrimaryKeyMixin, Base):
    """One server-side error, keyed by the request ID returned to the caller."""

    __tablename__ = "error_events"

    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    method: Mapped[str] = mapped_column(String(12), nullable=False)
    route: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exception_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    release_version: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    actor_hash: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    org_hash: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ErrorEvent {self.request_id} {self.status_code} {self.route}>"
