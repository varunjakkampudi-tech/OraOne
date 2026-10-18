"""Public API keys bound to one project must not read or write another project.

The ownership rule and the organization-wide guards are checked without the
database. The knowledge-base listing is checked against Postgres with two
projects in one organization, and skips when the database is not reachable.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from types import SimpleNamespace
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.api.public_api import routes as public_routes


def _key(org, project=None):
    return SimpleNamespace(id=uuid.uuid4(), organization_id=org, project_id=project)


# ── pure rules ───────────────────────────────────────────────────────────────


def test_owns_rejects_rows_from_another_organization():
    org, project = uuid.uuid4(), uuid.uuid4()
    row = SimpleNamespace(organization_id=uuid.uuid4(), project_id=project)
    assert public_routes._owns(row, _key(org, project)) is False


def test_project_key_rejects_rows_from_another_project_in_the_same_org():
    org = uuid.uuid4()
    mine, theirs = uuid.uuid4(), uuid.uuid4()
    row = SimpleNamespace(organization_id=org, project_id=theirs)
    assert public_routes._owns(row, _key(org, mine)) is False
    assert public_routes._owns(
        SimpleNamespace(organization_id=org, project_id=mine), _key(org, mine)
    )


def test_organization_key_sees_every_project_in_its_organization():
    org = uuid.uuid4()
    row = SimpleNamespace(organization_id=org, project_id=uuid.uuid4())
    assert public_routes._owns(row, _key(org, None)) is True


def test_missing_row_is_never_owned():
    assert public_routes._owns(None, _key(uuid.uuid4(), None)) is False


def test_scoped_clause_is_empty_for_organization_keys_and_set_for_project_keys():
    from app.database.models.knowledge_base import KnowledgeBase

    org = uuid.uuid4()
    assert public_routes._scoped(KnowledgeBase, _key(org, None)) == []
    clauses = public_routes._scoped(KnowledgeBase, _key(org, uuid.uuid4()))
    assert len(clauses) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [
        lambda key: public_routes.usage_v1(key=key, session=None),
        lambda key: public_routes.analytics_v1(days=7, key=key, session=None),
    ],
)
async def test_usage_and_analytics_refuse_project_keys(call):
    key = _key(uuid.uuid4(), uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        await call(key)
    assert exc.value.status_code == 403


# ── database: knowledge bases in two projects of one organization ──────────


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


db_only = pytest.mark.skipif(
    not _postgres_reachable(), reason="Postgres is not reachable from this host."
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


@db_only
@pytest.mark.asyncio
async def test_project_key_lists_only_its_own_knowledge_bases(db_session):
    from app.core.security import hash_password
    from app.database.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.project import Project, ProjectStatus
    from app.database.models.user import User

    suffix = uuid.uuid4().hex[:8]
    owner = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=f"api-{suffix}@example.test",
        full_name="API Owner",
        password_hash=hash_password("not-used-in-this-test-4"),
        is_email_verified=True,
    )
    db_session.add(owner)
    await db_session.flush()
    org = Organization(
        name=f"API {suffix}",
        slug=f"api-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=owner.id,
    )
    db_session.add(org)
    await db_session.flush()

    projects = {}
    for label in ("alpha", "beta"):
        project = Project(
            organization_id=org.id,
            name=label,
            slug=f"{label}-{suffix}",
            is_default=label == "alpha",
            status=ProjectStatus.active,
        )
        db_session.add(project)
        await db_session.flush()
        kb = KnowledgeBase(
            organization_id=org.id,
            project_id=project.id,
            name=f"{label} kb",
            status=KnowledgeBaseStatus.active,
        )
        db_session.add(kb)
        await db_session.flush()
        projects[label] = (project.id, kb.id)

    alpha_project, alpha_kb = projects["alpha"]
    beta_project, beta_kb = projects["beta"]

    scoped = await public_routes.list_kbs_v1(
        limit=50, key=_key(org.id, alpha_project), session=db_session
    )
    ids = {row["id"] for row in scoped["data"]}
    assert str(alpha_kb) in ids
    assert str(beta_kb) not in ids

    everything = await public_routes.list_kbs_v1(
        limit=50, key=_key(org.id, None), session=db_session
    )
    all_ids = {row["id"] for row in everything["data"]}
    assert {str(alpha_kb), str(beta_kb)} <= all_ids


@db_only
@pytest.mark.asyncio
async def test_key_stops_working_when_its_project_is_deleted(db_session):
    from datetime import datetime, timezone

    from app.core.security import hash_password
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.project import Project, ProjectStatus
    from app.database.models.user import User
    from app.services import api_key_service

    suffix = uuid.uuid4().hex[:8]
    owner = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=f"deleted-project-{suffix}@example.test",
        full_name="Owner",
        password_hash=hash_password("not-used-in-this-test-5"),
        is_email_verified=True,
    )
    db_session.add(owner)
    await db_session.flush()
    org = Organization(
        name=f"Del {suffix}",
        slug=f"del-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=owner.id,
    )
    db_session.add(org)
    await db_session.flush()
    project = Project(
        organization_id=org.id,
        name="Doomed",
        slug=f"doomed-{suffix}",
        is_default=False,
        status=ProjectStatus.active,
    )
    db_session.add(project)
    await db_session.flush()
    _row, full_key = await api_key_service.create_key(
        db_session,
        org.id,
        name="scoped",
        scopes=["chat:read"],
        created_by_user_id=owner.id,
        project_id=project.id,
    )
    await db_session.flush()

    assert (
        await api_key_service.authenticate(db_session, full_key)
    ).project_id == project.id

    project.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()
    with pytest.raises(HTTPException) as exc:
        await api_key_service.authenticate(db_session, full_key)
    assert exc.value.status_code == 401


@db_only
@pytest.mark.asyncio
async def test_channel_management_cannot_load_an_agent_from_another_project(db_session):
    from app.core.security import hash_password
    from app.database.models.agent import Agent, AgentStatus, AgentType
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.project import Project, ProjectStatus
    from app.database.models.user import User
    from app.api.channels.routes import _load_agent

    suffix = uuid.uuid4().hex[:8]
    owner = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=f"channels-{suffix}@example.test",
        full_name="Channels Owner",
        password_hash=hash_password("not-used-in-this-test-7"),
        is_email_verified=True,
    )
    db_session.add(owner)
    await db_session.flush()
    org = Organization(
        name=f"Channels {suffix}",
        slug=f"channels-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=owner.id,
    )
    db_session.add(org)
    await db_session.flush()
    alpha = Project(
        organization_id=org.id,
        name="alpha",
        slug=f"alpha-{suffix}",
        is_default=True,
        status=ProjectStatus.active,
    )
    beta = Project(
        organization_id=org.id,
        name="beta",
        slug=f"beta-{suffix}",
        is_default=False,
        status=ProjectStatus.active,
    )
    db_session.add_all([alpha, beta])
    await db_session.flush()
    agent = Agent(
        organization_id=org.id,
        project_id=beta.id,
        name="Beta support",
        type=AgentType.chat,
        status=AgentStatus.active,
        model="test/model",
    )
    db_session.add(agent)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await _load_agent(
            db_session,
            agent_id=agent.id,
            organization_id=org.id,
            project_id=alpha.id,
        )
    assert exc.value.status_code == 404

    found = await _load_agent(
        db_session, agent_id=agent.id, organization_id=org.id, project_id=beta.id
    )
    assert found.id == agent.id
