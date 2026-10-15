"""Rate-limit cache outage behavior and verified caller identity boundaries."""

import json

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.cookies import ACCESS_COOKIE_NAME
from app.core.security import create_access_token
from app.middleware import rate_limit


def _request(path="/api/agents", headers=None):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "scheme": "http",
            "headers": headers or [],
            "client": ("127.0.0.1", 1234),
        }
    )


async def _ok(_request):
    return JSONResponse({"ok": True}, status_code=200)


class _Unavailable:
    def increment(self, key, ttl_seconds=None):
        raise ConnectionError("redis unavailable")


@pytest.mark.asyncio
async def test_production_rate_limiter_fails_closed(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(rate_limit, "_cache", lambda: _Unavailable())
    response = await rate_limit.rate_limit_middleware(_request(), _ok)
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert json.loads(response.body)["error"]["code"] == "RATE_LIMIT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_local_development_rate_limiter_remains_best_effort(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setattr(rate_limit, "_cache", lambda: _Unavailable())
    response = await rate_limit.rate_limit_middleware(_request(), _ok)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_endpoints_remain_ip_scoped_even_with_signed_bearer(monkeypatch):
    seen = []

    class _Cache:
        def increment(self, key, ttl_seconds=None):
            seen.append(key)
            return 1

    monkeypatch.setattr(rate_limit, "_cache", lambda: _Cache())
    token, _ = create_access_token(sub="trusted-user", email="person@example.com")
    response = await rate_limit.rate_limit_middleware(
        _request(
            path="/api/auth/login",
            headers=[(b"authorization", f"Bearer {token}".encode())],
        ),
        _ok,
    )
    assert response.status_code == 200
    assert seen and ":ip:127.0.0.1:" in seen[0]


@pytest.mark.asyncio
async def test_verified_cookie_gets_user_bucket(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "auth_provider", "self_hosted")
    token, _ = create_access_token(sub="signed-cookie-user", email="person@example.com")
    request = _request(headers=[(b"cookie", f"{ACCESS_COOKIE_NAME}={token}".encode())])
    assert await rate_limit._verified_caller_id(request) == "user:signed-cookie-user"


@pytest.mark.asyncio
async def test_forged_cookie_stays_on_ip_bucket(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "auth_provider", "self_hosted")
    request = _request(headers=[(b"cookie", f"{ACCESS_COOKIE_NAME}=forged".encode())])
    assert await rate_limit._verified_caller_id(request) == "ip:127.0.0.1"


@pytest.mark.asyncio
async def test_cognito_subject_requires_verified_token(monkeypatch):
    from app.core.config import settings
    from app.middleware import jwt_auth

    monkeypatch.setattr(settings, "auth_provider", "cognito")

    async def verified(token, request=None):
        assert token == "signed-cognito"
        return {"sub": "verified-cognito-user"}

    monkeypatch.setattr(jwt_auth, "verify_cognito_access_token", verified)
    request = _request(headers=[(b"authorization", b"Bearer signed-cognito")])
    assert await rate_limit._verified_caller_id(request) == "user:verified-cognito-user"
