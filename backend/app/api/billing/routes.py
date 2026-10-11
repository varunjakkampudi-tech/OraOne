"""Billing & Subscription API (Phase 12, Module 1).

Endpoints
---------
* ``GET  /api/billing/plans``         — public plan catalogue
* ``GET  /api/billing/subscription``  — current org subscription (+plan)
* ``POST /api/billing/checkout``      — upgrade (mock activates instantly)
* ``POST /api/billing/portal``        — Stripe customer-portal link
* ``POST /api/billing/cancel``        — cancel at period end
* ``GET  /api/billing/invoices``      — invoice history
* ``POST /api/billing/webhook``       — Stripe webhook sink (no auth)

Writes require the ``owner``/``admin`` role (billing admins).
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.billing_repository import BillingRepository
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_role,
)
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    InvoiceListResponse,
    InvoiceRead,
    PlanListResponse,
    PlanRead,
    PortalResponse,
    SubscriptionDetail,
)
from app.services import billing_service
from app.services.audit import audit

log = logging.getLogger("app.billing.api")
router = APIRouter(tags=["billing"])

_APP_URL = os.getenv("APP_URL", "http://localhost:3000")


def _repo(session: AsyncSession, ctx: OrgContext) -> BillingRepository:
    return BillingRepository(session, ctx.organization_id)


@router.get("/api/billing/plans", response_model=PlanListResponse, summary="List plans")
async def list_plans(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> PlanListResponse:
    repo = _repo(session, ctx)
    plans = await repo.list_plans()
    if not plans:
        # Lazily seed on first read so fresh databases work out of the box.
        await billing_service.ensure_plans_seeded(session)
        plans = await repo.list_plans()
    return PlanListResponse(
        items=[PlanRead.model_validate(p) for p in plans], total=len(plans)
    )


@router.get(
    "/api/billing/subscription",
    response_model=SubscriptionDetail,
    summary="Current subscription",
)
async def get_subscription(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SubscriptionDetail:
    sub = await billing_service.get_or_create_subscription(session, ctx.organization_id)
    return SubscriptionDetail.model_validate(sub)


@router.post(
    "/api/billing/checkout",
    response_model=CheckoutResponse,
    summary="Start an upgrade / change plan",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def checkout(
    payload: CheckoutRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    try:
        result = await billing_service.create_checkout(
            session,
            ctx.organization_id,
            payload.plan_code,
            payload.billing_cycle,
            success_url=f"{_APP_URL}/app/billing?status=success",
            cancel_url=f"{_APP_URL}/app/billing?status=cancel",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    audit(
        "checkout",
        resource="subscription",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={"plan_code": payload.plan_code, "cycle": payload.billing_cycle, "mode": result["mode"]},
    )

    sub_detail = (
        SubscriptionDetail.model_validate(result["subscription"])
        if result.get("subscription") is not None
        else None
    )
    return CheckoutResponse(
        mode=result["mode"],
        checkout_url=result.get("checkout_url"),
        activated=result.get("activated", False),
        subscription=sub_detail,
        message=result.get("message"),
    )


@router.post(
    "/api/billing/portal",
    response_model=PortalResponse,
    summary="Open the billing customer portal",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def portal(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> PortalResponse:
    result = await billing_service.create_portal(
        session, ctx.organization_id, return_url=f"{_APP_URL}/app/billing"
    )
    return PortalResponse(**result)


@router.post(
    "/api/billing/cancel",
    response_model=SubscriptionDetail,
    summary="Cancel the subscription at period end",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def cancel(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SubscriptionDetail:
    sub = await billing_service.cancel_subscription(session, ctx.organization_id)
    audit(
        "cancel",
        resource="subscription",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(sub.id),
    )
    return SubscriptionDetail.model_validate(sub)


@router.get(
    "/api/billing/invoices",
    response_model=InvoiceListResponse,
    summary="List invoices",
)
async def list_invoices(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> InvoiceListResponse:
    repo = _repo(session, ctx)
    rows = await repo.list_invoices(limit=limit, offset=offset)
    total = await repo.count_invoices()
    return InvoiceListResponse(
        items=[InvoiceRead.model_validate(r) for r in rows], total=total
    )


@router.post("/api/billing/webhook", summary="Stripe webhook sink", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Verify and process Stripe events (real mode only)."""
    if not billing_service.stripe_enabled():
        return {"received": True, "mode": "mock"}

    import stripe

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        # Real Stripe mode requires signature verification — an unsigned
        # payload can be forged by anyone to fake payments/subscriptions.
        log.error("STRIPE_WEBHOOK_SECRET is not set while Stripe billing is enabled; rejecting webhook.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook verification is not configured.",
        )
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid webhook: {e}")

    await billing_service.handle_webhook_event(session, dict(event))
    return {"received": True}
