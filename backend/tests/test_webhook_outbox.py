"""Transactional outbox — failure/retry/duplicate-delivery guarantees.

These tests exercise app.services.webhook_outbox directly against Postgres
(the whole point of the pattern is transactional commit semantics, which an
in-memory fake can't faithfully reproduce). They auto-skip when Postgres
isn't reachable, matching the pattern in test_phase6_agents_crud.py.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio


def _postgres_reachable() -> bool:
    import os

    import asyncpg

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    dsn = (
        url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgresql+psycopg2://", "postgresql://")
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


REQUIRES_DB = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="Postgres is not reachable from this host.",
)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
    """Engine-per-test so asyncpg's loop-bound pool doesn't leak across tests."""
    from app.database import session as db_session_module
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    Maker = db_session_module.AsyncSessionLocal
    assert Maker is not None

    async with Maker() as s:
        yield s
        await s.rollback()

    await dispose_engine()


async def _seed_org(session) -> uuid.UUID:
    from datetime import datetime, timezone

    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import MemberRole, MemberStatus, OrganizationMember
    from app.database.models.project import Project
    from app.database.models.user import User

    email = f"outbox-{uuid.uuid4()}@x.com"
    user = User(cognito_sub=f"sub-{uuid.uuid4()}", email=email, full_name="Outbox Tester")
    session.add(user)
    await session.flush()

    org = Organization(
        name="Outbox Test Workspace",
        slug=f"outbox-{uuid.uuid4().hex[:8]}",
        plan=OrgPlan.free,
        owner_user_id=user.id,
    )
    session.add(org)
    await session.flush()

    session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user.id,
            role=MemberRole.owner,
            status=MemberStatus.active,
            joined_at=datetime.now(timezone.utc),
        )
    )
    session.add(
        Project(organization_id=org.id, name="Default", slug="default", is_default=True, created_by_user_id=user.id)
    )
    await session.flush()
    return org.id


async def _cleanup_outbox(session, org_id: uuid.UUID) -> None:
    """Delete test-created outbox rows so they don't linger and get picked
    up by the real background worker running in the dev server process."""
    from sqlalchemy import delete

    from app.database.models.webhook import WebhookOutbox

    await session.execute(delete(WebhookOutbox).where(WebhookOutbox.organization_id == org_id))
    await session.commit()


@REQUIRES_DB
@pytest.mark.asyncio
async def test_enqueue_is_transactional_with_business_data(db_session):
    """A row only exists in webhook_outbox if the surrounding commit succeeded."""
    from app.database.models.webhook import OutboxStatus, WebhookOutbox
    from app.services import webhook_outbox
    from sqlalchemy import select

    org_id = await _seed_org(db_session)
    webhook_outbox.enqueue(db_session, organization_id=org_id, event="agent.created", data={"agent_id": "abc"})
    await db_session.commit()

    try:
        rows = (
            await db_session.scalars(select(WebhookOutbox).where(WebhookOutbox.organization_id == org_id))
        ).all()
        assert len(rows) == 1
        assert rows[0].status == OutboxStatus.PENDING
        assert rows[0].attempts == 0
    finally:
        await _cleanup_outbox(db_session, org_id)


@REQUIRES_DB
@pytest.mark.asyncio
async def test_deliver_success_marks_completed(db_session, monkeypatch):
    from app.database.models.webhook import OutboxStatus
    from app.services import webhook_outbox

    org_id = await _seed_org(db_session)
    row = webhook_outbox.enqueue(db_session, organization_id=org_id, event="agent.created", data={"x": 1})
    await db_session.commit()
    row_id = row.id

    async def _fake_dispatch(organization_id, event, data):
        return 1  # 1 endpoint scheduled

    monkeypatch.setattr("app.services.webhook_service.dispatch", _fake_dispatch)

    try:
        await webhook_outbox._deliver_outbox_row(row_id)

        fresh = await db_session.get(type(row), row_id)
        await db_session.refresh(fresh)
        assert fresh.status == OutboxStatus.COMPLETED
        assert fresh.attempts == 1
        assert fresh.processed_at is not None
    finally:
        await _cleanup_outbox(db_session, org_id)


@REQUIRES_DB
@pytest.mark.asyncio
async def test_deliver_failure_retries_until_max_attempts(db_session, monkeypatch):
    """Below MAX_ATTEMPTS a failed delivery goes back to PENDING (retryable);
    at MAX_ATTEMPTS it moves to FAILED and stops being retried."""
    from app.database.models.webhook import OutboxStatus
    from app.services import webhook_outbox

    org_id = await _seed_org(db_session)
    row = webhook_outbox.enqueue(db_session, organization_id=org_id, event="agent.created", data={"x": 1})
    await db_session.commit()
    row_id = row.id

    async def _always_fails(organization_id, event, data):
        raise RuntimeError("simulated endpoint down")

    monkeypatch.setattr("app.services.webhook_service.dispatch", _always_fails)

    try:
        for attempt in range(1, webhook_outbox._MAX_ATTEMPTS + 1):
            await webhook_outbox._deliver_outbox_row(row_id)
            fresh = await db_session.get(type(row), row_id)
            await db_session.refresh(fresh)
            assert fresh.attempts == attempt
            assert fresh.last_error and "simulated endpoint down" in fresh.last_error
            if attempt < webhook_outbox._MAX_ATTEMPTS:
                assert fresh.status == OutboxStatus.PENDING, f"expected retryable PENDING at attempt {attempt}"
            else:
                assert fresh.status == OutboxStatus.FAILED, "expected FAILED once max attempts reached"
    finally:
        await _cleanup_outbox(db_session, org_id)


@REQUIRES_DB
@pytest.mark.asyncio
async def test_tick_claims_rows_so_a_second_tick_does_not_redeliver(db_session, monkeypatch):
    """_tick() flips PENDING -> PROCESSING in one commit before delivering,
    so a concurrent/overlapping tick sees nothing left to claim — this is
    what prevents duplicate delivery of the same outbox row.

    _tick() polls globally (not scoped to one org, by design), so the test
    tags its own row with a unique event name and only asserts on that
    tag — other pending rows that happen to exist are irrelevant noise."""
    from app.services import webhook_outbox

    org_id = await _seed_org(db_session)
    unique_event = f"agent.created.drill.{uuid.uuid4().hex}"
    webhook_outbox.enqueue(db_session, organization_id=org_id, event=unique_event, data={"x": 1})
    await db_session.commit()

    calls: list[str] = []

    async def _fake_dispatch(organization_id, event, data):
        calls.append(event)
        return 1

    monkeypatch.setattr("app.services.webhook_service.dispatch", _fake_dispatch)

    try:
        # First tick: claims the pending row (-> PROCESSING) and delivers it (-> COMPLETED).
        await webhook_outbox._tick()
        # Second tick immediately after: nothing PENDING left for our row, must be a no-op for it.
        await webhook_outbox._tick()

        our_calls = [c for c in calls if c == unique_event]
        assert our_calls == [unique_event], f"expected exactly one delivery of {unique_event}, got {our_calls}"
    finally:
        await _cleanup_outbox(db_session, org_id)


@REQUIRES_DB
@pytest.mark.asyncio
async def test_stale_processing_row_is_reclaimed_after_simulated_crash(db_session, monkeypatch):
    """If the worker crashes between claiming a row (-> PROCESSING) and
    finishing delivery, the row must not be stuck forever — the next tick's
    stale-row sweep should reset it back to PENDING once it's older than
    the stale threshold, so a restarted worker eventually retries it."""
    from datetime import timedelta

    from app.database.models.webhook import OutboxStatus, WebhookOutbox
    from app.services import webhook_outbox

    org_id = await _seed_org(db_session)
    row = webhook_outbox.enqueue(db_session, organization_id=org_id, event="agent.created", data={"x": 1})
    await db_session.commit()
    row_id = row.id

    try:
        # Simulate "claimed but never delivered" (worker died mid-flight),
        # with updated_at backdated past the stale threshold.
        row.status = OutboxStatus.PROCESSING
        await db_session.commit()
        await db_session.execute(
            WebhookOutbox.__table__.update()
            .where(WebhookOutbox.id == row_id)
            .values(updated_at=webhook_outbox._utcnow() - timedelta(seconds=webhook_outbox._STALE_PROCESSING_SECONDS + 30))
        )
        await db_session.commit()

        calls: list[str] = []

        async def _fake_dispatch(organization_id, event, data):
            calls.append(event)
            return 1

        monkeypatch.setattr("app.services.webhook_service.dispatch", _fake_dispatch)

        # This tick should reclaim the stale PROCESSING row back to PENDING,
        # then immediately claim + deliver it in the same pass.
        await webhook_outbox._tick()

        fresh = await db_session.get(type(row), row_id)
        await db_session.refresh(fresh)
        assert fresh.status == OutboxStatus.COMPLETED
        assert calls == ["agent.created"]
    finally:
        await _cleanup_outbox(db_session, org_id)


@pytest.mark.asyncio
async def test_worker_start_stop_is_clean_and_idempotent():
    """Graceful shutdown must actually cancel the background loop (not just
    drop the reference) — proves a restart won't leave a dangling task on
    a stale event loop."""
    from app.services import webhook_outbox

    webhook_outbox.start_outbox_worker()
    assert webhook_outbox._task is not None
    assert not webhook_outbox._task.done()

    await webhook_outbox.stop_outbox_worker()
    assert webhook_outbox._task.cancelled() or webhook_outbox._task.done()

    # Calling stop again (already stopped) must be a safe no-op.
    await webhook_outbox.stop_outbox_worker()

    # Restarting after a clean stop must work (simulates a process restart
    # re-entering the same module-level state).
    webhook_outbox.start_outbox_worker()
    assert not webhook_outbox._task.done()
    await webhook_outbox.stop_outbox_worker()
