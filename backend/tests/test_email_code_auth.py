"""Passwordless email-code sign-in (/api/auth/email-code/*).

The product's sign-in is email-only: a code is emailed, then exchanged for
session cookies. These tests capture the emailed code via a monkeypatched
sender (no SMTP in tests) and exercise the real database path. They skip when
Postgres is not reachable, matching the other DB-backed suites.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def isolated_rate_limit_cache(monkeypatch):
    from app.middleware import rate_limit
    from app.services.cache import get_shared_cache

    cache = get_shared_cache(f"test-email-code-{uuid.uuid4().hex}")
    monkeypatch.setattr(rate_limit, "_cache", lambda: cache)


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
def sent_codes(monkeypatch) -> dict[str, str]:
    """Capture codes the service would email instead of sending them."""
    from app.services import email_service

    codes: dict[str, str] = {}

    def fake_send(to: str, *, code: str, expires_in: str = "10 minutes") -> bool:
        codes[to] = code
        return True

    monkeypatch.setattr(email_service, "send_login_otp", fake_send)
    return codes


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


def _client():
    from httpx import ASGITransport, AsyncClient

    from server import app

    headers = {
        "X-Forwarded-For": f"10.1.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    }
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    )


@REQUIRES_DB
@pytest.mark.asyncio
async def test_new_email_gets_code_and_signs_in(db_session, sent_codes):
    email = f"code-{uuid.uuid4().hex[:10]}@example.com"
    async with _client() as client:
        req = await client.post(
            "/api/auth/email-code/request", json={"email": email, "name": "Ada Tester"}
        )
        assert req.status_code == 200, req.text
        assert email in sent_codes

        ver = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": sent_codes[email]},
        )
        assert ver.status_code == 200, ver.text
        body = ver.json()
        assert body["access_token"] and body["token_type"] == "Bearer"
        cookies = ver.headers.get_list("set-cookie")
        assert any(
            c.startswith("oraone_access_token=") and "HttpOnly" in c for c in cookies
        )

        me = await client.get("/api/auth/me")
        assert me.status_code == 200, me.text
        assert me.json()["email"] == email
        assert me.json()["name"] == "Ada Tester"


@REQUIRES_DB
@pytest.mark.asyncio
async def test_unknown_and_existing_emails_get_identical_responses(
    db_session, sent_codes
):
    email = f"same-{uuid.uuid4().hex[:10]}@example.com"
    async with _client() as client:
        first = await client.post("/api/auth/email-code/request", json={"email": email})
        second = await client.post(
            "/api/auth/email-code/request", json={"email": email}
        )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


@REQUIRES_DB
@pytest.mark.asyncio
async def test_wrong_code_is_rejected(db_session, sent_codes):
    email = f"wrong-{uuid.uuid4().hex[:10]}@example.com"
    async with _client() as client:
        await client.post("/api/auth/email-code/request", json={"email": email})
        wrong = "000000" if sent_codes[email] != "000000" else "111111"
        resp = await client.post(
            "/api/auth/email-code/verify", json={"email": email, "code": wrong}
        )
    assert resp.status_code == 400
    assert "access_token" not in resp.text


@REQUIRES_DB
@pytest.mark.asyncio
async def test_code_is_single_use(db_session, sent_codes):
    email = f"once-{uuid.uuid4().hex[:10]}@example.com"
    async with _client() as client:
        await client.post("/api/auth/email-code/request", json={"email": email})
        code = sent_codes[email]
        ok = await client.post(
            "/api/auth/email-code/verify", json={"email": email, "code": code}
        )
        again = await client.post(
            "/api/auth/email-code/verify", json={"email": email, "code": code}
        )
    assert ok.status_code == 200
    assert again.status_code == 400
