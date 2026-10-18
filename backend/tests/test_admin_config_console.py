"""Admin configuration console: access, masking, guarded writes, audit, isolation.

No test touches a real database or real provider. The store helpers in
``app.services.config_console`` are replaced with an in-memory store, and the
audit calls are captured.
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient

from app.core import config_overrides, crypto
from app.core.config_registry import BY_NAME, mask_secret
from app.database.models.admin_config_draft import AdminConfigDraft
from app.database.models.admin_config_override import AdminConfigOverride
from app.database.models.admin_config_publish_event import AdminConfigPublishEvent
from app.middleware.platform_context import (
    PlatformContext,
    get_current_platform_context,
)
from app.api.admin_config import routes as admin_config_routes
from app.services import config_console
from app.database.session import get_db
from app.database.models.user import UserRole

SECRET_VALUE = "sk-or-live-THE-FULL-SECRET-9876"
AUDIT_SECRET_VALUE = "sk-or-audit-SECRET-5555"
REASON = "Rotating the key after a planned review"


class _Store:
    """In-memory replacement for the active, draft and publish-event tables."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], AdminConfigOverride] = {}
        self.drafts: dict[tuple[str, str], AdminConfigDraft] = {}
        self.events: list[AdminConfigPublishEvent] = []

    async def fetch(self, session, environment):
        return [row for (env, _), row in self.rows.items() if env == environment]

    async def upsert(
        self, session, *, existing, environment, name, value_encrypted, actor_id, now
    ):
        if existing is None:
            self.rows[(environment, name)] = AdminConfigOverride(
                environment=environment,
                name=name,
                value_encrypted=value_encrypted,
                updated_at=now,
            )
        else:
            existing.value_encrypted = value_encrypted
            existing.updated_at = now

    async def delete(self, session, *, environment, name):
        self.rows.pop((environment, name), None)

    async def fetch_drafts(self, session, environment):
        return [d for (env, _), d in self.drafts.items() if env == environment]

    async def upsert_draft(
        self,
        session,
        *,
        existing,
        environment,
        name,
        action,
        value_encrypted,
        actor_id,
        now,
    ):
        if existing is None:
            self.drafts[(environment, name)] = AdminConfigDraft(
                environment=environment,
                name=name,
                action=action,
                value_encrypted=value_encrypted,
                updated_at=now,
            )
        else:
            existing.action = action
            existing.value_encrypted = value_encrypted
            existing.updated_at = now

    async def delete_draft(self, session, *, environment, name):
        self.drafts.pop((environment, name), None)

    async def delete_drafts(self, session, *, environment):
        for key in [k for k in self.drafts if k[0] == environment]:
            del self.drafts[key]

    async def fetch_events(self, session, environment, limit):
        matching = sorted(
            (e for e in self.events if e.environment == environment),
            key=lambda e: e.published_at,
            reverse=True,
        )
        return matching[:limit]

    def add_event(self, session, event):
        if event.id is None:
            event.id = uuid.uuid4()
        self.events.append(event)


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


@pytest.fixture
def store(monkeypatch):
    fake = _Store()
    monkeypatch.setattr(config_console, "_fetch_rows", fake.fetch)
    monkeypatch.setattr(config_console, "_upsert_row", fake.upsert)
    monkeypatch.setattr(config_console, "_delete_row", fake.delete)
    monkeypatch.setattr(config_console, "_fetch_drafts", fake.fetch_drafts)
    monkeypatch.setattr(config_console, "_upsert_draft", fake.upsert_draft)
    monkeypatch.setattr(config_console, "_delete_draft", fake.delete_draft)
    monkeypatch.setattr(config_console, "_delete_drafts", fake.delete_drafts)
    monkeypatch.setattr(config_console, "_fetch_publish_events", fake.fetch_events)
    monkeypatch.setattr(config_console, "_add_publish_event", fake.add_event)
    return fake


@pytest.fixture
def audit_calls(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def _capture(action, **kwargs):
        calls.append((action, kwargs))

    async def _noop_flush(session):
        return 0

    monkeypatch.setattr(config_console, "audit", _capture)
    monkeypatch.setattr(config_console, "flush_pending", _noop_flush)
    monkeypatch.setattr(admin_config_routes, "flush_pending", _noop_flush)
    return calls


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("INTEGRATIONS_ENCRYPTION_KEY", Fernet.generate_key().decode())
    crypto._fernet.cache_clear()
    monkeypatch.setenv("OPENROUTER_API_KEY", SECRET_VALUE)
    yield
    crypto._fernet.cache_clear()


def _platform_context(role: UserRole) -> PlatformContext:
    user = SimpleNamespace(
        id="00000000-0000-4000-8000-000000000001", email="admin@example.com"
    )
    return PlatformContext(user=user, auth_subject="sub-admin", role=role)


@pytest.fixture
def client_factory(store, audit_calls):
    from server import app

    session = _FakeSession()

    async def _db():
        yield session

    def _make(role: UserRole) -> AsyncClient:
        async def _ctx() -> PlatformContext:
            return _platform_context(role)

        app.dependency_overrides[get_current_platform_context] = _ctx
        app.dependency_overrides[get_db] = _db
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield _make
    app.dependency_overrides.pop(get_current_platform_context, None)
    app.dependency_overrides.pop(get_db, None)


def _write_body(**overrides):
    body = {
        "environment": "local",
        "value": "DEBUG",
        "confirm": "LOG_LEVEL",
        "reason": REASON,
    }
    body.update(overrides)
    return body


# --------------------------------------------------------------------------- #
# Masking and registry                                                        #
# --------------------------------------------------------------------------- #
def test_mask_secret_shows_at_most_four_characters_and_never_short_values():
    assert mask_secret("sk-or-live-THE-FULL-SECRET-9876") == "9876"
    assert mask_secret("short") is None
    assert mask_secret("") is None
    assert mask_secret(None) is None


def test_registry_has_unique_names_and_secret_plain_split():
    assert BY_NAME["OPENROUTER_API_KEY"].kind == "secret"
    assert BY_NAME["LOG_LEVEL"].kind == "plain"
    assert BY_NAME["DATABASE_URL"].console_managed is False
    assert BY_NAME["JWT_SECRET_KEY"].console_managed is False


# --------------------------------------------------------------------------- #
# Access control                                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.admin, UserRole.manager, UserRole.user])
async def test_non_super_admin_gets_403_on_read_write_and_reload(
    client_factory, store, audit_calls, role
):
    client = client_factory(role)
    async with client as c:
        read = await c.get("/api/admin/config?environment=local")
        write = await c.put("/api/admin/config/LOG_LEVEL", json=_write_body())
        reload = await c.post(
            "/api/admin/config/reload", json={"confirm": "RELOAD", "reason": REASON}
        )
    assert read.status_code == 403
    assert write.status_code == 403
    assert reload.status_code == 403
    assert store.rows == {}
    assert audit_calls == []


@pytest.mark.asyncio
async def test_super_admin_can_read(client_factory, store, audit_calls):
    async with client_factory(UserRole.super_admin) as c:
        r = await c.get("/api/admin/config?environment=local")
    assert r.status_code == 200
    names = {item["name"] for item in r.json()["items"]}
    assert "OPENROUTER_API_KEY" in names


# --------------------------------------------------------------------------- #
# Secrets never returned in full                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_secrets_are_never_returned_in_full(client_factory, store, audit_calls):
    async with client_factory(UserRole.super_admin) as c:
        local = await c.get("/api/admin/config?environment=local")
        production = await c.get("/api/admin/config?environment=production")
    assert SECRET_VALUE not in local.text
    assert SECRET_VALUE not in production.text
    item = next(i for i in local.json()["items"] if i["name"] == "OPENROUTER_API_KEY")
    assert item["is_set"] is True
    assert item["value"] is None
    assert item["masked_tail"] == "9876"
    assert len(item["masked_tail"]) <= 4


@pytest.mark.asyncio
async def test_production_never_returns_plain_values(
    client_factory, store, audit_calls, monkeypatch
):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    async with client_factory(UserRole.super_admin) as c:
        r = await c.get("/api/admin/config?environment=production")
    assert r.status_code == 200
    assert "WARNING" not in r.text
    for item in r.json()["items"]:
        assert item["value"] is None


# --------------------------------------------------------------------------- #
# Writes: confirm, reason, audit                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_write_requires_exact_confirm_and_reason(
    client_factory, store, audit_calls
):
    async with client_factory(UserRole.super_admin) as c:
        missing_confirm = await c.put(
            "/api/admin/config/LOG_LEVEL", json=_write_body(confirm=None)
        )
        wrong_confirm = await c.put(
            "/api/admin/config/LOG_LEVEL", json=_write_body(confirm="log_level")
        )
        missing_reason = await c.put(
            "/api/admin/config/LOG_LEVEL", json=_write_body(reason=None)
        )
        short_reason = await c.put(
            "/api/admin/config/LOG_LEVEL", json=_write_body(reason="fix")
        )
    assert missing_confirm.status_code == 400
    assert wrong_confirm.status_code == 400
    assert missing_reason.status_code == 400
    assert short_reason.status_code == 400
    assert store.rows == {}
    rejected = [
        kw["meta"]["reason_code"]
        for action, kw in audit_calls
        if action == "config_write_rejected"
    ]
    assert rejected == [
        "confirm_mismatch",
        "confirm_mismatch",
        "reason_length",
        "reason_length",
    ]


@pytest.mark.asyncio
async def test_successful_write_is_audited_without_secret_value(
    client_factory, store, audit_calls
):
    async with client_factory(UserRole.super_admin) as c:
        r = await c.put(
            "/api/admin/config/OPENROUTER_API_KEY",
            json=_write_body(value=AUDIT_SECRET_VALUE, confirm="OPENROUTER_API_KEY"),
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "draft_saved"
    assert body["active"] is False
    assert body["restart_required"] is False
    assert AUDIT_SECRET_VALUE not in r.text

    drafts = [kw for action, kw in audit_calls if action == "draft_save"]
    assert len(drafts) == 1
    audit_kwargs = drafts[0]
    assert audit_kwargs["user_id"] == "00000000-0000-4000-8000-000000000001"
    assert audit_kwargs["meta"]["admin_email"] == "admin@example.com"
    assert audit_kwargs["meta"]["key"] == "OPENROUTER_API_KEY"
    assert audit_kwargs["meta"]["reason"] == REASON
    assert audit_kwargs["meta"]["change"] == "set"
    assert AUDIT_SECRET_VALUE not in json.dumps(audit_calls, default=str)
    # The draft is stored encrypted, never as plaintext, and the active store is untouched.
    stored = store.drafts[("local", "OPENROUTER_API_KEY")]
    assert AUDIT_SECRET_VALUE not in stored.value_encrypted
    assert store.rows == {}


@pytest.mark.asyncio
async def test_clear_draft_takes_effect_only_after_publish(
    client_factory, store, audit_calls
):
    store.rows[("local", "LOG_LEVEL")] = AdminConfigOverride(
        environment="local",
        name="LOG_LEVEL",
        value_encrypted=crypto.encrypt("INFO"),
    )
    async with client_factory(UserRole.super_admin) as c:
        r = await c.put("/api/admin/config/LOG_LEVEL", json=_write_body(value=None))
        published = await c.post(
            "/api/admin/config/publish",
            json={
                "environment": "local",
                "confirm": "local",
                "reason": REASON,
                "reviewed": ["LOG_LEVEL"],
            },
        )
    assert r.status_code == 200
    assert r.json()["status"] == "draft_removal_saved"
    assert published.status_code == 200, published.text
    assert ("local", "LOG_LEVEL") not in store.rows
    assert store.drafts == {}


@pytest.mark.asyncio
async def test_unknown_and_unmanaged_keys_are_refused(
    client_factory, store, audit_calls
):
    async with client_factory(UserRole.super_admin) as c:
        unknown = await c.put(
            "/api/admin/config/NOT_A_REAL_KEY",
            json=_write_body(confirm="NOT_A_REAL_KEY"),
        )
        unmanaged = await c.put(
            "/api/admin/config/DATABASE_URL",
            json=_write_body(value="postgresql://x", confirm="DATABASE_URL"),
        )
    assert unknown.status_code == 404
    assert unmanaged.status_code == 400
    assert store.rows == {}


# --------------------------------------------------------------------------- #
# Cross-environment isolation                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_environments_are_isolated(client_factory, store, audit_calls):
    async with client_factory(UserRole.super_admin) as c:
        await c.put(
            "/api/admin/config/OPENROUTER_API_KEY",
            json=_write_body(
                environment="production",
                value="sk-prod-PRODUCTION-KEY-0001",
                confirm="OPENROUTER_API_KEY",
            ),
        )
        published = await c.post(
            "/api/admin/config/publish",
            json={
                "environment": "production",
                "confirm": "production",
                "reason": REASON,
                "reviewed": ["OPENROUTER_API_KEY"],
            },
        )
        assert published.status_code == 200, published.text
        local_view = await c.get("/api/admin/config?environment=local")
        prod_view = await c.get("/api/admin/config?environment=production")

    assert "sk-prod-PRODUCTION-KEY-0001" not in local_view.text
    assert "sk-prod-PRODUCTION-KEY-0001" not in prod_view.text

    local_item = next(
        i for i in local_view.json()["items"] if i["name"] == "OPENROUTER_API_KEY"
    )
    prod_item = next(
        i for i in prod_view.json()["items"] if i["name"] == "OPENROUTER_API_KEY"
    )
    # Local still reports this process's own value, not the production row.
    assert local_item["source"] == "deployment"
    assert local_item["masked_tail"] == "9876"
    assert prod_item["source"] == "console"
    assert prod_item["masked_tail"] == "0001"
    assert prod_view.json()["deployment_visible"] is False


@pytest.mark.asyncio
async def test_production_rows_are_not_read_by_local_process(store, monkeypatch):
    """The startup loader asks the database only for this process's environment."""
    captured: dict[str, object] = {}

    class _Cursor:
        def execute(self, sql, params):
            captured["params"] = params

        def fetchall(self):
            return []

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class _Conn:
        def cursor(self):
            return _Cursor()

        def close(self):
            return None

    import psycopg2

    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: _Conn())
    values = config_overrides.read_stored_overrides(
        "postgresql+asyncpg://u:p@h/db", "local"
    )
    assert captured["params"] == ("local",)
    assert values == {}


def test_applied_overrides_revert_to_baseline_when_removed(monkeypatch):
    monkeypatch.setattr(config_overrides, "_BASELINE", {})
    monkeypatch.setattr(config_overrides, "_APPLIED", set())
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    assert config_overrides.apply_overrides({"LOG_LEVEL": "DEBUG"}) == ["LOG_LEVEL"]
    assert config_overrides.os.environ["LOG_LEVEL"] == "DEBUG"

    # A key that is no longer stored returns to the value the environment had.
    assert config_overrides.apply_overrides({}) == ["LOG_LEVEL"]
    assert config_overrides.os.environ["LOG_LEVEL"] == "WARNING"


def test_apply_ignores_keys_that_are_not_console_managed(monkeypatch):
    monkeypatch.setattr(config_overrides, "_BASELINE", {})
    monkeypatch.setattr(config_overrides, "_APPLIED", set())
    monkeypatch.setenv("DATABASE_URL", "postgresql://original")
    assert config_overrides.apply_overrides({"DATABASE_URL": "postgresql://evil"}) == []
    assert config_overrides.os.environ["DATABASE_URL"] == "postgresql://original"


@pytest.mark.asyncio
async def test_reload_requires_confirm_and_reason_and_is_audited(
    client_factory, store, audit_calls, monkeypatch
):
    async def _fake_reload():
        return ["LOG_LEVEL"]

    monkeypatch.setattr(config_overrides, "reload_stored_overrides", _fake_reload)
    async with client_factory(UserRole.super_admin) as c:
        refused = await c.post(
            "/api/admin/config/reload", json={"confirm": "yes", "reason": REASON}
        )
        accepted = await c.post(
            "/api/admin/config/reload", json={"confirm": "RELOAD", "reason": REASON}
        )
    assert refused.status_code == 400
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "reloaded"
    assert accepted.json()["changed_keys"] == ["LOG_LEVEL"]
    actions = [action for action, _ in audit_calls]
    assert "config_write_rejected" in actions
    assert "reload" in actions


@pytest.mark.asyncio
async def test_list_survives_missing_encryption_key(
    client_factory, store, audit_calls, monkeypatch
):
    store.rows[("local", "LOG_LEVEL")] = AdminConfigOverride(
        environment="local", name="LOG_LEVEL", value_encrypted="not-a-real-token"
    )
    monkeypatch.delenv("INTEGRATIONS_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    crypto._fernet.cache_clear()
    async with client_factory(UserRole.super_admin) as c:
        r = await c.get("/api/admin/config?environment=local")
    assert r.status_code == 200
    item = next(i for i in r.json()["items"] if i["name"] == "LOG_LEVEL")
    assert item["overridden"] is True
    assert item["value"] is None
