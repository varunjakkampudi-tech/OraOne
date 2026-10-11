"""Phase 6 — Knowledge Base Foundation tests."""
from __future__ import annotations

import asyncio
import io
import os
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.middleware.org_context import OrgContext


def _ctx(org_id: uuid.UUID, *, user_id: uuid.UUID | None = None, role: str = "owner") -> OrgContext:
    return OrgContext(
        user_id=user_id or uuid.uuid4(),
        cognito_sub="sub-" + str(org_id),
        organization_id=org_id,
        membership_role=role,
    )


def _postgres_reachable() -> bool:
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


# ─────────────────── Unit (no DB) ───────────────────

def test_storage_build_key_is_safe():
    from app.services.storage import build_key

    key = build_key(
        organization_id="11111111-1111-1111-1111-111111111111",
        knowledge_base_id="22222222-2222-2222-2222-222222222222",
        filename="my report (final)/v2.pdf",
    )
    assert key.startswith(
        "org/11111111-1111-1111-1111-111111111111/kb/22222222-2222-2222-2222-222222222222/"
    )
    # path separators must be neutralised
    assert "/v2.pdf" not in key.split("__", 1)[1]
    assert " " not in key  # spaces replaced
    assert key.endswith(".pdf")


def test_storage_local_fallback(tmp_path, monkeypatch):
    """When no S3_BUCKET, files must be written to UPLOAD_DIR."""
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

    from app.services import storage

    key = "org/o/kb/k/abc__hello.txt"
    s3_key = storage.put_object(
        key=key, body=io.BytesIO(b"hello world"), content_type="text/plain"
    )
    assert s3_key.startswith("local://")
    assert storage.is_local_key(s3_key) is True
    assert storage.local_path(s3_key).read_bytes() == b"hello world"


def test_swagger_documents_all_required_endpoints():
    """OpenAPI must register the spec'd paths + describe their query params."""
    from server import app

    paths = app.openapi()["paths"]
    required = [
        "/api/knowledge-bases",
        "/api/knowledge-bases/{kb_id}",
        "/api/documents/upload",
        "/api/documents",
        "/api/documents/{document_id}",
        "/api/knowledge/stats",
    ]
    for p in required:
        assert p in paths, f"missing path: {p}"

    list_kb = paths["/api/knowledge-bases"]["get"]
    params = {p["name"] for p in list_kb.get("parameters", [])}
    for must_have in ("q", "status", "limit", "offset", "sort"):
        assert must_have in params

    upload = paths["/api/documents/upload"]["post"]
    assert "multipart/form-data" in upload["requestBody"]["content"]


def test_schemas_validate_required_fields():
    from pydantic import ValidationError

    from app.schemas.knowledge import KnowledgeBaseCreate

    # name length boundary
    with pytest.raises(ValidationError):
        KnowledgeBaseCreate(name="")
    with pytest.raises(ValidationError):
        KnowledgeBaseCreate(name="x" * 200)
    ok = KnowledgeBaseCreate(name="Product Docs")
    assert ok.name == "Product Docs"


# ─────────────────── DB-backed integration ───────────────────

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


async def _seed_org(session, *, email: str, slug_hint: str):
    from datetime import datetime, timezone

    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.organization_member import (
        MemberRole, MemberStatus, OrganizationMember,
    )
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
async def test_kb_crud_and_upload(db_session, tmp_path, monkeypatch):
    """End-to-end: create KB, upload doc, list documents, stats reflect both."""
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

    from app.middleware.org_context import get_current_organization
    from server import app

    user, org = await _seed_org(db_session, email=f"kb-{uuid.uuid4()}@x.com", slug_hint="kb")
    await db_session.commit()

    async def _override() -> OrgContext:
        return _ctx(org.id, user_id=user.id)

    app.dependency_overrides[get_current_organization] = _override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Stats should start at zero
            r = await client.get("/api/knowledge/stats")
            assert r.status_code == 200
            stats = r.json()
            assert stats["total_knowledge_bases"] == 0
            assert stats["total_documents"] == 0
            assert stats["total_chunks"] >= 0

            # Create a KB
            r = await client.post(
                "/api/knowledge-bases",
                json={"name": "Product Docs", "description": "Public-facing docs", "status": "active"},
            )
            assert r.status_code == 201, r.text
            kb = r.json()
            assert kb["name"] == "Product Docs"
            assert kb["document_count"] == 0
            kb_id = kb["id"]

            # List + search
            r = await client.get("/api/knowledge-bases", params={"q": "product"})
            assert r.status_code == 200
            assert any(x["id"] == kb_id for x in r.json()["items"])

            # Upload a document
            r = await client.post(
                "/api/documents/upload",
                data={"knowledge_base_id": kb_id},
                files={"file": ("hello.txt", b"hello world", "text/plain")},
            )
            assert r.status_code == 201, r.text
            doc = r.json()
            assert doc["filename"] == "hello.txt"
            assert doc["status"] == "pending"
            assert doc["s3_key"].startswith("local://")  # we forced local mode

            # List documents
            r = await client.get("/api/documents", params={"knowledge_base_id": kb_id})
            assert r.status_code == 200
            assert r.json()["total"] == 1

            # Stats now show 1 KB, 1 document
            r = await client.get("/api/knowledge/stats")
            stats = r.json()
            assert stats["total_knowledge_bases"] == 1
            assert stats["total_documents"] == 1
            assert stats["total_chunks"] >= 0  # background processing may have run

            # Soft-delete the document
            r = await client.delete(f"/api/documents/{doc['id']}")
            assert r.status_code == 204
            r = await client.get("/api/documents", params={"knowledge_base_id": kb_id})
            assert r.json()["total"] == 0

            # Soft-delete the KB
            r = await client.delete(f"/api/knowledge-bases/{kb_id}")
            assert r.status_code == 204
            r = await client.get("/api/knowledge-bases")
            assert all(x["id"] != kb_id for x in r.json()["items"])
    finally:
        app.dependency_overrides.pop(get_current_organization, None)


@REQUIRES_DB
@pytest.mark.asyncio
async def test_kb_org_isolation(db_session, tmp_path, monkeypatch):
    """Org A must not see Org B's knowledge bases / documents."""
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))

    from app.database.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
    from app.middleware.org_context import get_current_organization
    from server import app

    user_a, org_a = await _seed_org(db_session, email=f"a-{uuid.uuid4()}@x.com", slug_hint="a")
    user_b, org_b = await _seed_org(db_session, email=f"b-{uuid.uuid4()}@x.com", slug_hint="b")

    # Seed a KB directly into Org A
    kb_a = KnowledgeBase(
        organization_id=org_a.id,
        name="Alice secrets",
        status=KnowledgeBaseStatus.active,
    )
    db_session.add(kb_a)
    await db_session.commit()

    current_ctx = {"v": _ctx(org_b.id, user_id=user_b.id)}

    async def _override() -> OrgContext:
        return current_ctx["v"]

    app.dependency_overrides[get_current_organization] = _override
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Bob (Org B) tries to fetch Alice's KB by id → 404
            r = await client.get(f"/api/knowledge-bases/{kb_a.id}")
            assert r.status_code == 404

            # Listing shows nothing of Alice's
            r = await client.get("/api/knowledge-bases")
            assert all(x["id"] != str(kb_a.id) for x in r.json()["items"])

            # Bob cannot upload into Alice's KB either
            r = await client.post(
                "/api/documents/upload",
                data={"knowledge_base_id": str(kb_a.id)},
                files={"file": ("oops.txt", b"x", "text/plain")},
            )
            assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_organization, None)
