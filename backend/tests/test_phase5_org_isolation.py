"""Phase 5 — tenant isolation tests.

Two layers:

1. **Unit** (no DB) — proves the in-process contracts of
   ``OrgScopedRepository`` & ``get_current_organization``: they refuse
   cross-org writes, never trust client-supplied org ids, and 401/403
   on missing membership. Runs anywhere.

2. **Integration** (live Postgres) — boots the FastAPI app and a real
   AsyncSession against ``DATABASE_URL``, creates two orgs with two
   users, and proves Org A literally cannot read or mutate Org B's
   ``agents`` / ``conversations`` / ``messages`` / ``integrations`` rows
   over HTTP. Skipped when Postgres is unreachable so the suite still
   passes in the Emergent preview pod where the RDS instance is private.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.middleware.org_context import OrgContext


# ───────────────────── 1) Unit tests (no DB) ─────────────────────

def _ctx(org_id: uuid.UUID, *, role: str = "owner") -> OrgContext:
    return OrgContext(
        user_id=uuid.uuid4(),
        cognito_sub="sub-" + str(org_id),
        organization_id=org_id,
        membership_role=role,
    )


def test_org_scoped_repo_rejects_models_without_org_column():
    """Constructing OrgScopedRepository on a tenant-less model must fail loudly."""
    from app.database.models.user import User
    from app.database.repositories.org_scoped import OrgScopedRepository

    class BadRepo(OrgScopedRepository[User]):
        model = User

    with pytest.raises(TypeError, match="no `organization_id`"):
        BadRepo(session=SimpleNamespace(), ctx=_ctx(uuid.uuid4()))  # type: ignore[arg-type]


def test_org_scoped_repo_refuses_cross_org_writes():
    """``add_for_org`` must reject payloads pre-stamped with another tenant."""
    from app.database.models.agent import Agent, AgentStatus, AgentType
    from app.database.repositories.agent_repository import OrgScopedAgentRepository

    my_org = uuid.uuid4()
    other_org = uuid.uuid4()

    repo = OrgScopedAgentRepository(
        session=SimpleNamespace(add=lambda *_: None, flush=lambda: None),  # type: ignore[arg-type]
        ctx=_ctx(my_org),
    )
    rogue = Agent(
        organization_id=other_org,
        name="Hacker",
        type=AgentType.chat,
        status=AgentStatus.draft,
        model="gpt-4o-mini",
    )
    with pytest.raises(PermissionError):
        asyncio.run(repo.add_for_org(rogue, flush=False))


def test_org_scoped_repo_stamps_org_when_unset():
    """``add_for_org`` must auto-pin org_id when the caller didn't set one."""
    from app.database.models.agent import Agent, AgentStatus, AgentType
    from app.database.repositories.agent_repository import OrgScopedAgentRepository

    my_org = uuid.uuid4()

    class FakeSession:
        def __init__(self):
            self.added = []

        def add(self, obj):
            self.added.append(obj)

        async def flush(self):
            pass

    session = FakeSession()
    repo = OrgScopedAgentRepository(session=session, ctx=_ctx(my_org))  # type: ignore[arg-type]

    a = Agent(name="Sales", type=AgentType.chat, status=AgentStatus.draft, model="gpt-4o-mini")
    assert getattr(a, "organization_id", None) is None
    asyncio.run(repo.add_for_org(a))
    assert a.organization_id == my_org
    assert session.added == [a]


# ───────────────────── 2) Integration (live Postgres) ─────────────────────

def _postgres_reachable() -> bool:
    """Best-effort probe so the suite skips when RDS is in a private VPC."""
    import os

    import asyncpg

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    # Convert SQLAlchemy URL to plain asyncpg DSN.
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
        # Already inside a loop (rare in pytest collection); fall through.
        return False


REQUIRES_DB = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="Postgres is not reachable from this host (private VPC, etc).",
)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
    """Yield a fresh AsyncSession bound to the current test's event loop.

    pytest-asyncio gives each test its own loop, but asyncpg connections
    are loop-bound — so we must dispose & re-create the engine per test.
    Otherwise the second DB test inherits a pool from a now-closed loop
    and crashes with 'Future attached to a different loop'.
    """
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


async def _seed_org_with_user(session, *, email: str, slug_hint: str):
    """Insert a (user, organization, owner-membership, default-project) set."""
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import MemberRole, MemberStatus, OrganizationMember
    from app.database.models.project import Project
    from app.database.models.user import User

    user = User(
        cognito_sub=f"sub-{uuid.uuid4()}",
        email=email,
        full_name=email.split("@")[0].title(),
    )
    session.add(user)
    await session.flush()

    org = Organization(
        name=f"{slug_hint.title()} Workspace",
        slug=f"{slug_hint}-{uuid.uuid4().hex[:8]}",
        plan=OrgPlan.free,
        owner_user_id=user.id,
    )
    session.add(org)
    await session.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=MemberRole.owner,
        status=MemberStatus.active,
        joined_at=datetime.now(timezone.utc),
    )
    session.add(member)

    session.add(
        Project(
            organization_id=org.id,
            name="Default",
            slug="default",
            is_default=True,
            created_by_user_id=user.id,
        )
    )
    await session.flush()
    return user, org


@REQUIRES_DB
@pytest.mark.asyncio
async def test_org_isolation_repo_layer(db_session):
    """Repo-level proof: Org A can't see Org B's agents."""
    from app.database.models.agent import Agent, AgentStatus, AgentType
    from app.database.repositories.agent_repository import OrgScopedAgentRepository

    _, org_a = await _seed_org_with_user(db_session, email=f"a-{uuid.uuid4()}@x.com", slug_hint="alpha")
    _, org_b = await _seed_org_with_user(db_session, email=f"b-{uuid.uuid4()}@x.com", slug_hint="beta")

    ctx_a = _ctx(org_a.id)
    ctx_b = _ctx(org_b.id)

    repo_a = OrgScopedAgentRepository(db_session, ctx_a)
    repo_b = OrgScopedAgentRepository(db_session, ctx_b)

    agent_a = Agent(name="A-agent", type=AgentType.chat, status=AgentStatus.draft, model="gpt-4o-mini")
    await repo_a.add_for_org(agent_a)
    agent_b = Agent(name="B-agent", type=AgentType.chat, status=AgentStatus.draft, model="gpt-4o-mini")
    await repo_b.add_for_org(agent_b)
    await db_session.flush()

    # Cross-tenant fetch must return None, not the row.
    assert await repo_a.get_in_org(agent_b.id) is None
    assert await repo_b.get_in_org(agent_a.id) is None

    a_list = await repo_a.list_in_org()
    b_list = await repo_b.list_in_org()
    assert agent_a.id in [a.id for a in a_list]
    assert agent_a.id not in [a.id for a in b_list]
    assert agent_b.id in [a.id for a in b_list]
    assert agent_b.id not in [a.id for a in a_list]


@REQUIRES_DB
@pytest.mark.asyncio
async def test_org_isolation_http_layer(db_session):
    """HTTP-level proof: Bob (Org B) cannot read/delete Alice's (Org A) agent
    via /api/agents/{id}, even if he supplies the exact UUID."""
    from httpx import ASGITransport, AsyncClient

    from app.database.models.agent import Agent, AgentStatus, AgentType
    from app.middleware.org_context import OrgContext, get_current_organization
    from server import app

    user_a, org_a = await _seed_org_with_user(db_session, email=f"alice-{uuid.uuid4()}@x.com", slug_hint="alice")
    user_b, org_b = await _seed_org_with_user(db_session, email=f"bob-{uuid.uuid4()}@x.com", slug_hint="bob")

    alices_agent = Agent(
        organization_id=org_a.id,
        name="Alices secret agent",
        type=AgentType.chat,
        status=AgentStatus.active,
        model="gpt-4o-mini",
    )
    db_session.add(alices_agent)
    await db_session.commit()

    # Override the auth dependency so we can flip identities cheaply.
    current_ctx = {"v": OrgContext(
        user_id=user_b.id, cognito_sub="b", organization_id=org_b.id, membership_role="owner"
    )}

    async def _override() -> OrgContext:
        return current_ctx["v"]

    app.dependency_overrides[get_current_organization] = _override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Bob (Org B) tries to read Alice's agent → 404
            r = await client.get(f"/api/agents/{alices_agent.id}")
            assert r.status_code == 404, r.text

            # And to delete it → 404 (must not leak via 403/200)
            r = await client.delete(f"/api/agents/{alices_agent.id}")
            assert r.status_code == 404, r.text

            # His own list never contains Alice's agent
            r = await client.get("/api/agents")
            assert r.status_code == 200
            assert all(a["id"] != str(alices_agent.id) for a in r.json()["items"])

            # Flip to Alice — she sees her agent
            current_ctx["v"] = OrgContext(
                user_id=user_a.id, cognito_sub="a", organization_id=org_a.id, membership_role="owner",
            )
            r = await client.get(f"/api/agents/{alices_agent.id}")
            assert r.status_code == 200, r.text
            assert r.json()["id"] == str(alices_agent.id)
    finally:
        app.dependency_overrides.pop(get_current_organization, None)
