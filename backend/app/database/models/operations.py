"""R10 — Enterprise Security & Release-Readiness models.

Backing tables for the operations layer: security events (threat / audit
signal stream distinct from the immutable ``audit_logs``), feature flags
(per-org / per-environment rollout switches), and a deployment history /
release log used by the Operations dashboard and release pipeline.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SecuritySeverity:
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    ALL = (INFO, LOW, MEDIUM, HIGH, CRITICAL)
    RANK = {INFO: 0, LOW: 1, MEDIUM: 2, HIGH: 3, CRITICAL: 4}


class SecurityEventType:
    LOGIN_FAILED = "login_failed"
    LOGIN_SUCCESS = "login_success"
    ACCOUNT_LOCKED = "account_locked"
    PERMISSION_CHANGED = "permission_changed"
    PROMPT_INJECTION = "prompt_injection"
    PII_DETECTED = "pii_detected"
    CONTENT_BLOCKED = "content_blocked"
    OUTPUT_REDACTED = "output_redacted"
    MALWARE_DETECTED = "malware_detected"
    RATE_LIMIT_HIT = "rate_limit_hit"
    KEY_ROTATED = "key_rotated"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ALL = (
        LOGIN_FAILED,
        LOGIN_SUCCESS,
        ACCOUNT_LOCKED,
        PERMISSION_CHANGED,
        PROMPT_INJECTION,
        PII_DETECTED,
        CONTENT_BLOCKED,
        OUTPUT_REDACTED,
        MALWARE_DETECTED,
        RATE_LIMIT_HIT,
        KEY_ROTATED,
        SUSPICIOUS_ACTIVITY,
    )


class SecurityEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A security-relevant signal (threat detections, auth anomalies, …)."""

    __tablename__ = "security_events"
    __table_args__ = (
        Index("ix_security_events_org", "organization_id"),
        Index("ix_security_events_severity", "severity"),
        Index("ix_security_events_type", "event_type"),
        Index("ix_security_events_created", "created_at"),
    )

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SecuritySeverity.INFO, server_default=SecuritySeverity.INFO
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


class FeatureFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A rollout switch. ``organization_id`` NULL == a global/platform flag."""

    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "name", "environment",
            name="uq_feature_flags_scope",
        ),
        Index("ix_feature_flags_org", "organization_id"),
        Index("ix_feature_flags_name", "name"),
    )

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    environment: Mapped[str] = mapped_column(
        String(20), nullable=False, default="production", server_default="production"
    )
    rollout_percentage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100"
    )
    updated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class DeploymentStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    ALL = (PENDING, IN_PROGRESS, SUCCEEDED, FAILED, ROLLED_BACK)


class DeploymentRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One release-pipeline run / deployment, for the changelog + rollback view."""

    __tablename__ = "deployment_history"
    __table_args__ = (
        Index("ix_deployment_history_org", "organization_id"),
        Index("ix_deployment_history_created", "created_at"),
    )

    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    environment: Mapped[str] = mapped_column(
        String(20), nullable=False, default="production", server_default="production"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DeploymentStatus.SUCCEEDED, server_default=DeploymentStatus.SUCCEEDED
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deployed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
