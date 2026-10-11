"""R10 — Enterprise Security & Operations API (dashboard, Cognito-auth).

Security: threat-event stream, audit trail, inline PII/injection/moderation
scanning. System: health, live metrics, release-readiness checklist, feature
flags, and deployment history. Read endpoints require ``settings.read``;
mutating endpoints require ``settings.manage``. The ``/scan`` helper is open to
any authenticated member so client-side flows can pre-flight text.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.models.audit_log import AuditLog
from app.database.models.operations import SecurityEventType, SecuritySeverity
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization, require_permission
from app.schemas.operations import (
    DeploymentRecordRequest,
    FeatureFlagToggleRequest,
    FeatureFlagUpsertRequest,
    ScanRequest,
)
from app.services import ops_service, security_service
from app.services.audit import audit

router = APIRouter(tags=["operations"])


# ═══════════════════════════ SECURITY ═══════════════════════════
@router.get("/api/security/events")
async def security_events(
    severity: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await ops_service.list_security_events(
        session, ctx.organization_id, severity=severity, event_type=event_type, limit=limit
    )


@router.get("/api/security/audit")
async def security_audit(
    limit: int = Query(100, ge=1, le=500),
    action: str | None = Query(None),
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    stmt = (
        select(AuditLog)
        .where(AuditLog.organization_id == ctx.organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = (await session.execute(stmt)).scalars().all()
    return {
        "entries": [
            {
                "id": str(a.id),
                "action": a.action,
                "resource": a.resource,
                "resource_id": a.resource_id,
                "user_id": str(a.user_id) if a.user_id else None,
                "meta": a.meta or {},
                "created_at": a.created_at,
            }
            for a in rows
        ]
    }


@router.get("/api/security/meta")
async def security_meta(
    ctx: OrgContext = Depends(get_current_organization),
) -> dict:
    return {
        "severities": list(SecuritySeverity.ALL),
        "event_types": list(SecurityEventType.ALL),
    }


@router.post("/api/security/scan")
async def security_scan(
    payload: ScanRequest,
    request: Request,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    result = security_service.scan_text(payload.text, direction=payload.direction)
    # persist an event when the scan flags something noteworthy
    if not result["safe"]:
        if result["prompt_injection"]["injection"]:
            etype, title = SecurityEventType.PROMPT_INJECTION, "Prompt injection attempt detected"
        elif result["moderation"]["flagged"]:
            etype, title = SecurityEventType.CONTENT_BLOCKED, "Content moderation flagged text"
        elif payload.direction == "output" and not result.get("output_validation", {}).get("safe", True):
            etype, title = SecurityEventType.OUTPUT_REDACTED, "Sensitive data in output"
        else:
            etype, title = SecurityEventType.PII_DETECTED, "PII detected in text"
        await security_service.record_security_event(
            session,
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            event_type=etype,
            title=title,
            severity=result["severity"],
            description=f"types={result['pii']['types']} injection={result['prompt_injection']['flags']} moderation={result['moderation']['categories']}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            meta={"direction": payload.direction},
        )
    return result


@router.post("/api/security/mask")
async def security_mask(
    payload: ScanRequest,
    ctx: OrgContext = Depends(get_current_organization),
) -> dict:
    """Return text with PII (input) or secrets (output) masked/redacted."""
    if payload.direction == "output":
        return security_service.redact_output(payload.text)
    return security_service.mask_pii(payload.text)


@router.post("/api/security/rotate-keys")
async def rotate_keys(
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Record a key-rotation security event (operational acknowledgement).

    Actual per-key rotation is performed from the API Keys / Webhooks screens;
    this records the org-wide rotation intent for the audit + security trail.
    """
    await security_service.record_security_event(
        session,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        event_type=SecurityEventType.KEY_ROTATED,
        title="Credential rotation requested",
        severity=SecuritySeverity.MEDIUM,
        description="Operator initiated an org-wide credential rotation review.",
    )
    audit(
        "rotate",
        resource="credentials",
        resource_id=str(ctx.organization_id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return {"status": "recorded", "message": "Rotation review recorded. Rotate individual keys/webhooks from their screens."}


# ═══════════════════════════ SYSTEM ═══════════════════════════
@router.get("/api/system/version")
async def system_version(
    ctx: OrgContext = Depends(get_current_organization),
) -> dict:
    return {"version": ops_service.APP_VERSION, "name": "OraOne"}


@router.get("/api/system/health")
async def system_health(
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await ops_service.system_health(session)


@router.get("/api/system/metrics")
async def system_metrics(
    hours: int = Query(24, ge=1, le=168),
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await ops_service.system_metrics(session, ctx.organization_id, hours)


@router.get("/api/system/readiness")
async def system_readiness(
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await ops_service.readiness_checklist(session)


@router.get("/api/system/features")
async def list_features(
    environment: str | None = Query(None),
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return {"features": await ops_service.list_feature_flags(session, ctx.organization_id, environment)}


@router.post("/api/system/features", status_code=status.HTTP_201_CREATED)
async def upsert_feature(
    payload: FeatureFlagUpsertRequest,
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    flag = await ops_service.upsert_feature_flag(
        session,
        ctx.organization_id,
        ctx.user_id,
        name=payload.name,
        enabled=payload.enabled,
        description=payload.description,
        environment=payload.environment,
        rollout_percentage=payload.rollout_percentage,
    )
    audit(
        "update",
        resource="feature_flag",
        resource_id=str(flag.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"name": flag.name, "enabled": flag.enabled},
    )
    return {"id": str(flag.id), "name": flag.name, "enabled": flag.enabled}


@router.put("/api/system/features/{flag_id}")
async def toggle_feature(
    flag_id: uuid.UUID,
    payload: FeatureFlagToggleRequest,
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    flag = await ops_service.set_feature_flag_enabled(
        session, ctx.organization_id, ctx.user_id, flag_id, payload.enabled
    )
    if flag is None:
        raise HTTPException(status_code=404, detail="Feature flag not found.")
    return {"id": str(flag.id), "name": flag.name, "enabled": flag.enabled}


@router.get("/api/system/deployments")
async def list_deployments(
    limit: int = Query(50, ge=1, le=200),
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return {"deployments": await ops_service.list_deployments(session, ctx.organization_id, limit)}


@router.post("/api/system/deployments", status_code=status.HTTP_201_CREATED)
async def record_deployment(
    payload: DeploymentRecordRequest,
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    record = await ops_service.record_deployment(
        session,
        ctx.organization_id,
        ctx.user_id,
        version=payload.version,
        environment=payload.environment,
        status=payload.status,
        notes=payload.notes,
    )
    return {"id": str(record.id), "version": record.version, "status": record.status}
