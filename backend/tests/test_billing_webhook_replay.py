"""Stripe webhook events are applied once, and an older event never overwrites a newer state.

Database-backed: each test seeds an organization on the real database and sends Stripe-shaped
events through the same handler the webhook route uses. Skips when Postgres is not reachable.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import func, select


def _postgres_reachable() -> bool:
    import asyncpg

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    dsn = url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    async def _probe() -> bool:
        try:
            conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=3)
            await conn.close()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_probe())
    except RuntimeError:
        return False


# Probe once at import time: inside a running test event loop the probe cannot start its own loop.
_DB_REACHABLE = _postgres_reachable()
db_only = pytest.mark.skipif(
    not _DB_REACHABLE, reason="Postgres is not reachable from this host."
)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
    from app.database import session as db_session_module
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    maker = db_session_module.AsyncSessionLocal
    assert maker is not None
    async with maker() as s:
        yield s
        await s.rollback()
    await dispose_engine()


async def _seed_org(session):
    from app.core.security import hash_password
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.user import User
    from app.services import billing_service

    suffix = uuid.uuid4().hex[:8]
    owner = User(
        auth_subject=f"sub-bill-{suffix}",
        email=f"bill-{suffix}@example.test",
        full_name="Billing Owner",
        password_hash=hash_password("not-used-in-this-test-12"),
        is_email_verified=True,
    )
    session.add(owner)
    await session.flush()
    org = Organization(
        name=f"Bill {suffix}",
        slug=f"bill-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=owner.id,
    )
    session.add(org)
    await session.flush()
    await billing_service.ensure_plans_seeded(session)
    await session.commit()
    return org.id


def _event(
    event_id: str,
    etype: str,
    created: int,
    org_id: uuid.UUID,
    plan_code: str | None = None,
) -> dict:
    obj = {
        "metadata": {"organization_id": str(org_id)},
        "customer": "cus_test",
        "subscription": "sub_test",
    }
    if plan_code:
        obj["metadata"]["plan_code"] = plan_code
        obj["metadata"]["billing_cycle"] = "monthly"
    # Stripe ids are unique across the account; a fresh suffix keeps reruns of this suite independent.
    unique_id = f"{event_id}_{uuid.uuid4().hex[:10]}"
    return {"id": unique_id, "type": etype, "created": created, "data": {"object": obj}}


async def _invoice_count(session, org_id) -> int:
    from app.database.models.billing import Invoice

    return int(
        await session.scalar(
            select(func.count(Invoice.id)).where(Invoice.organization_id == org_id)
        )
    )


async def _plan_code(session, org_id) -> str:
    from app.database.models.billing import Subscription
    from app.database.models.billing import Plan

    sub = await session.scalar(
        select(Subscription).where(Subscription.organization_id == org_id)
    )
    plan = await session.get(Plan, sub.plan_id)
    return plan.code.value if hasattr(plan.code, "value") else str(plan.code)


@db_only
@pytest.mark.asyncio
async def test_a_replayed_checkout_event_applies_once_and_bills_once(db_session):
    from app.services import billing_service

    org_id = await _seed_org(db_session)
    before = await _invoice_count(db_session, org_id)
    event = _event(
        "evt_replay_1", "checkout.session.completed", 1_700_000_000, org_id, "starter"
    )

    first = await billing_service.handle_webhook_event(db_session, dict(event))
    await db_session.commit()
    second = await billing_service.handle_webhook_event(db_session, dict(event))
    await db_session.commit()

    assert first == "applied"
    assert second == "duplicate"
    assert (
        await _invoice_count(db_session, org_id) == before + 1
    )  # one invoice, not two
    assert await _plan_code(db_session, org_id) == "starter"


@db_only
@pytest.mark.asyncio
async def test_an_older_cancellation_arriving_late_cannot_undo_a_newer_upgrade(
    db_session,
):
    from app.services import billing_service

    org_id = await _seed_org(db_session)
    checkout_old = _event(
        "evt_order_checkout",
        "checkout.session.completed",
        1_700_000_100,
        org_id,
        "starter",
    )
    deleted_newer = _event(
        "evt_order_deleted", "customer.subscription.deleted", 1_700_000_300, org_id
    )
    checkout_newer = _event(
        "evt_order_checkout2",
        "checkout.session.completed",
        1_700_000_500,
        org_id,
        "starter",
    )

    assert (
        await billing_service.handle_webhook_event(db_session, dict(checkout_old))
        == "applied"
    )
    await db_session.commit()
    assert (
        await billing_service.handle_webhook_event(db_session, dict(deleted_newer))
        == "applied"
    )
    await db_session.commit()
    assert await _plan_code(db_session, org_id) == "free"

    # A later-created checkout re-subscribes the organization; it is newer than the cancellation.
    assert (
        await billing_service.handle_webhook_event(db_session, dict(checkout_newer))
        == "applied"
    )
    await db_session.commit()
    assert await _plan_code(db_session, org_id) == "starter"


@db_only
@pytest.mark.asyncio
async def test_a_stale_event_is_recorded_but_changes_nothing(db_session):
    from app.services import billing_service

    org_id = await _seed_org(db_session)
    newer = _event(
        "evt_stale_newer", "customer.subscription.deleted", 1_700_000_400, org_id
    )
    older = _event(
        "evt_stale_older",
        "checkout.session.completed",
        1_700_000_200,
        org_id,
        "starter",
    )
    assert (
        await billing_service.handle_webhook_event(db_session, dict(newer)) == "applied"
    )
    await db_session.commit()
    invoices = await _invoice_count(db_session, org_id)

    assert (
        await billing_service.handle_webhook_event(db_session, dict(older)) == "stale"
    )
    await db_session.commit()
    assert await _invoice_count(db_session, org_id) == invoices
    assert await _plan_code(db_session, org_id) == "free"


@db_only
@pytest.mark.asyncio
async def test_unhandled_and_unattributed_events_are_ignored(db_session):
    from app.services import billing_service

    org_id = await _seed_org(db_session)
    unrelated = _event("evt_unrelated", "invoice.paid", 1_700_000_600, org_id)
    unattributed = {
        "id": f"evt_no_org_{uuid.uuid4().hex[:10]}",
        "type": "checkout.session.completed",
        "created": 1_700_000_700,
        "data": {"object": {"metadata": {}}},
    }
    no_id = {
        "type": "checkout.session.completed",
        "created": 1_700_000_800,
        "data": {"object": {}},
    }

    assert (
        await billing_service.handle_webhook_event(db_session, dict(unrelated))
        == "ignored"
    )
    assert (
        await billing_service.handle_webhook_event(db_session, dict(unattributed))
        == "ignored"
    )
    assert (
        await billing_service.handle_webhook_event(db_session, dict(no_id)) == "ignored"
    )
    await db_session.commit()
    assert await _plan_code(db_session, org_id) == "free"
