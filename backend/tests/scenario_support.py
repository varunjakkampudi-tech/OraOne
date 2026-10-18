"""Shared helpers for the product scenario matrix (``test_scenarios_*.py``).

Nothing here touches a database or the network. Sessions are scripted fakes, routes run
through TestClient, and every external call is replaced by the test that needs it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.core.permissions import has_permission
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import authorization as authz

# Fixed identities. Two tenants so every isolation test has a foreign org to refuse.
ORG_A = uuid.UUID("aaaaaaaa-0000-4000-8000-00000000000a")
ORG_B = uuid.UUID("bbbbbbbb-0000-4000-8000-00000000000b")
PROJECT_A = uuid.UUID("aaaaaaaa-0000-4000-8000-0000000000a1")
USER = uuid.UUID("cccccccc-0000-4000-8000-00000000000c")

# A weekday afternoon in UTC: inside calling and messaging hours for any default zone.
DAYTIME = datetime(2026, 10, 19, 14, 0, tzinfo=timezone.utc)
# Late evening: outside calling and messaging hours (quiet hours are 21:00 to 08:00).
QUIET_HOURS = datetime(2026, 10, 19, 23, 30, tzinfo=timezone.utc)


class Rows:
    """Stand-in for a SQLAlchemy result. Supports ``all()``, ``scalars()`` and iteration."""

    def __init__(self, items=(), rowcount: int = 1) -> None:
        self._items = list(items)
        self.rowcount = rowcount

    def all(self) -> list:
        return list(self._items)

    def scalars(self) -> "Rows":
        return self

    def __iter__(self):
        return iter(self._items)


class FakeSession:
    """Scripted AsyncSession. ``scalars`` results are consumed in order and every statement
    is recorded so tests can assert on the SQL that would have run."""

    def __init__(self, scalars=(), scalar_value=None) -> None:
        self._scalars = list(scalars)
        self._scalar_value = scalar_value
        self.statements: list = []
        self.commits = 0
        self.added: list = []

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return self._scalar_value

    async def scalars(self, stmt):
        self.statements.append(stmt)
        return Rows(self._scalars.pop(0) if self._scalars else [])

    async def execute(self, stmt):
        self.statements.append(stmt)
        return Rows([])

    async def get(self, model, pk):
        return None

    def add(self, obj) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def refresh(self, obj) -> None:
        return None


def sql(stmt) -> str:
    """Compile a statement to Postgres SQL with literal values, for tenant-filter assertions."""
    return str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def record_permissions(monkeypatch, recorded: list) -> None:
    """Use the real RBAC matrix without subscription lookups. Records each permission checked."""

    async def authorize(session, ctx, *, permission=None, **_):
        recorded.append(permission)
        if permission and not has_permission(ctx.membership_role, permission):
            raise HTTPException(
                403, f"Role '{ctx.membership_role}' lacks {permission}."
            )
        return SimpleNamespace(raise_for_denied=lambda: None)

    monkeypatch.setattr(authz, "authorize", authorize)


def org_app(router, *, role: str, session, org_id: uuid.UUID = ORG_A) -> TestClient:
    """A FastAPI app with ``router`` mounted, acting as a member of ``org_id``."""

    async def _org():
        return OrgContext(
            user_id=USER,
            auth_subject="scenario-sub",
            organization_id=org_id,
            membership_role=role,
        )

    async def _project():
        return ProjectContext(
            user_id=USER,
            organization_id=org_id,
            membership_role=role,
            project_id=PROJECT_A,
            project_slug="default",
            is_default_project=True,
        )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_organization] = _org
    app.dependency_overrides[get_current_project] = _project
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app)


def channels_config(**overrides) -> SimpleNamespace:
    """A channels configuration with fake credentials. Nothing here is a real secret."""
    base = {
        "twilio_account_sid": "",
        "twilio_auth_token": "",
        "twilio_phone_number": "",
        "meta_whatsapp_access_token": "",
        "meta_whatsapp_app_secret": "",
        "meta_whatsapp_verify_token": "",
        "meta_instagram_access_token": "",
        "email_inbound_secret": "",
        "public_api_base_url": "",
        "voice_handoff_number": "",
        "voice_say_voice": "alice",
        "elevenlabs_api_key": "",
        "elevenlabs_voice_id": "",
        "elevenlabs_model_id": "eleven_flash_v2_5",
        "twilio_configured": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)
