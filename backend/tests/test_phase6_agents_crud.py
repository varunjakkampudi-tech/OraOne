"""Phase 6 — Agent CRUD tests.

Mix of fast unit tests (no DB) and DB-backed integration tests. The
DB-backed tests auto-skip when Postgres isn't reachable so the suite
passes everywhere; the unit tests run anywhere.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.middleware.org_context import OrgContext


# ───────────────────── Helpers shared with Phase 5 ─────────────────────

def _ctx(org_id: uuid.UUID, *, user_id: uuid.UUID | None = None, role: str = "owner") -> OrgContext:
    return OrgContext(
        user_id=user_id or uuid.uuid4(),
        cognito_sub="sub-" + str(org_id),
        organization_id=org_id,
        membership_role=role,
    )


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


# ─────────────────── 1) Unit-level tests (no DB) ───────────────────

def test_schemas_partial_update_keeps_all_optional():
    """`AgentUpdate` must allow zero fields → no validation errors."""
    from app.schemas.agents import AgentUpdate
    assert AgentUpdate().model_dump(exclude_unset=True) == {}


def test_schemas_temperature_bounds():
    from pydantic import ValidationError
    from app.schemas.agents import AgentCreate

    with pytest.raises(ValidationError):
        AgentCreate(name="x", type="chat", temperature=3.0)

    with pytest.raises(ValidationError):
        AgentCreate(name="x", type="chat", temperature=-0.1)

    ok = AgentCreate(name="x", type="chat", temperature=0.5)
    assert ok.temperature == 0.5


def test_schemas_max_tokens_bounds():
    from pydantic import ValidationError
    from app.schemas.agents import AgentCreate

    with pytest.raises(ValidationError):
        AgentCreate(name="x", type="chat", max_tokens=0)

    with pytest.raises(ValidationError):
        AgentCreate(name="x", type="chat", max_tokens=99999)

    ok = AgentCreate(name="x", type="chat", max_tokens=2048)
    assert ok.max_tokens == 2048


def test_audit_emits_structured_record(caplog):
    """`audit()` must emit a JSON record on the `app.audit` logger."""
    import json as _json

    from app.services.audit import audit

    with caplog.at_level(logging.INFO, logger="app.audit"):
        audit(
            "create",
            resource="agent",
            resource_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            organization_id="11111111-1111-1111-1111-111111111111",
            user_id="22222222-2222-2222-2222-222222222222",
            after={"name": "Sales", "type": "chat"},
        )

    assert any("AUDIT" in r.getMessage() for r in caplog.records)
    msg = next(r.getMessage() for r in caplog.records if "AUDIT" in r.getMessage())
    payload = _json.loads(msg.split("AUDIT ", 1)[1])
    assert payload["action"] == "create"
    assert payload["resource"] == "agent"
    assert payload["resource_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert payload["after"]["name"] == "Sales"
    assert payload["organization_id"] == "11111111-1111-1111-1111-111111111111"


def test_router_paths_registered():
    """OpenAPI must expose the full CRUD surface required by the spec."""
    from server import app
    paths = set(app.openapi()["paths"].keys())
    assert "/api/agents" in paths
    assert "/api/agents/{agent_id}" in paths
    # And the methods exposed
    methods_on_root = set(app.openapi()["paths"]["/api/agents"].keys())
    methods_on_item = set(app.openapi()["paths"]["/api/agents/{agent_id}"].keys())
    assert {"get", "post"}.issubset(methods_on_root)
    assert {"get", "put", "delete"}.issubset(methods_on_item)


def test_swagger_describes_filters_and_pagination():
    """The list endpoint must document `q`, `type`, `status`, `model`, `limit`, `offset`."""
    from server import app
    op = app.openapi()["paths"]["/api/agents"]["get"]
    names = {p["name"] for p in op.get("parameters", [])}
    for required in ("q", "type", "status", "model", "limit", "offset", "sort"):
        assert required in names, f"missing query param documentation: {required!r}"


# ─────────────────── 2) DB-backed integration tests ───────────────────

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


async def _seed_org(session, *, email: str, slug_hint: str):
    from datetime import datetime, timezone

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
async def test_crud_full_lifecycle(db_session):
    """Create → read → update → delete an agent through the HTTP layer."""
    from app.middleware.org_context import get_current_organization
    from server import app

    user, org = await _seed_org(db_session, email=f"alice-{uuid.uuid4()}@x.com", slug_hint="alice")
    await db_session.commit()

    async def _override() -> OrgContext:
        return _ctx(org.id, user_id=user.id)

    app.dependency_overrides[get_current_organization] = _override
    try:
        from httpx import ASGITransport, AsyncClient
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # CREATE
            r = await client.post(
                "/api/agents",
                json={
                    "name": "Sales bot",
                    "type": "sales",
                    "description": "qualifies inbound leads",
                    "model": "gpt-4o-mini",
                    "status": "active",
                    "system_prompt": "You are a friendly SDR.",
                    "temperature": 0.4,
                    "voice": "Aria",
                    "language": "en-US",
                    "max_tokens": 800,
                },
            )
            assert r.status_code == 201, r.text
            created = r.json()
            agent_id = created["id"]
            assert created["name"] == "Sales bot"
            assert created["temperature"] == 0.4
            assert created["voice"] == "Aria"

            # READ ONE
            r = await client.get(f"/api/agents/{agent_id}")
            assert r.status_code == 200 and r.json()["id"] == agent_id

            # UPDATE (partial)
            r = await client.put(
                f"/api/agents/{agent_id}",
                json={"status": "paused", "temperature": 0.9},
            )
            assert r.status_code == 200, r.text
            assert r.json()["status"] == "paused"
            assert r.json()["temperature"] == 0.9
            assert r.json()["name"] == "Sales bot"  # unchanged

            # LIST + filter + search
            r = await client.get("/api/agents", params={"status": "paused"})
            assert r.status_code == 200
            assert any(a["id"] == agent_id for a in r.json()["items"])

            r = await client.get("/api/agents", params={"q": "sales"})
            assert r.status_code == 200 and r.json()["total"] >= 1

            r = await client.get("/api/agents", params={"type": "chat"})
            assert all(a["id"] != agent_id for a in r.json()["items"])

            # DELETE
            r = await client.delete(f"/api/agents/{agent_id}")
            assert r.status_code == 204
            # Soft-deleted → 404 on subsequent reads
            r = await client.get(f"/api/agents/{agent_id}")
            assert r.status_code == 404
            r = await client.get("/api/agents")
            assert all(a["id"] != agent_id for a in r.json()["items"])
    finally:
        app.dependency_overrides.pop(get_current_organization, None)


@REQUIRES_DB
@pytest.mark.asyncio
async def test_pagination_and_sort(db_session):
    from app.middleware.org_context import get_current_organization
    from server import app

    user, org = await _seed_org(db_session, email=f"pg-{uuid.uuid4()}@x.com", slug_hint="pg")
    await db_session.commit()

    async def _override() -> OrgContext:
        return _ctx(org.id, user_id=user.id)

    app.dependency_overrides[get_current_organization] = _override
    try:
        from httpx import ASGITransport, AsyncClient
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for i in range(5):
                r = await client.post("/api/agents", json={"name": f"A{i}", "type": "chat"})
                assert r.status_code == 201

            r = await client.get("/api/agents", params={"limit": 2, "offset": 0, "sort": "name"})
            assert r.status_code == 200
            page1 = r.json()
            assert len(page1["items"]) == 2
            assert page1["total"] >= 5
            assert page1["limit"] == 2 and page1["offset"] == 0

            r = await client.get("/api/agents", params={"limit": 2, "offset": 2, "sort": "name"})
            page2 = r.json()
            page1_ids = {a["id"] for a in page1["items"]}
            page2_ids = {a["id"] for a in page2["items"]}
            assert page1_ids.isdisjoint(page2_ids)
    finally:
        app.dependency_overrides.pop(get_current_organization, None)
