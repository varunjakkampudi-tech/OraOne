"""AI token budget: reserve before a paid call, settle afterwards, refuse when the plan cannot cover it.

The arithmetic is tested without a database. The atomic limit is tested against
Postgres and skips when the database is not reachable.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import conftest
from app.services import usage_service
from app.services.rag_service import RetrievedChunk


def _chunk(text: str) -> RetrievedChunk:
    return RetrievedChunk(
        content=text, chunk_index=0, document_name="Policy", score=0.9
    )


@pytest.mark.asyncio
async def test_reservation_larger_than_the_limit_is_refused(monkeypatch):
    async def _plan_for(_session, _org):
        return SimpleNamespace(limits={"ai_tokens_per_month": 100})

    monkeypatch.setattr(usage_service, "_plan_for", _plan_for)
    assert (
        await conftest.REAL_RESERVE_METERED(None, uuid.uuid4(), "ai_tokens", 500)
        is False
    )


@pytest.mark.asyncio
async def test_unlimited_plan_always_reserves(monkeypatch):
    recorded: list[int] = []

    async def _plan_for(_session, _org):
        return SimpleNamespace(limits={"ai_tokens_per_month": -1})

    async def _record(_session, _org, _metric, amount=1):
        recorded.append(amount)
        return amount

    monkeypatch.setattr(usage_service, "_plan_for", _plan_for)
    monkeypatch.setattr(usage_service, "record_usage", _record)
    assert (
        await conftest.REAL_RESERVE_METERED(None, uuid.uuid4(), "ai_tokens", 500)
        is True
    )
    assert recorded == [500]


@pytest.mark.asyncio
async def test_settle_refunds_an_overestimate(monkeypatch):
    recorded: list[int] = []

    async def _record(_session, _org, _metric, amount=1):
        recorded.append(amount)
        return 0

    monkeypatch.setattr(usage_service, "record_usage", _record)
    await conftest.REAL_SETTLE_METERED(
        None, uuid.uuid4(), "ai_tokens", reserved=500, actual=120
    )
    assert recorded == [-380]


@pytest.mark.asyncio
async def test_settle_charges_an_underestimate(monkeypatch):
    recorded: list[int] = []

    async def _record(_session, _org, _metric, amount=1):
        recorded.append(amount)
        return 0

    monkeypatch.setattr(usage_service, "record_usage", _record)
    await conftest.REAL_SETTLE_METERED(
        None, uuid.uuid4(), "ai_tokens", reserved=100, actual=180
    )
    assert recorded == [80]


@pytest.mark.asyncio
async def test_failed_call_is_refunded_in_full(monkeypatch):
    """A provider failure settles to zero, so the whole reservation is returned."""
    from app.services import rag_answer

    settled: list[tuple[int, int]] = []

    async def _settle(_session, _org, _metric, reserved, actual):
        settled.append((reserved, actual))

    class _Failing:
        async def chat(self, *_args, **_kwargs):
            raise RuntimeError("provider down")

    async def _one(*_args, **_kwargs):
        return [_chunk("Refunds take five days.")]

    monkeypatch.setattr(usage_service, "settle_metered", _settle)
    monkeypatch.setattr(rag_answer, "get_provider", lambda: _Failing())
    monkeypatch.setattr(rag_answer.rag_service, "hybrid_search", _one)

    await rag_answer.answer_query(
        object(),
        "How long do refunds take?",
        uuid.uuid4(),
        persona=None,
        project_id=uuid.uuid4(),
    )
    # Both counters (daily and monthly) are settled, and each is refunded in full.
    assert len(settled) == 2
    assert all(actual == 0 for _reserved, actual in settled)


@pytest.mark.asyncio
async def test_exhausted_budget_answers_from_passages_without_a_model_call(monkeypatch):
    from app.services import rag_answer

    calls: list[str] = []

    class _Provider:
        async def chat(self, *_args, **_kwargs):
            calls.append("model")
            raise AssertionError("no model call when the budget is exhausted")

    async def _no_budget(*_args, **_kwargs):
        return False

    async def _one(*_args, **_kwargs):
        return [_chunk("Refunds take five days.")]

    monkeypatch.setattr(usage_service, "reserve_metered", _no_budget)
    monkeypatch.setattr(rag_answer, "get_provider", lambda: _Provider())
    monkeypatch.setattr(rag_answer.rag_service, "hybrid_search", _one)

    result = await rag_answer.answer_query(
        object(),
        "How long do refunds take?",
        uuid.uuid4(),
        persona=None,
        project_id=uuid.uuid4(),
    )
    assert calls == []
    assert result["generated"] is False
    assert "five days" in result["answer"]


@pytest.mark.asyncio
async def test_agent_runtime_refuses_with_402_when_the_budget_is_used_up(monkeypatch):
    from app.services import agent_runtime
    from app.services.agent_runtime import AgentRuntime

    async def _no_budget(*_args, **_kwargs):
        return False

    monkeypatch.setattr(usage_service, "reserve_metered", _no_budget)
    monkeypatch.setattr(
        agent_runtime, "get_provider", lambda: SimpleNamespace(chat=None)
    )
    runtime = AgentRuntime(
        session=None, ctx=SimpleNamespace(organization_id=uuid.uuid4())
    )
    monkeypatch.setattr(runtime, "_model_params", lambda agent: ("m", 0.2, 100))

    async def _chain(model):
        return [model]

    monkeypatch.setattr(runtime, "_route_chain", _chain)
    with pytest.raises(HTTPException) as exc:
        await runtime.generate_reply(SimpleNamespace(), [])
    assert exc.value.status_code == 402


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


@pytest.mark.skipif(
    not _DB_REACHABLE, reason="Postgres is not reachable from this host."
)
@pytest.mark.asyncio
async def test_concurrent_reservations_cannot_exceed_the_limit(monkeypatch):
    """Against a real counter: five concurrent reservations of 60 with a limit of 100 admit one."""
    from sqlalchemy import delete

    from app.database import session as db_session_module
    from app.database.models.usage import UsageCounter
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    maker = db_session_module.AsyncSessionLocal

    # The counter has a foreign key to organizations, so a real organization is needed.
    from app.core.security import hash_password
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.user import User

    suffix = uuid.uuid4().hex[:8]
    async with maker() as session:
        owner = User(
            auth_subject=f"sub-{uuid.uuid4()}",
            email=f"budget-{suffix}@example.test",
            full_name="Budget Owner",
            password_hash=hash_password("not-used-in-this-test-8"),
            is_email_verified=True,
        )
        session.add(owner)
        await session.flush()
        organization = Organization(
            name=f"Budget {suffix}",
            slug=f"budget-{suffix}",
            plan=OrgPlan.free,
            owner_user_id=owner.id,
        )
        session.add(organization)
        await session.commit()
        org = organization.id

    async def _plan_for(_session, _org):
        return SimpleNamespace(limits={"ai_tokens_per_month": 100})

    monkeypatch.setattr(usage_service, "_plan_for", _plan_for)

    async def _attempt():
        async with maker() as session:
            return await conftest.REAL_RESERVE_METERED(session, org, "ai_tokens", 60)

    try:
        results = await asyncio.gather(*[_attempt() for _ in range(5)])
        assert results.count(True) == 1
    finally:
        async with maker() as session:
            await session.execute(
                delete(UsageCounter).where(UsageCounter.organization_id == org)
            )
            await session.commit()
        await dispose_engine()


@pytest.mark.asyncio
async def test_monthly_refusal_returns_the_daily_reservation(monkeypatch):
    """If the monthly allowance refuses, the daily reservation is refunded."""
    calls: list[tuple[str, int]] = []

    async def _reserve(_session, _org, metric, amount):
        calls.append(("reserve", metric, amount))
        return metric == "ai_tokens_daily"

    async def _settle(_session, _org, metric, reserved, actual):
        calls.append(("settle", metric, actual - reserved))

    monkeypatch.setattr(usage_service, "reserve_metered", _reserve)
    monkeypatch.setattr(usage_service, "settle_metered", _settle)

    assert await usage_service.reserve_ai_tokens(None, uuid.uuid4(), 40) is False
    assert calls == [
        ("reserve", "ai_tokens_daily", 40),
        ("reserve", "ai_tokens", 40),
        ("settle", "ai_tokens_daily", -40),
    ]


@pytest.mark.asyncio
async def test_daily_cap_uses_the_metric_default_unless_the_plan_sets_one(monkeypatch):
    spec = usage_service.METERED_METRICS["ai_tokens_daily"]
    assert (
        usage_service._metered_limit({}, spec) == usage_service.DEFAULT_DAILY_AI_TOKENS
    )
    assert usage_service._metered_limit({"ai_tokens_per_day": 1000}, spec) == 1000
    assert (
        usage_service._metered_limit({"ai_tokens_per_day": -1}, spec)
        == usage_service.UNLIMITED
    )


@pytest.mark.asyncio
async def test_daily_cap_refuses_the_call_that_would_exceed_it(monkeypatch):
    """Against the real counter: with a daily cap of 100, a second 60-token reservation is refused."""
    if not _DB_REACHABLE:
        pytest.skip("Postgres is not reachable from this host.")
    from sqlalchemy import delete

    from app.database import session as db_session_module
    from app.database.models.usage import UsageCounter
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    maker = db_session_module.AsyncSessionLocal
    # The counters have a foreign key to organizations, so a real organization row is needed.
    from app.core.security import hash_password
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.user import User

    suffix = uuid.uuid4().hex[:8]
    async with maker() as session:
        owner = User(
            auth_subject=f"sub-{uuid.uuid4()}",
            email=f"daily-cap-{suffix}@example.test",
            full_name="Daily Cap Owner",
            password_hash=hash_password("not-used-in-this-test-9"),
            is_email_verified=True,
        )
        session.add(owner)
        await session.flush()
        organization = Organization(
            name=f"Daily {suffix}",
            slug=f"daily-{suffix}",
            plan=OrgPlan.free,
            owner_user_id=owner.id,
        )
        session.add(organization)
        await session.commit()
        org = organization.id
    monkeypatch.setitem(
        usage_service.METERED_METRICS["ai_tokens_daily"], "default_limit", 100
    )

    async def _plan_for(_session, _org):
        return SimpleNamespace(limits={"ai_tokens_per_month": -1})

    monkeypatch.setattr(usage_service, "_plan_for", _plan_for)
    try:
        async with maker() as session:
            # The monthly counter is not a constraint here; only the daily cap is.
            assert (
                await conftest.REAL_RESERVE_METERED(session, org, "ai_tokens_daily", 60)
                is True
            )
        async with maker() as session:
            assert (
                await conftest.REAL_RESERVE_METERED(session, org, "ai_tokens_daily", 60)
                is False
            )
    finally:
        async with maker() as session:
            await session.execute(
                delete(UsageCounter).where(UsageCounter.organization_id == org)
            )
            await session.commit()
        await dispose_engine()


def test_daily_default_never_exceeds_the_monthly_allowance():
    """Free plan: 250,000 tokens a month must also cap a day, so the daily cap can apply first."""
    spec = usage_service.METERED_METRICS["ai_tokens_daily"]
    assert usage_service._metered_limit({"ai_tokens_per_month": 250000}, spec) == 250000
    assert (
        usage_service._metered_limit({"ai_tokens_per_month": -1}, spec)
        == usage_service.DEFAULT_DAILY_AI_TOKENS
    )
    assert (
        usage_service._metered_limit(
            {"ai_tokens_per_day": 1000, "ai_tokens_per_month": 250000}, spec
        )
        == 1000
    )
