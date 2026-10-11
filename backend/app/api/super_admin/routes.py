"""Super Admin Control Center API (platform-scoped).

Every endpoint is gated by :func:`get_platform_admin` and therefore reads
across all tenants. Reads are audited; the only writes are feature-flag
toggles. Secrets are exposed **masked and read-only** — plaintext never
leaves the server.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.super_admin.deps import PlatformAdminContext, get_platform_admin
from app.database.session import get_db
from app.services import entitlements as ent
from app.services import platform_admin as svc
from app.services import platform_assistant as assistant
from app.services import platform_intelligence as intel
from app.services.audit import audit

router = APIRouter(prefix="/api/super-admin", tags=["super-admin"])


def _audit(
    admin: PlatformAdminContext,
    action: str,
    resource: str,
    *,
    resource_id: Optional[str] = None,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
    reason: Optional[str] = None,
    **meta: Any,
) -> None:
    """Emit a platform-admin audit record.

    Change-carrying calls should pass ``before``/``after`` snapshots plus the
    ``request`` so the actor's IP and request id are captured — entitlement
    changes are never made silently.
    """
    request_meta: dict[str, Any] = {}
    if request is not None:
        request_meta["ip"] = request.client.host if request.client else None
        request_meta["request_id"] = request.headers.get("x-request-id")
    if reason is not None:
        request_meta["reason"] = reason
    audit(
        action,
        resource=resource,
        resource_id=resource_id,
        organization_id="platform",
        user_id=str(admin.user_id),
        before=before,
        after=after,
        meta={"admin_email": admin.email, **request_meta, **meta},
    )


# --------------------------------------------------------------------------- #
# Identity / gate                                                             #
# --------------------------------------------------------------------------- #
@router.get("/me")
async def whoami(admin: PlatformAdminContext = Depends(get_platform_admin)) -> dict[str, Any]:
    return {"user_id": str(admin.user_id), "email": admin.email, "full_name": admin.full_name, "is_platform_admin": True}


# --------------------------------------------------------------------------- #
# Dashboard                                                                   #
# --------------------------------------------------------------------------- #
@router.get("/overview")
async def get_overview(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await svc.overview(db)


@router.get("/activity")
async def get_activity(
    limit: int = Query(40, ge=1, le=200),
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await svc.activity(db, limit=limit)


# --------------------------------------------------------------------------- #
# Customers                                                                   #
# --------------------------------------------------------------------------- #
@router.get("/customers")
async def get_customers(
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _audit(admin, "read", "platform_customers", q=q)
    return await svc.customers(db, q=q, limit=limit, offset=offset)


@router.get("/customers/{org_id}")
async def get_customer_detail(
    org_id: str,
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    data = await svc.customer_detail(db, org_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    _audit(admin, "read", "platform_customer", resource_id=org_id)
    return data


# --------------------------------------------------------------------------- #
# Conversations                                                               #
# --------------------------------------------------------------------------- #
@router.get("/conversations")
async def get_conversations(
    q: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await svc.conversations(db, q=q, channel=channel, limit=limit)


# --------------------------------------------------------------------------- #
# Audit logs                                                                  #
# --------------------------------------------------------------------------- #
@router.get("/audit-logs")
async def get_audit_logs(
    q: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await svc.audit_logs(db, q=q, action=action, resource=resource, limit=limit)


# --------------------------------------------------------------------------- #
# Billing / Usage                                                             #
# --------------------------------------------------------------------------- #
@router.get("/billing")
async def get_billing(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await svc.billing(db)


@router.get("/usage")
async def get_usage(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await svc.usage(db)


# --------------------------------------------------------------------------- #
# Security / Infrastructure / Releases                                        #
# --------------------------------------------------------------------------- #
@router.get("/security")
async def get_security(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await svc.security(db)


@router.get("/infrastructure")
async def get_infrastructure(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await svc.infrastructure(db)


@router.get("/releases")
async def get_releases(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await svc.releases(db)


# --------------------------------------------------------------------------- #
# Feature flags                                                               #
# --------------------------------------------------------------------------- #
class FeatureFlagPatch(BaseModel):
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = None


@router.get("/feature-flags")
async def get_feature_flags(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    return await svc.list_feature_flags(db)


@router.patch("/feature-flags/{key}")
async def patch_feature_flag(
    key: str,
    payload: FeatureFlagPatch,
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await svc.set_feature_flag(
        db, key, enabled=payload.enabled,
        rollout_percentage=payload.rollout_percentage, admin_user_id=admin.user_id,
    )
    _audit(admin, "update", "feature_flag", resource_id=key, enabled=payload.enabled, rollout=payload.rollout_percentage)
    return result


# --------------------------------------------------------------------------- #
# Products & entitlements (Phase 1)                                            #
# --------------------------------------------------------------------------- #
class ProductPatch(BaseModel):
    status: Optional[str] = None
    visibility: Optional[str] = None
    version: Optional[str] = None
    release_notes: Optional[str] = None
    default_enabled: Optional[bool] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    documentation_url: Optional[str] = None
    sort_order: Optional[int] = None
    reason: Optional[str] = None


class OrgEntitlementPatch(BaseModel):
    enabled: bool
    reason: Optional[str] = None


@router.get("/products")
async def get_products(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    products = await ent.list_products(db)
    return [ent.product_to_dict(p) for p in products]


@router.get("/entitlements/overview")
async def get_entitlements_overview(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Per-product adoption analytics across every organization."""
    return await ent.entitlement_overview(db)


@router.get("/authz-metrics")
async def get_authz_metrics(
    fmt: Optional[str] = None,
    admin: PlatformAdminContext = Depends(get_platform_admin),
) -> Any:
    """Authorization + entitlement-cache metrics (in-process registry).

    Returns JSON by default; pass ``?fmt=prometheus`` for text exposition.
    Surfaces cache hit/miss, authorization latency, denials, maintenance
    blocks and feature-flag evaluations.
    """
    from app.services import metrics as _metrics

    if (fmt or "").lower() in {"prom", "prometheus", "text"}:
        return PlainTextResponse(_metrics.prometheus_text())
    return _metrics.snapshot()


@router.patch("/products/{key}")
async def patch_product(
    key: str,
    payload: ProductPatch,
    request: Request,
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await ent.set_product(
        db, key,
        status=payload.status, visibility=payload.visibility,
        version=payload.version, release_notes=payload.release_notes,
        default_enabled=payload.default_enabled,
        display_name=payload.display_name, description=payload.description,
        icon=payload.icon, documentation_url=payload.documentation_url,
        sort_order=payload.sort_order,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown product '{key}'.")
    _audit(
        admin, "update", "product", resource_id=key,
        before=result["before"], after=result["after"],
        request=request, reason=payload.reason,
    )
    return result


@router.get("/customers/{organization_id}/entitlements")
async def get_customer_entitlements(
    organization_id: str,
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    try:
        org_uuid = uuid.UUID(organization_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid organization id.")
    return await ent.get_org_products(db, org_uuid)


@router.patch("/customers/{organization_id}/entitlements/{product_key}")
async def patch_customer_entitlement(
    organization_id: str,
    product_key: str,
    payload: OrgEntitlementPatch,
    request: Request,
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        org_uuid = uuid.UUID(organization_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid organization id.")
    result = await ent.set_org_entitlement(
        db, org_uuid, product_key, enabled=payload.enabled, admin_user_id=admin.user_id,
    )
    _audit(
        admin, "update", "org_entitlement",
        resource_id=f"{organization_id}:{product_key}",
        before=result.get("before"), after=result.get("after"),
        request=request, reason=payload.reason,
    )
    return result


# --------------------------------------------------------------------------- #
# Secrets (masked, read-only)                                                 #
# --------------------------------------------------------------------------- #
@router.get("/secrets")
async def get_secrets(
    admin: PlatformAdminContext = Depends(get_platform_admin),
) -> dict[str, Any]:
    _audit(admin, "read", "platform_secrets")
    return svc.secrets_inventory()


# --------------------------------------------------------------------------- #
# Generic cross-tenant resource lists (agents, leads, workspaces, …)          #
# --------------------------------------------------------------------------- #
@router.get("/resources/{kind}")
async def get_resource(
    kind: str,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await svc.list_resource(db, kind, q=q, limit=limit)


# --------------------------------------------------------------------------- #
# Platform intelligence (cost / quality / self-improvement / benchmark / …)   #
# --------------------------------------------------------------------------- #
@router.get("/cost-optimization")
async def get_cost_optimization(
    days: int = Query(30, ge=1, le=90),
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _audit(admin, "read", "platform_cost")
    return await intel.cost_optimization(db, days=days)


@router.get("/quality")
async def get_quality(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await intel.quality_monitoring(db)


@router.get("/self-improvement")
async def get_self_improvement(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await intel.self_improvement(db)


@router.get("/benchmarking")
async def get_benchmarking(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await intel.benchmarking(db)


@router.get("/health-monitor")
async def get_health_monitor(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await intel.health_monitor(db)


@router.get("/fraud")
async def get_fraud(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _audit(admin, "read", "platform_fraud")
    return await intel.fraud_detection(db)


@router.get("/compliance")
async def get_compliance(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await intel.compliance(db)


@router.get("/tenant-isolation")
async def get_tenant_isolation(
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await intel.tenant_isolation(db)


# --------------------------------------------------------------------------- #
# Universal search / Ora Copilot / Report generator                           #
# --------------------------------------------------------------------------- #
@router.get("/search")
async def universal_search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(8, ge=1, le=25),
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await assistant.universal_search(db, q=q, limit=limit)


class CopilotAsk(BaseModel):
    question: str


@router.post("/copilot")
async def ora_copilot(
    body: CopilotAsk,
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _audit(admin, "ask", "ora_copilot", question=body.question[:200])
    return await assistant.ora_copilot(db, question=body.question)


@router.get("/reports/{period}")
async def generate_report(
    period: str,
    admin: PlatformAdminContext = Depends(get_platform_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _audit(admin, "generate", "platform_report", period=period)
    return await assistant.generate_report(db, period=period)
