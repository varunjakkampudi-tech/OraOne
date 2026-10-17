"""Quota enforcement: measured usage, fail-closed when unmeasured.

* Measured quotas (users, projects, api_calls, ai_requests, kb_size_mb) are
  counted from real rows and allow below the limit, deny at the limit.
* Unmeasured quotas (storage_mb) fail closed in production with a plain reason
  and are allowed in development.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator
from types import SimpleNamespace

import pytest
import pytest_asyncio

from app.core.config import settings
from app.services import authorization as azm
from app.services import quotas as q

UNMEASURED_REASON = "We cannot check this limit yet."


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


REQUIRES_DB = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="Postgres is not reachable from this host.",
)


@pytest.fixture
def prod_env(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    return monkeypatch


@pytest.fixture
def dev_env(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    return monkeypatch


# ─────────────────── unmeasured (no DB needed) ───────────────────


async def test_unmeasured_quota_fails_closed_in_production(prod_env):
    d = await q.check_quota(None, uuid.uuid4(), q.QuotaKey.STORAGE_MB, plan_code="free")
    assert d.allowed is False
    assert d.outcome == "unmeasured"
    assert d.meta["reason"] == UNMEASURED_REASON


async def test_unmeasured_quota_is_allowed_in_development(dev_env):
    d = await q.check_quota(None, uuid.uuid4(), q.QuotaKey.STORAGE_MB, plan_code="free")
    assert d.allowed is True
    assert d.outcome == "unmeasured"
    assert d.meta["reason"] == UNMEASURED_REASON


async def test_unlimited_unmeasured_quota_is_allowed_in_production(prod_env):
    # Enterprise storage is unlimited, so there is nothing to measure or deny.
    d = await q.check_quota(
        None, uuid.uuid4(), q.QuotaKey.STORAGE_MB, plan_code="enterprise"
    )
    assert d.allowed is True
    assert d.limit == q.UNLIMITED


async def test_quota_policy_denies_unmeasured_in_production(prod_env, monkeypatch):
    """Through the authorization pipeline, an unmeasured quota is refused even
    when the enforcement switch is off."""

    async def _sub(session, org_id):
        return {
            "plan_code": "free",
            "plan_limits": None,
            "blocked": False,
            "outcome": azm.AuthzOutcome.ALLOW,
            "reason": None,
        }

    monkeypatch.setattr(azm, "_subscription_state", _sub)
    monkeypatch.setattr(azm, "ENFORCE_QUOTAS", False)
    ctx = SimpleNamespace(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        auth_subject="sub-quota",
        membership_role="owner",
    )
    d = await azm.authorize(
        None,
        ctx,
        quota=q.QuotaKey.STORAGE_MB,
        policies=(azm.QuotaPolicy(),),
    )
    assert d.allowed is False
    assert d.outcome == azm.AuthzOutcome.QUOTA_UNAVAILABLE
    assert d.http_status == 503
    assert UNMEASURED_REASON in d.reason


async def test_quota_policy_allows_unmeasured_in_development(dev_env, monkeypatch):
    async def _sub(session, org_id):
        return {
            "plan_code": "free",
            "plan_limits": None,
            "blocked": False,
            "outcome": azm.AuthzOutcome.ALLOW,
            "reason": None,
        }

    monkeypatch.setattr(azm, "_subscription_state", _sub)
    ctx = SimpleNamespace(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        auth_subject="sub-quota",
        membership_role="owner",
    )
    d = await azm.authorize(
        None,
        ctx,
        quota=q.QuotaKey.STORAGE_MB,
        policies=(azm.QuotaPolicy(),),
    )
    assert d.allowed is True


# ─────────────────── measured (real Postgres) ───────────────────


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
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


async def _seed_org_with_owner(session, *, slug_hint: str):
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import (
        MemberRole,
        MemberStatus,
        OrganizationMember,
    )
    from app.database.models.user import User

    user = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=f"{slug_hint}-{uuid.uuid4().hex[:8]}@example.com",
        full_name=slug_hint.title(),
    )
    session.add(user)
    await session.flush()
    org = Organization(
        name=f"{slug_hint.title()} Quota",
        slug=f"{slug_hint}-{uuid.uuid4().hex[:8]}",
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
    await session.flush()
    return org


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


@REQUIRES_DB
@pytest.mark.asyncio
async def test_measured_quota_allows_below_limit(db_session):
    from app.database.models.usage import UsageCounter

    org = await _seed_org_with_owner(db_session, slug_hint="qallow")
    db_session.add(
        UsageCounter(
            organization_id=org.id,
            metric="api_calls",
            period=_current_month(),
            value=4,
        )
    )
    await db_session.flush()

    d = await q.check_quota(
        db_session,
        org.id,
        q.QuotaKey.API_CALLS,
        plan_code="free",
        plan_limits={q.QuotaKey.API_CALLS: 10},
    )
    assert d.allowed is True
    assert d.outcome == "allow"
    assert d.used == 4
    assert d.remaining == 6


@REQUIRES_DB
@pytest.mark.asyncio
async def test_measured_quota_denies_at_limit(db_session):
    from app.database.models.usage import UsageCounter

    org = await _seed_org_with_owner(db_session, slug_hint="qdeny")
    db_session.add(
        UsageCounter(
            organization_id=org.id,
            metric="api_calls",
            period=_current_month(),
            value=10,
        )
    )
    await db_session.flush()

    d = await q.check_quota(
        db_session,
        org.id,
        q.QuotaKey.API_CALLS,
        plan_code="free",
        plan_limits={q.QuotaKey.API_CALLS: 10},
    )
    assert d.allowed is False
    assert d.outcome == "exceeded"
    assert d.used == 10
    assert d.remaining == 0


@REQUIRES_DB
@pytest.mark.asyncio
async def test_measured_ai_requests_sums_the_current_month_only(db_session):
    from app.database.models.usage import UsageCounter

    org = await _seed_org_with_owner(db_session, slug_hint="qai")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db_session.add_all(
        [
            UsageCounter(
                organization_id=org.id,
                metric="ai_messages",
                period=today,
                value=3,
            ),
            UsageCounter(
                organization_id=org.id,
                metric="ai_messages",
                period="2000-01-01",
                value=999,
            ),
        ]
    )
    await db_session.flush()

    d = await q.check_quota(
        db_session,
        org.id,
        q.QuotaKey.AI_REQUESTS,
        plan_code="free",
        plan_limits={q.QuotaKey.AI_REQUESTS: 5},
    )
    assert d.used == 3
    assert d.allowed is True


@REQUIRES_DB
@pytest.mark.asyncio
async def test_measured_users_quota_denies_at_seat_limit(db_session):
    org = await _seed_org_with_owner(db_session, slug_hint="qseat")
    # One active owner exists; a limit of 1 leaves no room for another seat.
    d = await q.check_quota(
        db_session,
        org.id,
        q.QuotaKey.USERS,
        plan_code="free",
        plan_limits={q.QuotaKey.USERS: 1},
    )
    assert d.used == 1
    assert d.allowed is False
    assert d.outcome == "exceeded"


@REQUIRES_DB
@pytest.mark.asyncio
async def test_measured_projects_quota_counts_live_projects(db_session):
    from app.database.models.project import Project

    org = await _seed_org_with_owner(db_session, slug_hint="qproj")
    db_session.add(
        Project(
            organization_id=org.id,
            name="Second",
            slug="second",
            is_default=False,
        )
    )
    await db_session.flush()

    d = await q.check_quota(
        db_session,
        org.id,
        q.QuotaKey.PROJECTS,
        plan_code="free",
        plan_limits={q.QuotaKey.PROJECTS: 5},
    )
    assert d.used == 1  # only the project added in this test exists
    assert d.allowed is True
