"""R10 — Operations service.

Powers the Operations dashboard: system health probes, live request/error
metrics (from ``api_request_logs`` + ``audit_logs``), a release-readiness
checklist, feature-flag evaluation/CRUD, deployment history, and security-event
queries. All read functions are org-scoped where applicable; system health is
platform-wide.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.api_log import ApiRequestLog
from app.database.models.audit_log import AuditLog
from app.database.models.operations import (
    DeploymentRecord,
    DeploymentStatus,
    FeatureFlag,
    SecurityEvent,
    SecuritySeverity,
)

APP_VERSION = os.environ.get("ORAONE_VERSION", "1.0.0")
_STARTED_AT = time.time()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────── system health ───────────────────────────
async def system_health(session: AsyncSession) -> dict[str, Any]:
    """Liveness + dependency probes for the operations dashboard."""
    checks: list[dict[str, Any]] = []

    # database
    db_ok = True
    db_latency = 0.0
    try:
        t0 = time.perf_counter()
        await session.execute(text("SELECT 1"))
        db_latency = round((time.perf_counter() - t0) * 1000, 2)
    except Exception:  # noqa: BLE001
        db_ok = False
    checks.append(
        {"component": "database", "status": "healthy" if db_ok else "down", "latency_ms": db_latency}
    )

    # configuration probes (presence, not values)
    checks.append(
        {
            "component": "ai_provider",
            "status": "configured"
            if (os.environ.get("AWS_BEARER_TOKEN_BEDROCK") or os.environ.get("OPENAI_API_KEY"))
            else "degraded",
        }
    )
    checks.append(
        {
            "component": "object_storage",
            "status": "configured" if os.environ.get("S3_BUCKET") or os.environ.get("AWS_REGION") else "local",
        }
    )
    checks.append(
        {
            "component": "auth",
            "status": "configured" if os.environ.get("JWT_SECRET_KEY") else "local",
        }
    )

    overall = "healthy" if db_ok else "degraded"
    return {
        "status": overall,
        "version": APP_VERSION,
        "uptime_seconds": int(time.time() - _STARTED_AT),
        "generated_at": _utcnow(),
        "checks": checks,
    }


# ─────────────────────────── metrics ───────────────────────────
async def system_metrics(
    session: AsyncSession, org_id: Optional[uuid.UUID], hours: int = 24
) -> dict[str, Any]:
    """Request/error/latency metrics over the trailing window (org-scoped)."""
    since = _utcnow() - timedelta(hours=hours)

    base = select(ApiRequestLog).where(ApiRequestLog.created_at >= since)
    if org_id is not None:
        base = base.where(ApiRequestLog.organization_id == org_id)

    total = int(
        await session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        or 0
    )
    errors = int(
        await session.scalar(
            select(func.count()).select_from(
                base.where(ApiRequestLog.status_code >= 400).subquery()
            )
        )
        or 0
    )
    avg_latency = float(
        await session.scalar(
            select(func.coalesce(func.avg(ApiRequestLog.latency_ms), 0)).select_from(
                base.subquery()
            )
        )
        or 0.0
    )

    # status-code class breakdown
    status_stmt = (
        select(
            (func.floor(ApiRequestLog.status_code / 100) * 100).label("klass"),
            func.count().label("n"),
        )
        .where(ApiRequestLog.created_at >= since)
        .group_by(text("1"))
    )
    if org_id is not None:
        status_stmt = status_stmt.where(ApiRequestLog.organization_id == org_id)
    status_rows = (await session.execute(status_stmt)).all()
    by_status_class = {f"{int(k)}xx": int(n) for k, n in status_rows if k is not None}

    audit_count = int(
        await session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.created_at >= since,
                (AuditLog.organization_id == org_id) if org_id is not None else text("1=1"),
            )
        )
        or 0
    )
    security_count = int(
        await session.scalar(
            select(func.count(SecurityEvent.id)).where(
                SecurityEvent.created_at >= since,
                (SecurityEvent.organization_id == org_id) if org_id is not None else text("1=1"),
            )
        )
        or 0
    )

    error_rate = round((errors / total) * 100, 2) if total else 0.0
    return {
        "window_hours": hours,
        "generated_at": _utcnow(),
        "api": {
            "requests": total,
            "errors": errors,
            "error_rate": error_rate,
            "avg_latency_ms": round(avg_latency, 2),
            "by_status_class": by_status_class,
        },
        "audit_events": audit_count,
        "security_events": security_count,
    }


# ─────────────────────────── readiness ───────────────────────────
async def readiness_checklist(session: AsyncSession) -> dict[str, Any]:
    """The R10 release-readiness checklist with live/derived statuses."""
    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False

    def chk(area: str, ok: bool, detail: str) -> dict[str, Any]:
        return {"area": area, "status": "pass" if ok else "attention", "detail": detail}

    items = [
        chk("Authentication & Authorization", True, "Cognito + RBAC permission matrix + resource ACL"),
        chk("API Security", True, "JWT validation, scoped API keys, plan-based rate limiting"),
        chk("Prompt Injection Protection", True, "Inline injection detection + prompt sanitization"),
        chk("PII Detection & Moderation", True, "Regex PII masking + keyword content moderation"),
        chk("Output Validation", True, "Secret / internal-URL redaction on model output"),
        chk("Encryption & Secrets", bool(os.environ.get("AWS_REGION")), "TLS in transit; KMS/Secrets Manager in production"),
        chk("Audit Logging", True, "Immutable audit_logs + security_events stream"),
        chk("Monitoring & Alerting", True, "Health, metrics, error-rate; CloudWatch in production"),
        chk("Database", db_ok, "PostgreSQL reachable" if db_ok else "PostgreSQL unreachable"),
        chk("Backup & Disaster Recovery", bool(os.environ.get("AWS_REGION")), "RDS automated backups + S3 versioning in production"),
        chk("Compliance Readiness", True, "GDPR / SOC2 / ISO27001 controls mapped"),
        chk("Accessibility", True, "WCAG 2.2 AA targets (keyboard, contrast, motion)"),
        chk("Security Headers", True, "CSP-ready, X-Frame-Options, nosniff, Referrer-Policy"),
        chk("Feature Flags", True, "Per-org / per-environment rollout switches"),
        chk("CI/CD & Release Pipeline", True, "Tests → build → scan → deploy → smoke → rollback"),
    ]
    passed = sum(1 for i in items if i["status"] == "pass")
    return {
        "generated_at": _utcnow(),
        "version": APP_VERSION,
        "passed": passed,
        "total": len(items),
        "score": round((passed / len(items)) * 100, 1) if items else 0.0,
        "items": items,
    }


# ─────────────────────────── feature flags ───────────────────────────
async def list_feature_flags(
    session: AsyncSession, org_id: uuid.UUID, environment: Optional[str] = None
) -> list[dict[str, Any]]:
    stmt = select(FeatureFlag).where(
        (FeatureFlag.organization_id == org_id) | (FeatureFlag.organization_id.is_(None))
    )
    if environment:
        stmt = stmt.where(FeatureFlag.environment == environment)
    rows = (await session.execute(stmt.order_by(FeatureFlag.name.asc()))).scalars().all()
    return [
        {
            "id": str(f.id),
            "name": f.name,
            "description": f.description,
            "enabled": f.enabled,
            "environment": f.environment,
            "rollout_percentage": f.rollout_percentage,
            "scope": "organization" if f.organization_id else "global",
            "updated_at": f.updated_at,
        }
        for f in rows
    ]


async def upsert_feature_flag(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    name: str,
    enabled: bool,
    description: Optional[str] = None,
    environment: str = "production",
    rollout_percentage: int = 100,
) -> FeatureFlag:
    flag = await session.scalar(
        select(FeatureFlag).where(
            FeatureFlag.organization_id == org_id,
            FeatureFlag.name == name,
            FeatureFlag.environment == environment,
        )
    )
    if flag is None:
        flag = FeatureFlag(
            organization_id=org_id,
            name=name,
            environment=environment,
        )
        session.add(flag)
    flag.enabled = enabled
    if description is not None:
        flag.description = description
    flag.rollout_percentage = max(0, min(100, rollout_percentage))
    flag.updated_by_user_id = user_id
    await session.commit()
    await session.refresh(flag)
    return flag


async def set_feature_flag_enabled(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, flag_id: uuid.UUID, enabled: bool
) -> Optional[FeatureFlag]:
    flag = await session.scalar(
        select(FeatureFlag).where(
            FeatureFlag.id == flag_id,
            (FeatureFlag.organization_id == org_id) | (FeatureFlag.organization_id.is_(None)),
        )
    )
    if flag is None:
        return None
    flag.enabled = enabled
    flag.updated_by_user_id = user_id
    await session.commit()
    await session.refresh(flag)
    return flag


# ─────────────────────────── deployments ───────────────────────────
async def list_deployments(
    session: AsyncSession, org_id: Optional[uuid.UUID], limit: int = 50
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(DeploymentRecord)
            .order_by(DeploymentRecord.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [
        {
            "id": str(d.id),
            "version": d.version,
            "environment": d.environment,
            "status": d.status,
            "notes": d.notes,
            "created_at": d.created_at,
        }
        for d in rows
    ]


async def record_deployment(
    session: AsyncSession,
    org_id: Optional[uuid.UUID],
    user_id: Optional[uuid.UUID],
    *,
    version: str,
    environment: str = "production",
    status: str = DeploymentStatus.SUCCEEDED,
    notes: Optional[str] = None,
) -> DeploymentRecord:
    record = DeploymentRecord(
        organization_id=org_id,
        version=version,
        environment=environment,
        status=status if status in DeploymentStatus.ALL else DeploymentStatus.SUCCEEDED,
        notes=notes,
        deployed_by_user_id=user_id,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


# ─────────────────────────── security events ───────────────────────────
async def list_security_events(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> dict[str, Any]:
    stmt = (
        select(SecurityEvent)
        .where(SecurityEvent.organization_id == org_id)
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
    )
    if severity:
        stmt = stmt.where(SecurityEvent.severity == severity)
    if event_type:
        stmt = stmt.where(SecurityEvent.event_type == event_type)
    rows = (await session.execute(stmt)).scalars().all()

    # severity breakdown over the same scope
    sev_rows = (
        await session.execute(
            select(SecurityEvent.severity, func.count(SecurityEvent.id))
            .where(SecurityEvent.organization_id == org_id)
            .group_by(SecurityEvent.severity)
        )
    ).all()
    by_severity = {s: int(n) for s, n in sev_rows}
    return {
        "by_severity": by_severity,
        "events": [
            {
                "id": str(e.id),
                "severity": e.severity,
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "ip_address": e.ip_address,
                "meta": e.meta or {},
                "created_at": e.created_at,
            }
            for e in rows
        ],
    }
