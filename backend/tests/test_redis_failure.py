"""Redis-failure semantics — verifies the fail-closed / fail-safe policies
documented in app/middleware/idempotency.py and app/services/token_service.py.

Per-primitive policy under a Redis/cache outage:
    Idempotency        -> fail CLOSED (503, reject the mutation) — never
                           silently lose dedup protection on a paid/mutating action.
    Login / refresh    -> fail SAFELY (503, clear retryable error) — never a
                           raw unhandled 500.
    Rate limiter        -> fail OPEN (best-effort, request proceeds) — see
                           app/middleware/rate_limit.py's own try/except.

No DB or real Redis required — the cache backend is monkeypatched to raise,
simulating an outage.
"""
from __future__ import annotations

import pytest

from app.middleware.idempotency import idempotency_middleware
from app.schemas.auth import LoginRequest, RefreshTokenRequest


class _BrokenCache:
    """Stands in for a cache backend whose Redis connection is down."""

    def get(self, key):
        raise ConnectionError("redis unreachable")

    def set(self, key, value, ttl_seconds=None):
        raise ConnectionError("redis unreachable")

    def delete(self, key):
        raise ConnectionError("redis unreachable")

    def set_if_not_exists(self, key, value, ttl_seconds=None):
        raise ConnectionError("redis unreachable")


def _fake_request(*, method="POST", path="/api/agents", idem_key="key-123"):
    from starlette.requests import Request

    headers = [(b"authorization", b"Bearer faketoken")]
    if idem_key:
        headers.append((b"idempotency-key", idem_key.encode()))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "query_string": b"",
        "client": ("127.0.0.1", 0),
    }
    return Request(scope)


async def _call_next_ok(request):
    from starlette.responses import JSONResponse

    return JSONResponse(status_code=201, content={"id": "abc123"})


@pytest.mark.asyncio
async def test_idempotency_fails_closed_when_cache_unreachable(monkeypatch):
    """A Redis outage must reject the mutation (503), not silently execute
    it unprotected — the caller explicitly asked for dedup protection."""
    from app.middleware import idempotency as idem_module

    monkeypatch.setattr(idem_module, "_cache", lambda: _BrokenCache())

    request = _fake_request()
    response = await idempotency_middleware(request, _call_next_ok)

    assert response.status_code == 503
    import json
    body = json.loads(bytes(response.body))
    assert body["error"]["code"] == "IDEMPOTENCY_UNAVAILABLE"


@pytest.mark.asyncio
async def test_idempotency_without_key_bypasses_cache_entirely(monkeypatch):
    """Requests without the header never touch the cache — even a fully
    broken backend must not affect ordinary (non-idempotent) requests."""
    from app.middleware import idempotency as idem_module

    monkeypatch.setattr(idem_module, "_cache", lambda: _BrokenCache())

    request = _fake_request(idem_key=None)
    response = await idempotency_middleware(request, _call_next_ok)

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_login_fails_safely_when_token_store_unreachable(monkeypatch):
    """A broken refresh-token store must surface as a clear 503, never a
    raw unhandled exception/500. Token issuance happens in verify_login_otp()
    (see app/services/auth_service.py) — login() itself only emails an OTP."""
    from fastapi import HTTPException

    from app.schemas.auth import VerifyLoginOtpRequest
    from app.services import auth_service, token_service

    class _FakeUser:
        cognito_sub = "sub-1"
        email = "a@b.com"
        full_name = "A B"
        password_hash = "irrelevant"

        class status:
            value = "active"

        is_email_verified = True
        last_login_at = None

    class _FakeUsers:
        async def get_by_email(self, email):
            return _FakeUser()

    class _FakeSession:
        async def commit(self):
            return None

    class _FakeOtpCache:
        def get(self, key):
            return "123456"

        def delete(self, key):
            return None

    monkeypatch.setattr(auth_service, "UserRepository", lambda session: _FakeUsers())
    monkeypatch.setattr(auth_service, "verify_password", lambda plain, hashed: True)
    monkeypatch.setattr(auth_service, "_cache", lambda: _FakeOtpCache())

    def _broken_issue(**kwargs):
        raise ConnectionError("redis unreachable")

    monkeypatch.setattr(token_service, "issue_token_pair", _broken_issue)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.verify_login_otp(_FakeSession(), VerifyLoginOtpRequest(email="a@b.com", code="123456"))
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_refresh_fails_safely_when_token_store_unreachable(monkeypatch):
    from fastapi import HTTPException

    from app.services import auth_service, token_service

    def _broken_rotate(refresh_token):
        raise ConnectionError("redis unreachable")

    monkeypatch.setattr(token_service, "rotate", _broken_rotate)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_tokens(RefreshTokenRequest(refresh_token="abc"))
    assert exc_info.value.status_code == 503
