"""Browser-visible throttling and verified rate-limit identities."""

import jwt
import pytest
import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.security import create_access_token
from app.middleware.rate_limit import _caller_id


def request_for(token):
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/auth/me",
            "headers": [(b"authorization", f"Bearer {token}".encode())],
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
        }
    )


def test_forged_subject_cannot_change_rate_limit_bucket():
    token = jwt.encode(
        {"sub": "attacker-chosen"},
        "untrusted-signing-key-that-is-long-enough",
        algorithm="HS256",
    )
    assert _caller_id(request_for(token)) == "ip:127.0.0.1"


def test_valid_local_access_token_gets_user_bucket():
    token, _ = create_access_token(sub="synthetic-user", email="test@example.com")
    assert _caller_id(request_for(token)) == "user:synthetic-user"


@pytest.mark.asyncio
async def test_rate_limit_response_has_cors_for_allowed_browser_origin(monkeypatch):
    import server

    async def throttled(request, call_next):
        return JSONResponse({"detail": "Too many requests"}, status_code=429)

    monkeypatch.setattr(server, "_rate_limit_middleware", throttled)
    origin = server.allow_origins[0]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server.app), base_url="http://test"
    ) as client:
        response = await client.get("/api/auth/me", headers={"Origin": origin})
        assert response.status_code == 429
        assert response.headers["access-control-allow-origin"] == origin
        denied = await client.get(
            "/api/auth/me", headers={"Origin": "https://unauthorized.example"}
        )
        assert "access-control-allow-origin" not in denied.headers


@pytest.mark.asyncio
async def test_widget_management_preflight_uses_strict_credentialed_cors():
    import server

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server.app), base_url="http://test"
    ) as client:
        headers = {
            "Origin": server.allow_origins[0],
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        }
        response = await client.options("/api/widgets?limit=100", headers=headers)
        assert response.status_code == 200
        assert response.headers["access-control-allow-credentials"] == "true"
        assert (
            response.headers["access-control-allow-origin"] == server.allow_origins[0]
        )
        headers["Origin"] = "https://unauthorized.example"
        denied = await client.options("/api/widgets", headers=headers)
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers


@pytest.mark.asyncio
async def test_public_widget_preflight_remains_cookie_free_for_customer_origins():
    import server

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=server.app), base_url="http://test"
    ) as client:
        response = await client.options(
            "/api/widget/session",
            headers={
                "Origin": "https://customer.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 204
        assert (
            response.headers["access-control-allow-origin"]
            == "https://customer.example"
        )
        assert "access-control-allow-credentials" not in response.headers
