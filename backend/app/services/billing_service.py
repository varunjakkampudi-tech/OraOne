"""Billing service (Phase 12, Module 1).

Encapsulates the plan catalogue, idempotent plan seeding, and the
subscription lifecycle. Stripe is optional:

* If ``STRIPE_SECRET_KEY`` is set **and** the ``stripe`` package is
  importable, real Checkout / Portal sessions are created and the
  subscription is activated by the webhook.
* Otherwise the service runs in **mock mode** — ``create_checkout``
  activates the subscription immediately and returns a local success URL,
  so the whole upgrade flow is testable without any Stripe account.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.billing import (
    BillingCycle,
    Invoice,
    InvoiceStatus,
    Plan,
    PlanCode,
    Subscription,
    SubscriptionStatus,
)
from app.database.models.organization import Organization, OrgPlan

log = logging.getLogger("app.billing")

# ── plan catalogue (source of truth for seeding) ──
# limits: -1 means unlimited. storage in MB.
PLAN_CATALOGUE: list[dict] = [
    {
        "code": PlanCode.free,
        "name": "Free",
        "description": "Get started with a single workspace.",
        "price_cents": 0,
        "price_cents_yearly": 0,
        "sort_order": 0,
        "features": [
            "1 Workspace", "2 Users", "2 Agents",
            "500 MB Storage", "100 AI Messages/day",
        ],
        "limits": {
            "users": 2, "agents": 2, "knowledge_bases": 1,
            "storage_mb": 500, "ai_messages_per_day": 100,
            "workflows": 1, "integrations": 1, "api_rpm": 0,
        },
    },
    {
        "code": PlanCode.starter,
        "name": "Starter",
        "description": "For small teams getting serious.",
        "price_cents": 4900,
        "price_cents_yearly": 49000,
        "sort_order": 1,
        "features": [
            "10 Users", "20 Agents", "20 GB Storage",
            "Unlimited Chat", "Basic Integrations",
        ],
        "limits": {
            "users": 10, "agents": 20, "knowledge_bases": 10,
            "storage_mb": 20480, "ai_messages_per_day": -1,
            "workflows": 25, "integrations": 10, "api_rpm": 100,
        },
    },
    {
        "code": PlanCode.business,
        "name": "Business",
        "description": "Scale automation across your company.",
        "price_cents": 19900,
        "price_cents_yearly": 199000,
        "sort_order": 2,
        "features": [
            "Unlimited Users", "Unlimited Agents",
            "Unlimited Knowledge Bases", "Workflow Automation",
            "Priority Support",
        ],
        "limits": {
            "users": -1, "agents": -1, "knowledge_bases": -1,
            "storage_mb": 512000, "ai_messages_per_day": -1,
            "workflows": -1, "integrations": -1, "api_rpm": 1000,
        },
    },
    {
        "code": PlanCode.enterprise,
        "name": "Enterprise",
        "description": "SSO, audit logs, custom models and SLAs.",
        "price_cents": 0,  # custom / contact sales
        "price_cents_yearly": 0,
        "sort_order": 3,
        "features": [
            "SSO", "Audit Logs", "Custom Models",
            "Dedicated Support", "Custom SLAs", "Private Deployment",
        ],
        "limits": {
            "users": -1, "agents": -1, "knowledge_bases": -1,
            "storage_mb": -1, "ai_messages_per_day": -1,
            "workflows": -1, "integrations": -1, "api_rpm": -1,
        },
    },
]

# Map our plan codes onto the legacy Organization.plan enum so existing
# code paths that read org.plan stay consistent.
_ORG_PLAN_MAP = {
    PlanCode.free: OrgPlan.free,
    PlanCode.starter: OrgPlan.starter,
    PlanCode.business: OrgPlan.growth,
    PlanCode.enterprise: OrgPlan.enterprise,
}


def stripe_enabled() -> bool:
    if not os.getenv("STRIPE_SECRET_KEY"):
        return False
    try:
        import stripe  # noqa: F401
        return True
    except Exception:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_plans_seeded(session: AsyncSession) -> int:
    """Insert any catalogue plans missing from the DB. Idempotent."""
    created = 0
    for spec in PLAN_CATALOGUE:
        existing = await session.scalar(
            select(Plan).where(Plan.code == spec["code"])
        )
        if existing is not None:
            continue
        session.add(
            Plan(
                code=spec["code"],
                name=spec["name"],
                description=spec["description"],
                price_cents=spec["price_cents"],
                price_cents_yearly=spec["price_cents_yearly"],
                currency="usd",
                features=spec["features"],
                limits=spec["limits"],
                is_active=True,
                sort_order=spec["sort_order"],
            )
        )
        created += 1
    if created:
        await session.commit()
        log.info("seeded %d plans", created)
    return created


async def get_or_create_subscription(
    session: AsyncSession, organization_id: uuid.UUID
) -> Subscription:
    """Return the org's subscription, creating a Free one if absent."""
    sub = await session.scalar(
        select(Subscription).where(
            Subscription.organization_id == organization_id
        )
    )

    # Until real Stripe billing is integrated, every workspace runs on the
    # Starter plan. We seed new subscriptions on Starter and coerce any other
    # plan (e.g. legacy mock "upgrades") back to Starter so the dashboard,
    # entitlements and usage limits stay consistent everywhere.
    seed_code = PlanCode.starter if not stripe_enabled() else PlanCode.free

    if sub is not None:
        if not stripe_enabled():
            starter = await session.scalar(
                select(Plan).where(Plan.code == PlanCode.starter)
            )
            if starter is not None and sub.plan_id != starter.id:
                sub.plan_id = starter.id
                sub.status = SubscriptionStatus.active
                sub.cancel_at_period_end = False
                org = await session.get(Organization, organization_id)
                if org is not None:
                    org.plan = _ORG_PLAN_MAP.get(PlanCode.starter, OrgPlan.starter)
                await session.commit()
                await session.refresh(sub)
        return sub

    base_plan = await session.scalar(select(Plan).where(Plan.code == seed_code))
    if base_plan is None:
        await ensure_plans_seeded(session)
        base_plan = await session.scalar(select(Plan).where(Plan.code == seed_code))

    sub = Subscription(
        organization_id=organization_id,
        plan_id=base_plan.id,
        status=SubscriptionStatus.active,
        billing_cycle=BillingCycle.monthly,
        current_period_start=_now(),
        current_period_end=_now() + timedelta(days=30),
    )
    session.add(sub)
    # Keep the legacy Organization.plan column in sync from the start.
    org = await session.get(Organization, organization_id)
    if org is not None:
        org.plan = _ORG_PLAN_MAP.get(seed_code, OrgPlan.free)
    await session.commit()
    await session.refresh(sub)
    return sub


def _cycle(value: str) -> BillingCycle:
    try:
        return BillingCycle(value)
    except ValueError:
        return BillingCycle.monthly


async def _activate(
    session: AsyncSession,
    organization_id: uuid.UUID,
    plan: Plan,
    cycle: BillingCycle,
    *,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
) -> Subscription:
    """Move the org onto ``plan`` and (re)issue the current period + invoice."""
    sub = await get_or_create_subscription(session, organization_id)
    days = 365 if cycle == BillingCycle.yearly else 30
    sub.plan_id = plan.id
    sub.status = SubscriptionStatus.active
    sub.billing_cycle = cycle
    sub.current_period_start = _now()
    sub.current_period_end = _now() + timedelta(days=days)
    sub.cancel_at_period_end = False
    if stripe_customer_id:
        sub.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id:
        sub.stripe_subscription_id = stripe_subscription_id

    # Keep the legacy Organization.plan column in sync.
    org = await session.get(Organization, organization_id)
    if org is not None:
        org.plan = _ORG_PLAN_MAP.get(plan.code, OrgPlan.free)

    # Issue an invoice (skip $0 plans).
    amount = plan.price_cents_yearly if cycle == BillingCycle.yearly else plan.price_cents
    if amount > 0:
        count_q = select(Invoice).where(Invoice.organization_id == organization_id)
        existing = len((await session.scalars(count_q)).all())
        session.add(
            Invoice(
                organization_id=organization_id,
                subscription_id=sub.id,
                number=f"INV-{existing + 1:05d}",
                amount_cents=amount,
                currency=plan.currency,
                status=InvoiceStatus.paid,
                description=f"{plan.name} ({cycle.value})",
                hosted_url=None,
            )
        )

    await session.commit()
    await session.refresh(sub)
    return sub


async def create_checkout(
    session: AsyncSession,
    organization_id: uuid.UUID,
    plan_code: str,
    billing_cycle: str,
    *,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Begin an upgrade. Mock mode activates immediately."""
    plan = await session.scalar(select(Plan).where(Plan.code == plan_code))
    if plan is None:
        raise ValueError(f"Unknown plan '{plan_code}'.")
    cycle = _cycle(billing_cycle)

    if not stripe_enabled():
        # Until Stripe is integrated, paid upgrades are disabled — every
        # workspace stays on Starter. Return a friendly message instead of
        # activating a different plan.
        sub = await get_or_create_subscription(session, organization_id)
        return {
            "mode": "mock",
            "checkout_url": cancel_url,
            "activated": False,
            "subscription": sub,
            "message": "Paid plans are launching soon — your workspace is on the Starter plan for now.",
        }

    # Real Stripe Checkout.
    import stripe

    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    sub = await get_or_create_subscription(session, organization_id)
    customer_id = sub.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(metadata={"organization_id": str(organization_id)})
        customer_id = customer["id"]
        sub.stripe_customer_id = customer_id
        await session.commit()

    price_amount = plan.price_cents_yearly if cycle == BillingCycle.yearly else plan.price_cents
    cs = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        success_url=success_url,
        cancel_url=cancel_url,
        line_items=[{
            "price_data": {
                "currency": plan.currency,
                "product_data": {"name": plan.name},
                "recurring": {"interval": "year" if cycle == BillingCycle.yearly else "month"},
                "unit_amount": price_amount,
            },
            "quantity": 1,
        }],
        metadata={
            "organization_id": str(organization_id),
            "plan_code": plan_code,
            "billing_cycle": cycle.value,
        },
    )
    return {
        "mode": "stripe",
        "checkout_url": cs["url"],
        "activated": False,
        "subscription": None,
        "message": "Redirect to Stripe Checkout to complete the upgrade.",
    }


async def cancel_subscription(
    session: AsyncSession, organization_id: uuid.UUID
) -> Subscription:
    """Schedule cancellation at period end (downgrades to Free)."""
    sub = await get_or_create_subscription(session, organization_id)
    sub.cancel_at_period_end = True
    if stripe_enabled() and sub.stripe_subscription_id:
        import stripe
        stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
        try:
            stripe.Subscription.modify(
                sub.stripe_subscription_id, cancel_at_period_end=True
            )
        except Exception as e:  # pragma: no cover
            log.warning("stripe cancel failed: %s", e)
    await session.commit()
    await session.refresh(sub)
    return sub


async def create_portal(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    return_url: str,
) -> dict:
    if not stripe_enabled():
        return {
            "mode": "mock",
            "portal_url": return_url,
            "message": "Customer portal is available once Stripe is configured.",
        }
    import stripe
    stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
    sub = await get_or_create_subscription(session, organization_id)
    if not sub.stripe_customer_id:
        return {"mode": "stripe", "portal_url": None, "message": "No Stripe customer yet."}
    ps = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id, return_url=return_url
    )
    return {"mode": "stripe", "portal_url": ps["url"], "message": None}


async def handle_webhook_event(session: AsyncSession, event: dict) -> None:
    """Process a verified Stripe webhook event (real mode only)."""
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    meta = obj.get("metadata") or {}
    org_id = meta.get("organization_id")
    if not org_id:
        return
    organization_id = uuid.UUID(org_id)

    if etype == "checkout.session.completed":
        plan = await session.scalar(
            select(Plan).where(Plan.code == meta.get("plan_code", "free"))
        )
        if plan is not None:
            await _activate(
                session, organization_id, plan, _cycle(meta.get("billing_cycle", "monthly")),
                stripe_customer_id=obj.get("customer"),
                stripe_subscription_id=obj.get("subscription"),
            )
    elif etype == "customer.subscription.deleted":
        free = await session.scalar(select(Plan).where(Plan.code == PlanCode.free))
        if free is not None:
            await _activate(session, organization_id, free, BillingCycle.monthly)
