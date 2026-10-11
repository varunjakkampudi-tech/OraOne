"""Public entitlements API (Phase 1).

A single, cheap, authenticated endpoint the frontend calls once after login to
learn what its organization may see:

    GET /api/entitlements/me

Returns product access, feature flags and maintenance state for the caller's
org. This endpoint is **read-only** — customers can never grant themselves
entitlements; that is done exclusively by platform admins.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.services import entitlements as ent
from app.services.audit import audit

router = APIRouter(prefix="/api/entitlements", tags=["entitlements"])


@router.get("/me")
async def my_entitlements(
    ctx: OrgContext = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Effective product + feature entitlements for the current organization."""
    return await ent.entitlements_snapshot(db, ctx.organization_id)


class AccessRequest(BaseModel):
    """A customer's request to enable a product they aren't entitled to."""

    product_key: str = Field(..., min_length=1, max_length=60)
    reason: Optional[str] = Field(default=None, max_length=500)


@router.post("/request-access")
async def request_access(
    body: AccessRequest,
    request: Request,
    ctx: OrgContext = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Record a customer's request for access to a product.

    Read-only with respect to entitlements — this never grants access. It emits
    an audit record so platform admins can act on the request, and returns a
    confirmation payload for the UI.
    """
    result = await ent.record_access_request(
        db, ctx, body.product_key, reason=body.reason,
    )
    client_ip = request.client.host if request.client else None
    audit(
        "request_access",
        resource="product_entitlement",
        resource_id=body.product_key,
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={
            "product_key": body.product_key,
            "reason": result.get("reason"),
            "ip": client_ip,
            "request_id": request.headers.get("x-request-id"),
        },
    )
    return {"ok": True, **result}
