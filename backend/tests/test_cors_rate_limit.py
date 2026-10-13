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
