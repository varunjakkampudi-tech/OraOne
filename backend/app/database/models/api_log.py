"""API request log (R7).

Lightweight, org-scoped access log for the external ``/api/v1`` surface:
which key called which endpoint, the HTTP status, and the latency. Powers
the developer dashboard's usage / error views and feeds cost/observability
without depending on external log aggregation.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ApiRequestLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_request_logs"
    __table_args__ = (
        Index("ix_api_request_logs_organization_id", "organization_id"),
        Index("ix_api_request_logs_api_key_id", "api_key_id"),
        Index("ix_api_request_logs_created_at", "created_at"),
        Index("ix_api_request_logs_status_code", "status_code"),
    )

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )
    key_prefix: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
