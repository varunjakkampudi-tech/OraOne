"""Every Super Admin route refuses an ordinary signed-in user.

The sweep finds every route under the platform-admin prefixes, calls each one with a
valid token for an ordinary (non-admin) user, and requires HTTP 403. The real
platform-admin dependency runs; only the token claims and the user lookup are
supplied by the test. A new admin route that forgets its guard fails this test.
"""

from __future__ import annotations

import re
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

ADMIN_PREFIXES = ("/api/super-admin", "/api/admin")
MIN_ROUTES_EXPECTED = 15  # guards against an empty sweep passing silently
_PATH_PARAM = re.compile(r"\{[^}]+\}")


class _OrdinaryUserSession:
    """Answers the one lookup the platform-admin check makes: a plain user."""

    async def scalar(self, _stmt):
        return SimpleNamespace(
            id=uuid.uuid4(),
            email="ordinary@example.test",
            full_name="Ordinary User",
            role=_user_role("user"),
            status=SimpleNamespace(value="active"),
        )

    async def execute(self, _stmt):
        raise AssertionError("an ordinary user must be refused before any query runs")


def _user_role(value: str):
    from app.database.models.user import UserRole

    return UserRole(value)


def _admin_routes(app):
    """Every method and path under the admin prefixes, read from the OpenAPI document.

    The OpenAPI document lists routers that are included through nested routers,
    which the app's flat route list does not expose in this FastAPI version.
    """
    found = []
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith(ADMIN_PREFIXES):
            continue
        for method in operations:
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                found.append((method.upper(), path))
    return sorted(set(found))


@pytest.fixture
def ordinary_user_client(monkeypatch):
    import server
    from app.database.session import get_db
    from app.middleware.jwt_auth import get_current_user_claims

    app = server.app
    app.dependency_overrides[get_current_user_claims] = lambda: {
        "sub": "ordinary-user-subject",
        "role": "user",
    }

    async def _db():
        yield _OrdinaryUserSession()

    app.dependency_overrides[get_db] = _db
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.pop(get_current_user_claims, None)
        app.dependency_overrides.pop(get_db, None)


def test_every_admin_route_refuses_an_ordinary_user(ordinary_user_client):
    import server

    routes = _admin_routes(server.app)
    assert len(routes) >= MIN_ROUTES_EXPECTED, (
        f"sweep found only {len(routes)} admin routes"
    )

    unguarded = []
    for method, path in routes:
        url = _PATH_PARAM.sub(lambda _m: str(uuid.uuid4()), path)
        body = {} if method in {"POST", "PUT", "PATCH", "DELETE"} else None
        response = ordinary_user_client.request(method, url, json=body)
        if response.status_code != 403:
            unguarded.append((method, path, response.status_code))

    assert unguarded == [], (
        f"admin routes that did not refuse an ordinary user: {unguarded}"
    )
