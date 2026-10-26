"""Cookie-based auth: sign-in, refresh and logout must set and clear httpOnly cookies
(app/core/cookies.py) as defense-in-depth alongside the existing bearer
token flow, and protected routes must accept either.

DB-backed (needs a real user row + password hash for a real login), auto-skips
when Postgres isn't reachable — same pattern as test_phase6_agents_crud.py.
"""

from __future__ import annotations

import asyncio
import secrets
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def isolated_rate_limit_cache(monkeypatch):
    """Exercise real limits without sharing counters with another test or API."""
    from app.middleware import rate_limit
    from app.services.cache import get_shared_cache

    cache = get_shared_cache(f"test-auth-cookies-{uuid.uuid4().hex}")
    monkeypatch.setattr(rate_limit, "_cache", lambda: cache)


@pytest.fixture(autouse=True)
def stub_code_delivery(monkeypatch):
    """No SMTP in tests: report the code as delivered so sign-in can proceed."""
    from app.services import email_service

    monkeypatch.setattr(
        email_service,
        "send_login_otp",
        lambda to, *, code, expires_in="10 minutes": True,
    )


def _postgres_reachable() -> bool:
    import os

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


async def _seed_user(session, *, email: str, password: str):
    from app.core.security import hash_password
    from app.database.models.user import User

    user = User(
        auth_subject=f"sub-{uuid.uuid4()}",
        email=email,
        full_name="Cookie Auth Tester",
        password_hash=hash_password(password),
        is_email_verified=True,
    )
    session.add(user)
    await session.flush()
    await session.commit()
    return user


async def _login_via_otp(client, *, email: str, password: str):
    """Sign in through the passwordless flow used by the product.

    The emailed code is read from the shared cache here, standing in for
    checking the inbox. ``password`` is accepted for signature compatibility
    with the seeding helper and is not used by the product sign-in.
    """

    del password
    from unittest.mock import patch

    from app.services import email_service

    sent: dict[str, str] = {}

    def _capture(to: str, *, code: str, expires_in: str = "5 minutes") -> bool:
        sent[to] = code
        return True

    with patch.object(email_service, "send_login_otp", _capture):
        request_resp = await client.post(
            "/api/auth/email-code/request", json={"email": email}
        )
    assert request_resp.status_code == 200, request_resp.text

    code = sent.get(email.strip().lower())
    assert code, "sign-in code was not emailed"

    return await client.post(
        "/api/auth/email-code/verify", json={"email": email, "code": code}
    )


@REQUIRES_DB
@pytest.mark.asyncio
async def test_login_sets_httponly_samesite_cookies(db_session):
    from httpx import ASGITransport, AsyncClient

    from server import app

    email = f"cookie-{uuid.uuid4()}@x.com"
    password = "T" + secrets.token_urlsafe(16)
    await _seed_user(db_session, email=email, password=password)

    transport = ASGITransport(app=app)
    headers = {
        "X-Forwarded-For": f"10.0.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    }
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as client:
        resp = await _login_via_otp(client, email=email, password=password)
        assert resp.status_code == 200, resp.text

        set_cookie_headers = resp.headers.get_list("set-cookie")
        access_cookie = next(
            (h for h in set_cookie_headers if h.startswith("oraone_access_token=")),
            None,
        )
        refresh_cookie = next(
            (h for h in set_cookie_headers if h.startswith("oraone_refresh_token=")),
            None,
        )
        assert access_cookie is not None, set_cookie_headers
        assert refresh_cookie is not None, set_cookie_headers

        for cookie in (access_cookie, refresh_cookie):
            assert "HttpOnly" in cookie
            assert "SameSite=lax" in cookie or "SameSite=Lax" in cookie
        # Refresh cookie scoped narrowly to the auth path, unlike the access cookie.
        assert "Path=/api/auth" in refresh_cookie
        assert "Path=/" in access_cookie and "Path=/api/auth" not in access_cookie


@REQUIRES_DB
@pytest.mark.asyncio
async def test_protected_route_accepts_cookie_without_authorization_header(db_session):
    """/api/auth/me must work from the cookie alone (browser session), with
    no Authorization header at all."""
    from httpx import ASGITransport, AsyncClient

    from server import app

    email = f"cookie-{uuid.uuid4()}@x.com"
    password = "T" + secrets.token_urlsafe(16)
    await _seed_user(db_session, email=email, password=password)

    transport = ASGITransport(app=app)
    headers = {
        "X-Forwarded-For": f"10.0.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    }
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as client:
        login_resp = await _login_via_otp(client, email=email, password=password)
        assert login_resp.status_code == 200

        # httpx's AsyncClient persists cookies from Set-Cookie automatically
        # across requests on the same client — no Authorization header set.
        me_resp = await client.get("/api/auth/me")
        assert me_resp.status_code == 200, me_resp.text
        assert me_resp.json()["email"] == email


@REQUIRES_DB
@pytest.mark.asyncio
async def test_refresh_works_from_cookie_alone_with_no_body(db_session):
    from httpx import ASGITransport, AsyncClient

    from server import app

    email = f"cookie-{uuid.uuid4()}@x.com"
    password = "T" + secrets.token_urlsafe(16)
    await _seed_user(db_session, email=email, password=password)

    transport = ASGITransport(app=app)
    headers = {
        "X-Forwarded-For": f"10.0.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    }
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as client:
        login_resp = await _login_via_otp(client, email=email, password=password)
        assert login_resp.status_code == 200
        old_access_token = login_resp.json()["access_token"]

        # No JSON body at all — must fall back to the refresh cookie.
        refresh_resp = await client.post("/api/auth/refresh")
        assert refresh_resp.status_code == 200, refresh_resp.text
        assert refresh_resp.json()["access_token"] != old_access_token


@REQUIRES_DB
@pytest.mark.asyncio
async def test_logout_clears_cookies_and_revokes_refresh(db_session):
    from httpx import ASGITransport, AsyncClient

    from server import app

    email = f"cookie-{uuid.uuid4()}@x.com"
    password = "T" + secrets.token_urlsafe(16)
    await _seed_user(db_session, email=email, password=password)

    transport = ASGITransport(app=app)
    headers = {
        "X-Forwarded-For": f"10.0.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    }
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as client:
        login_resp = await _login_via_otp(client, email=email, password=password)
        assert login_resp.status_code == 200

        original_refresh = client.cookies.get("oraone_refresh_token")
        assert original_refresh
        logout_resp = await client.post("/api/auth/logout")
        assert logout_resp.status_code == 200

        set_cookie_headers = logout_resp.headers.get_list("set-cookie")
        # Cleared cookies are re-set with Max-Age=0 / an expiry in the past.
        access_clear = next(
            (h for h in set_cookie_headers if h.startswith("oraone_access_token=")),
            None,
        )
        refresh_clear = next(
            (h for h in set_cookie_headers if h.startswith("oraone_refresh_token=")),
            None,
        )
        assert access_clear and (
            "Max-Age=0" in access_clear or "01 Jan 1970" in access_clear
        )
        assert refresh_clear and (
            "Max-Age=0" in refresh_clear or "01 Jan 1970" in refresh_clear
        )

        # The revoked refresh token must no longer work even if replayed.
        refresh_resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": original_refresh}
        )
        assert refresh_resp.status_code == 401
