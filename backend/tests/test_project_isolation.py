"""Project isolation inside one organization.

Two projects belong to the same organization. Knowledge and visitor memory
created in one project must never be visible from the other. These tests run
against Postgres and roll back after each case. They skip when the database is
not reachable, matching the other database-backed suites.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio


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


pytestmark = pytest.mark.skipif(
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
    maker = db_session_module.AsyncSessionLocal
    assert maker is not None

    async with maker() as s:
        yield s
        await s.rollback()

    await dispose_engine()


async def _seed_org_with_two_projects(session):
    """One organization, two projects, one knowledge base and one chunk each."""
    from app.core.security import hash_password
    from app.database.models.document_chunk import DocumentChunk
    from app.database.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.project import Project, ProjectStatus
    from app.database.models.user import User

    suffix = uuid.uuid4().hex[:8]
    owner = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=f"owner-{suffix}@example.test",
        full_name="Project Owner",
        password_hash=hash_password("not-used-in-this-test-1"),
        is_email_verified=True,
    )
    session.add(owner)
    await session.flush()

    org = Organization(
        name=f"Acme {suffix}",
        slug=f"acme-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=owner.id,
    )
    session.add(org)
    await session.flush()

    projects = {}
    for label, is_default in (("alpha", True), ("beta", False)):
        project = Project(
            organization_id=org.id,
            name=f"{label} project",
            slug=f"{label}-{suffix}",
            is_default=is_default,
            status=ProjectStatus.active,
        )
        session.add(project)
        await session.flush()
        projects[label] = project

    chunks = {}
    for label, project in projects.items():
        kb = KnowledgeBase(
            organization_id=org.id,
            project_id=project.id,
            name=f"{label} knowledge",
            status=KnowledgeBaseStatus.active,
        )
        session.add(kb)
        await session.flush()
        chunk = DocumentChunk(
            organization_id=org.id,
            project_id=project.id,
            knowledge_base_id=kb.id,
            chunk_index=0,
            content=f"Refund policy for the {label} business: 14 days.",
        )
        session.add(chunk)
        await session.flush()
        chunks[label] = chunk

    return org, projects, chunks


@pytest.mark.asyncio
async def test_retrieval_filter_returns_only_the_requested_project(db_session):
    from app.services import rag_service

    org, projects, chunks = await _seed_org_with_two_projects(db_session)

    for label in ("alpha", "beta"):
        base = rag_service._base_query(org.id, None, projects[label].id)
        rows = (await db_session.execute(base)).all()
        ids = {row.chunk_id for row in rows}
        assert ids == {chunks[label].id}, f"{label} saw another project's chunks"


@pytest.mark.asyncio
async def test_visitor_memory_does_not_cross_projects(db_session):
    from app.services import visitor_service

    org, projects, _chunks = await _seed_org_with_two_projects(db_session)
    alpha, beta = projects["alpha"].id, projects["beta"].id

    in_alpha = await visitor_service.upsert_profile(
        db_session,
        organization_id=org.id,
        project_id=alpha,
        visitor_key="browser-visitor-1",
        email="pat@example.test",
        channel="chat",
    )
    in_beta = await visitor_service.upsert_profile(
        db_session,
        organization_id=org.id,
        project_id=beta,
        visitor_key="browser-visitor-1",
        email="pat@example.test",
        channel="chat",
    )
    assert in_alpha.id != in_beta.id
    assert in_alpha.project_id == alpha
    assert in_beta.project_id == beta

    # An identity known in alpha is not recognised from beta.
    found = await visitor_service.find_by_identity(
        db_session, org.id, beta, email="pat@example.test"
    )
    assert found is not None and found.id == in_beta.id


@pytest.mark.asyncio
async def test_missing_project_resolves_to_the_default_project(db_session):
    from app.services import project_scope

    org, projects, _chunks = await _seed_org_with_two_projects(db_session)

    resolved = await project_scope.resolve_project_id(db_session, org.id, None)
    assert resolved == projects["alpha"].id

    explicit = await project_scope.resolve_project_id(
        db_session, org.id, projects["beta"].id
    )
    assert explicit == projects["beta"].id


@pytest.mark.asyncio
async def test_organization_without_projects_fails_closed(db_session):
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.user import User
    from app.core.security import hash_password
    from app.services import project_scope

    suffix = uuid.uuid4().hex[:8]
    owner = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=f"lonely-{suffix}@example.test",
        full_name="Lonely Owner",
        password_hash=hash_password("not-used-in-this-test-2"),
        is_email_verified=True,
    )
    db_session.add(owner)
    await db_session.flush()
    org = Organization(
        name=f"Empty {suffix}",
        slug=f"empty-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=owner.id,
    )
    db_session.add(org)
    await db_session.flush()

    with pytest.raises(project_scope.ProjectScopeError):
        await project_scope.resolve_project_id(db_session, org.id, None)
