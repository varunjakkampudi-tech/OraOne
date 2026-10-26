"""Hardening regressions for the authentication surface.

Covers: sign-in code lockout and send limits, refresh-token reuse detection
with family revocation, atomic rotation, idempotency scoping across
principals, identity degradation returning 503 instead of a synthetic
workspace, cookie-authenticated cross-origin refusal, the limiter fail-closed
policy for auth/AI tiers, trusted-proxy handling for logged IPs, and the
unset-ENVIRONMENT default.

Everything here runs against in-process cache backends, so no Postgres or
Redis is needed.
"""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request


@pytest.fixture
def otp_stores(monkeypatch):
    """Fresh code and guard stores for the auth service, in development mode."""
    from app.services import auth_service
    from app.services.cache import InProcessCacheBackend

    monkeypatch.setattr(auth_service.settings, "environment", "development")
    codes = InProcessCacheBackend()
    guard = InProcessCacheBackend()
    monkeypatch.setattr(auth_service, "_cache", lambda: codes)
    monkeypatch.setattr(auth_service, "get_shared_cache", lambda namespace: guard)
    return codes, guard


@pytest.fixture
def token_store(monkeypatch):
    from app.services import token_service
    from app.services.cache import InProcessCacheBackend

    store = InProcessCacheBackend()
    monkeypatch.setattr(token_service, "_cache", lambda: store)
    return store


# ── Sign-in code attempt cap ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_code_is_locked_after_five_failed_attempts(otp_stores):
    from app.schemas.auth import VerifyLoginOtpRequest
    from app.services import auth_service

    codes, _guard = otp_stores
    email = "lockout@example.com"
    codes.set(
        auth_service._code_key(email),
        {"digest": auth_service._digest(email, "123456")},
        ttl_seconds=600,
    )

    for _ in range(5):
        with pytest.raises(HTTPException) as exc:
            await auth_service.verify_email_code(
                None, VerifyLoginOtpRequest(email=email, code="000000")
            )
        assert exc.value.status_code == 400

    # The pending code is invalidated by the fifth failure.
    assert codes.get(auth_service._code_key(email)) is None

    # Even the correct code is refused once the window is locked.
    with pytest.raises(HTTPException) as exc:
        await auth_service.verify_email_code(
            None, VerifyLoginOtpRequest(email=email, code="123456")
        )
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_correct_code_within_attempt_budget_is_single_use(
    otp_stores, monkeypatch
):
    from app.schemas.auth import VerifyLoginOtpRequest
    from app.services import auth_service

    codes, _guard = otp_stores
    email = "budget@example.com"
    codes.set(
        auth_service._code_key(email),
        {"digest": auth_service._digest(email, "654321")},
        ttl_seconds=600,
    )

    class _Users:
        def __init__(self, session):
            pass

        async def get_by_email(self, _email):
            return None

    monkeypatch.setattr(auth_service, "UserRepository", _Users)

    # A wrong guess first, then the right one: still within the budget.
    with pytest.raises(HTTPException) as exc:
        await auth_service.verify_email_code(
            None, VerifyLoginOtpRequest(email=email, code="000000")
        )
    assert exc.value.status_code == 400

    # The correct code is accepted and consumed. A new address gets its account
    # now, at first verification, and the session is issued.
    class _Session:
        def add(self, obj):
            self.added = obj

        async def flush(self):
            return None

        async def commit(self):
            return None

    from app.core.config import settings

    tokens = await auth_service.verify_email_code(
        _Session(),
        VerifyLoginOtpRequest(
            email=email,
            code="654321",
            terms_accepted=True,
            privacy_accepted=True,
            terms_version=settings.legal_terms_version,
            privacy_version=settings.legal_privacy_version,
        ),
    )
    assert tokens.access_token
    assert codes.get(auth_service._code_key(email)) is None


# ── Per-email send limit ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_limit_caps_codes_per_email_and_hides_the_limit(
    otp_stores, monkeypatch, caplog
):
    from app.schemas.auth import EmailCodeRequest
    from app.services import auth_service, email_service

    codes, _guard = otp_stores
    sent: list[str] = []
    monkeypatch.setattr(
        email_service,
        "send_login_otp",
        lambda to, *, code, expires_in="10 minutes": sent.append(to) or True,
    )

    user = SimpleNamespace(
        auth_subject="sub-send-limit",
        status=SimpleNamespace(value="active"),
    )

    class _Users:
        def __init__(self, session):
            pass

        async def get_by_email(self, _email):
            return user

    monkeypatch.setattr(auth_service, "UserRepository", _Users)

    email = "sendlimit-person@example.com"
    session = SimpleNamespace(add=lambda obj: None, commit=_noop)
    caplog.set_level("INFO", logger="app.auth.service")
    for _ in range(7):
        # The resend cooldown is tested separately; clear it so this test reaches the send limit.
        auth_service._guard_cache().delete(auth_service._cooldown_key(email))
        # Every call returns None, so the limit is not visible to the caller.
        result = await auth_service.request_email_code(
            session, EmailCodeRequest(email=email)
        )
        assert result is None

    assert len(sent) == auth_service.MAX_CODE_SENDS
    assert auth_service._code_key(email) in codes._store
    # Logs carry a redacted address, never the address itself.
    assert "email_code_send_limited" in caplog.text
    assert email not in caplog.text


async def _noop():
    return None


# ── Refresh-token reuse and atomic rotation ───────────────────────────────


def test_refresh_reuse_revokes_the_whole_family(token_store):
    from app.services import token_service

    first = token_service.issue_token_pair(user_id="user-reuse", email="r@example.com")
    second = token_service.rotate(first.refresh_token)

    # Presenting the already-rotated token is reuse: the family is revoked.
    with pytest.raises(ValueError):
        token_service.rotate(first.refresh_token)

    # The legitimate successor, which was never presented twice, is now dead too.
    with pytest.raises(ValueError):
        token_service.rotate(second.refresh_token)


def test_concurrent_rotation_has_exactly_one_winner(token_store):
    from app.services import token_service

    pair = token_service.issue_token_pair(user_id="user-race", email="race@example.com")
    barrier = threading.Barrier(16)
    outcomes: list[bool] = []
    lock = threading.Lock()

    def _attempt():
        barrier.wait()
        try:
            token_service.rotate(pair.refresh_token)
            ok = True
        except ValueError:
            ok = False
        with lock:
            outcomes.append(ok)

    threads = [threading.Thread(target=_attempt) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 15


# ── Idempotency scoping ───────────────────────────────────────────────────


class _StreamedResponse:
    def __init__(self, status_code: int, content: dict):
        import json as _json

        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.media_type = "application/json"
        self._body = _json.dumps(content).encode()

    @property
    async def body_iterator(self):
        yield self._body


def _post(path: str, *, idem_key: str, authorization: str | None = None) -> Request:
    headers = [(b"idempotency-key", idem_key.encode())]
    if authorization:
        headers.append((b"authorization", authorization.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": headers,
            "query_string": b"",
            "client": ("203.0.113.9", 0),
        }
    )


@pytest.mark.asyncio
async def test_idempotency_never_replays_across_principals(monkeypatch):
    from app.core.security import create_access_token
    from app.middleware import idempotency as idem
    from app.services.cache import InProcessCacheBackend

    shared = InProcessCacheBackend()
    monkeypatch.setattr(idem, "_cache", lambda: shared)

    token_a, _ = create_access_token(sub="user-a", email="a@example.com")
    token_b, _ = create_access_token(sub="user-b", email="b@example.com")
    executions: list[str] = []

    def _call_for(owner: str):
        async def _call_next(request):
            executions.append(owner)
            return _StreamedResponse(201, {"owner": owner, "n": len(executions)})

        return _call_next

    same_key = "shared-idem-key"
    path = "/api/agents"

    first = await idem.idempotency_middleware(
        _post(path, idem_key=same_key, authorization=f"Bearer {token_a}"),
        _call_for("a"),
    )
    other = await idem.idempotency_middleware(
        _post(path, idem_key=same_key, authorization=f"Bearer {token_b}"),
        _call_for("b"),
    )
    # User B's own request must run and must not receive A's response.
    assert executions == ["a", "b"]
    assert b'"owner": "b"' in bytes(other.body)
    assert first.status_code == other.status_code == 201

    # The same principal still gets the replay, which is the retry case.
    replay = await idem.idempotency_middleware(
        _post(path, idem_key=same_key, authorization=f"Bearer {token_a}"),
        _call_for("a-again"),
    )
    assert executions == ["a", "b"]
    assert replay.headers.get("Idempotency-Replayed") == "true"


@pytest.mark.asyncio
async def test_idempotency_does_not_cache_auth_responses(monkeypatch):
    from app.middleware import idempotency as idem
    from app.services.cache import InProcessCacheBackend

    shared = InProcessCacheBackend()
    monkeypatch.setattr(idem, "_cache", lambda: shared)
    executions = 0

    async def _call_next(request):
        nonlocal executions
        executions += 1
        return _StreamedResponse(200, {"access_token": f"t{executions}"})

    await idem.idempotency_middleware(
        _post("/api/auth/refresh", idem_key="auth-key"), _call_next
    )
    await idem.idempotency_middleware(
        _post("/api/auth/refresh", idem_key="auth-key"), _call_next
    )
    assert executions == 2
    assert shared._store == {}


# ── Identity degradation ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_identity_db_failure_returns_503_not_a_synthetic_workspace(monkeypatch):
    from app.api.auth import routes

    class _BrokenIdentity:
        def __init__(self, session):
            pass

        async def upsert_identity(self, **kwargs):
            raise RuntimeError("database unreachable")

    class _Session:
        async def rollback(self):
            return None

        async def commit(self):
            return None

    monkeypatch.setattr(routes, "IdentityService", _BrokenIdentity)

    with pytest.raises(HTTPException) as exc:
        await routes.identity(
            claims={"sub": "sub-identity", "email": "id@example.com", "name": "Id"},
            session=_Session(),
        )
    assert exc.value.status_code == 503
    assert "workspace" in str(exc.value.detail).lower()
    assert "Workspace's" not in str(exc.value.detail)


# ── Cookie-authenticated cross-origin refusal ─────────────────────────────


def test_cookie_origin_guard_rules():
    from app.core.cookies import cookie_origin_refused

    allowed = ["https://app.example.com"]
    cookies = {"oraone_refresh_token": "opaque"}

    def refused(method, headers, cookie_map=cookies):
        return cookie_origin_refused(
            method=method, headers=headers, cookies=cookie_map, allowed_origins=allowed
        )

    # Foreign origin on a cookie-authenticated unsafe request: refused.
    assert refused("POST", {"origin": "https://evil.example"})
    assert refused("DELETE", {"origin": "null"})
    # Allow-listed origin, safe methods, no Origin, or bearer auth: not refused.
    assert not refused("POST", {"origin": "https://app.example.com"})
    assert not refused("GET", {"origin": "https://evil.example"})
    assert not refused("POST", {})
    assert not refused(
        "POST",
        {"origin": "https://evil.example", "authorization": "Bearer abc"},
    )
    assert not refused("POST", {"origin": "https://evil.example"}, cookie_map={})


@pytest.mark.asyncio
async def test_unsafe_cookie_request_with_foreign_origin_is_refused():
    from httpx import ASGITransport, AsyncClient

    from server import allow_origins, app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        refused = await client.post(
            "/api/auth/logout",
            headers={
                "Origin": "https://evil.example",
                "Cookie": "oraone_refresh_token=not-a-real-token",
            },
        )
        assert refused.status_code == 403, refused.text

        allowed = await client.post(
            "/api/auth/logout",
            headers={
                "Origin": allow_origins[0],
                "Cookie": "oraone_refresh_token=not-a-real-token",
            },
        )
        assert allowed.status_code == 200, allowed.text


# ── Limiter failure policy ────────────────────────────────────────────────


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "query_string": b"",
            "client": ("203.0.113.20", 0),
        }
    )


async def _ok(request):
    return SimpleNamespace(status_code=200)


class _BrokenStore:
    def increment(self, key, ttl_seconds=None):
        raise ConnectionError("redis unreachable")


@pytest.mark.asyncio
async def test_limiter_fails_closed_for_auth_and_ai_tiers(monkeypatch):
    from app.middleware import rate_limit

    monkeypatch.setattr(rate_limit, "_cache", lambda: _BrokenStore())

    auth = await rate_limit.rate_limit_middleware(_request("/api/auth/refresh"), _ok)
    assert auth.status_code == 503

    ai = await rate_limit.rate_limit_middleware(_request("/api/rag/query"), _ok)
    assert ai.status_code == 503


@pytest.mark.asyncio
async def test_limiter_stays_fail_open_for_best_effort_tiers(monkeypatch):
    from app.middleware import rate_limit

    monkeypatch.setattr(rate_limit, "_cache", lambda: _BrokenStore())
    response = await rate_limit.rate_limit_middleware(_request("/api/agents"), _ok)
    assert response.status_code == 200


# ── Trusted proxy for logged IPs ──────────────────────────────────────────


def test_forwarded_for_is_ignored_from_untrusted_peer(monkeypatch):
    from app.middleware import rate_limit

    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/health",
            "headers": [(b"x-forwarded-for", b"198.51.100.7")],
            "query_string": b"",
            "client": ("203.0.113.50", 0),
        }
    )
    assert rate_limit._client_ip(request) == "203.0.113.50"

    monkeypatch.setenv("TRUSTED_PROXY_IPS", "203.0.113.0/24")
    assert rate_limit._client_ip(request) == "198.51.100.7"


# ── Environment default and dev-login gating ──────────────────────────────


def test_unset_environment_is_treated_as_production(monkeypatch):
    from app.core import cookies

    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert cookies._is_production() is True
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert cookies._is_production() is False


def test_dev_login_stays_off_when_environment_is_unset(monkeypatch):
    from app.services import auth_service

    monkeypatch.setenv("ALLOW_DEV_PASSWORD_LOGIN", "true")
    monkeypatch.setattr(auth_service.settings, "environment", "production")
    assert auth_service._dev_password_login_allowed() is False
    monkeypatch.setattr(auth_service.settings, "environment", "development")
    assert auth_service._dev_password_login_allowed() is True


@pytest.mark.asyncio
async def test_undelivered_code_is_not_issued_and_reports_failure(
    otp_stores, monkeypatch
):
    """A send that fails must not leave a usable code behind or report success."""
    from app.schemas.auth import EmailCodeRequest
    from app.services import auth_service, email_service

    codes, _guard = otp_stores
    monkeypatch.setattr(
        email_service,
        "send_login_otp",
        lambda to, *, code, expires_in="10 minutes": False,
    )
    user = SimpleNamespace(
        auth_subject="sub-undelivered",
        status=SimpleNamespace(value="active"),
    )

    class _Users:
        def __init__(self, _session):
            pass

        async def get_by_email(self, _email):
            return user

    monkeypatch.setattr(auth_service, "UserRepository", _Users)
    session = SimpleNamespace(add=lambda obj: None, commit=None)

    with pytest.raises(auth_service.EmailDeliveryError):
        await auth_service.request_email_code(
            session, EmailCodeRequest(email="undelivered@example.com")
        )
    assert auth_service._code_key("undelivered@example.com") not in codes._store
