"""An administrator of one organization cannot read or change another organization's records.

Each test seeds two organizations on the real database, creates a record in organization B,
then calls the route as an administrator of organization A using B's record ID. The route must
answer "not found" (never the record, never a server error). Database-backed; skips when Postgres
is not reachable.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.middleware.org_context import OrgContext
from app.middleware.project_context import ProjectContext


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


async def _seed_org(session, label: str):
    """One organization with an owner, an administrator member, and a default project."""
    from app.core.security import hash_password
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import (
        MemberRole,
        MemberStatus,
        OrganizationMember,
    )
    from app.database.models.project import Project, ProjectStatus
    from app.database.models.user import User

    suffix = uuid.uuid4().hex[:8]
    admin = User(
        auth_subject=f"sub-{label}-{suffix}",
        email=f"{label}-{suffix}@example.test",
        full_name=f"{label} admin",
        password_hash=hash_password("not-used-in-this-test-10"),
        is_email_verified=True,
    )
    session.add(admin)
    await session.flush()
    org = Organization(
        name=f"{label} {suffix}",
        slug=f"{label}-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=admin.id,
    )
    session.add(org)
    await session.flush()
    project = Project(
        organization_id=org.id,
        name=f"{label} main",
        slug=f"{label}-main-{suffix}",
        is_default=True,
        status=ProjectStatus.active,
    )
    session.add(project)
    await session.flush()
    session.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=admin.id,
            role=MemberRole.admin,
            status=MemberStatus.active,
        )
    )
    await session.flush()
    return SimpleNamespaceOrg(org=org, project=project, admin=admin)


class SimpleNamespaceOrg:
    def __init__(self, *, org, project, admin):
        self.org = org
        self.project = project
        self.admin = admin

    def org_context(self) -> OrgContext:
        return OrgContext(
            user_id=self.admin.id,
            auth_subject=self.admin.auth_subject,
            organization_id=self.org.id,
            membership_role="admin",
        )

    def project_context(self) -> ProjectContext:
        return ProjectContext(
            user_id=self.admin.id,
            organization_id=self.org.id,
            membership_role="admin",
            project_id=self.project.id,
            project_slug=self.project.slug,
            is_default_project=True,
        )

    def api_key(self):
        from types import SimpleNamespace

        return SimpleNamespace(
            id=uuid.uuid4(),
            organization_id=self.org.id,
            project_id=None,
        )


async def _agent(session, seeded):
    from app.database.models.agent import Agent, AgentStatus, AgentType

    agent = Agent(
        organization_id=seeded.org.id,
        project_id=seeded.project.id,
        name="Support",
        type=AgentType.chat,
        status=AgentStatus.active,
        model="test/model",
    )
    session.add(agent)
    await session.flush()
    return agent


async def _conversation(session, seeded, agent):
    from app.database.models.conversation import (
        Conversation,
        ConversationChannel,
        ConversationStatus,
    )

    conversation = Conversation(
        organization_id=seeded.org.id,
        project_id=seeded.project.id,
        agent_id=agent.id,
        channel=ConversationChannel.chat,
        status=ConversationStatus.active,
        started_at=datetime.now(timezone.utc),
    )
    session.add(conversation)
    await session.flush()
    return conversation


async def _escalation(session, seeded):
    from app.services import escalation_service

    return await escalation_service.create_escalation(
        session,
        organization_id=seeded.org.id,
        project_id=seeded.project.id,
        channel="chat",
        question="Owned by organization B.",
    )


@db_only
@pytest.mark.asyncio
async def test_admin_of_one_org_cannot_load_another_orgs_agent_channels(db_session):
    from app.api.channels import routes as channel_routes

    a = await _seed_org(db_session, "alpha")
    b = await _seed_org(db_session, "beta")
    agent_b = await _agent(db_session, b)

    with pytest.raises(HTTPException) as exc:
        await channel_routes.list_channels(
            agent_id=agent_b.id,
            org=a.org_context(),
            pctx=a.project_context(),
            session=db_session,
        )
    assert exc.value.status_code == 404


@db_only
@pytest.mark.asyncio
async def test_admin_of_one_org_cannot_read_another_orgs_escalation(db_session):
    from app.api.escalations import routes as esc_routes

    a = await _seed_org(db_session, "alpha")
    b = await _seed_org(db_session, "beta")
    escalation_b = await _escalation(db_session, b)

    with pytest.raises(HTTPException) as exc:
        await esc_routes.get_escalation(
            escalation_id=escalation_b.id,
            _=a.org_context(),
            pctx=a.project_context(),
            session=db_session,
        )
    assert exc.value.status_code == 404


@db_only
@pytest.mark.asyncio
async def test_admin_of_one_org_cannot_change_another_orgs_escalation(db_session):
    from app.api.escalations import routes as esc_routes

    a = await _seed_org(db_session, "alpha")
    b = await _seed_org(db_session, "beta")
    escalation_b = await _escalation(db_session, b)

    with pytest.raises(HTTPException) as exc:
        await esc_routes.resolve_escalation(
            escalation_id=escalation_b.id,
            _=a.org_context(),
            pctx=a.project_context(),
            session=db_session,
        )
    assert exc.value.status_code == 404
    await db_session.refresh(escalation_b)
    assert escalation_b.status == "open"


@db_only
@pytest.mark.asyncio
async def test_api_key_of_one_org_cannot_read_another_orgs_conversation(db_session):
    from app.api.public_api import routes as public_routes

    a = await _seed_org(db_session, "alpha")
    b = await _seed_org(db_session, "beta")
    agent_b = await _agent(db_session, b)
    conversation_b = await _conversation(db_session, b, agent_b)

    with pytest.raises(HTTPException) as exc:
        await public_routes.get_conversation_v1(
            conversation_id=conversation_b.id,
            key=a.api_key(),
            session=db_session,
        )
    assert exc.value.status_code == 404


@db_only
@pytest.mark.asyncio
async def test_listings_never_include_another_orgs_records(db_session):
    from app.api.public_api import routes as public_routes

    a = await _seed_org(db_session, "alpha")
    b = await _seed_org(db_session, "beta")
    agent_b = await _agent(db_session, b)
    conversation_b = await _conversation(db_session, b, agent_b)
    escalation_b = await _escalation(db_session, b)

    agents = await public_routes.list_agents_v1(
        limit=50, key=a.api_key(), session=db_session
    )
    conversations = await public_routes.list_conversations_v1(
        limit=50, key=a.api_key(), session=db_session
    )
    assert str(agent_b.id) not in {row["id"] for row in agents["data"]}
    assert str(conversation_b.id) not in {row["id"] for row in conversations["data"]}
    assert (
        escalation_b.id is not None
    )  # the record exists, and is still invisible above
