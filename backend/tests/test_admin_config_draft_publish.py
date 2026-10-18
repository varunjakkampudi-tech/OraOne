"""Admin configuration console: drafts, guarded publish, diff masking, history.

No test touches a real database or real provider. The table helpers in
``app.services.config_console`` are replaced with an in-memory store, audit
calls are captured, and the router is mounted on a small FastAPI app so the
test does not depend on the full server import.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.admin_config import routes as admin_config_routes
from app.core import config_overrides, crypto
from app.core.crypto import decrypt, encrypt
from app.database.models.admin_config_draft import AdminConfigDraft
from app.database.models.admin_config_override import AdminConfigOverride
from app.database.models.admin_config_publish_event import AdminConfigPublishEvent
from app.database.models.user import UserRole
from app.database.session import get_db
from app.middleware.platform_context import (
    PlatformContext,
    get_current_platform_context,
)
from app.services import config_console

SECRET_VALUE = "sk-or-live-THE-FULL-SECRET-9876"
DRAFT_SECRET = "sk-or-draft-SECRET-5555"
REASON = "Rotating the key after a planned review"
ADMIN_ID = "00000000-0000-4000-8000-000000000001"


class _Store:
    """In-memory replacement for the active, draft and publish-event tables."""

    def __init__(self) -> None:
        self.active: dict[tuple[str, str], AdminConfigOverride] = {}
        self.drafts: dict[tuple[str, str], AdminConfigDraft] = {}
        self.events: list[AdminConfigPublishEvent] = []

    async def fetch_rows(self, session, environment):
        return [row for (env, _), row in self.active.items() if env == environment]

    async def upsert_row(
        self, session, *, existing, environment, name, value_encrypted, actor_id, now
    ):
        if existing is None:
            self.active[(environment, name)] = AdminConfigOverride(
                environment=environment,
                name=name,
                value_encrypted=value_encrypted,
                updated_at=now,
            )
        else:
            existing.value_encrypted = value_encrypted
            existing.updated_at = now

    async def delete_row(self, session, *, environment, name):
        self.active.pop((environment, name), None)

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
    monkeypatch.setattr(config_console, "_fetch_rows", fake.fetch_rows)
    monkeypatch.setattr(config_console, "_upsert_row", fake.upsert_row)
    monkeypatch.setattr(config_console, "_delete_row", fake.delete_row)
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
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    yield
    crypto._fernet.cache_clear()


def _platform_context(role: UserRole) -> PlatformContext:
    user = SimpleNamespace(id=ADMIN_ID, email="admin@example.com")
    return PlatformContext(user=user, auth_subject="sub-admin", role=role)


@pytest.fixture
def client_factory(store, audit_calls):
    app = FastAPI()
    app.include_router(admin_config_routes.router)
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
    app.dependency_overrides.clear()


def _draft_body(**overrides):
    body = {
        "environment": "local",
        "value": "DEBUG",
        "confirm": "LOG_LEVEL",
        "reason": REASON,
    }
    body.update(overrides)
    return body


def _publish_body(store, environment="local", **overrides):
    reviewed = sorted(name for (env, name) in store.drafts if env == environment)
    body = {
        "environment": environment,
        "confirm": environment,
        "reason": REASON,
        "reviewed": reviewed,
    }
    body.update(overrides)
    return body


def _seed_active(store, environment, name, value):
    store.active[(environment, name)] = AdminConfigOverride(
        environment=environment,
        name=name,
        value_encrypted=encrypt(value),
        updated_at=datetime.now(timezone.utc),
    )


def _seed_draft(store, environment, name, value):
    store.drafts[(environment, name)] = AdminConfigDraft(
        environment=environment,
        name=name,
        action="set",
        value_encrypted=encrypt(value),
        updated_at=datetime.now(timezone.utc),
    )


# --------------------------------------------------------------------------- #
# Access control                                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.admin, UserRole.manager, UserRole.user])
async def test_non_super_admin_cannot_draft_discard_publish_or_read(
    client_factory, store, audit_calls, role
):
    _seed_draft(store, "local", "LOG_LEVEL", "DEBUG")
    client = client_factory(role)
    async with client as c:
        draft = await c.put("/api/admin/config/LOG_LEVEL", json=_draft_body())
        drafts = await c.get("/api/admin/config/drafts?environment=local")
        discard = await c.delete("/api/admin/config/drafts/LOG_LEVEL?environment=local")
        publish = await c.post("/api/admin/config/publish", json=_publish_body(store))
        history = await c.get("/api/admin/config/history?environment=local")
    assert draft.status_code == 403
    assert drafts.status_code == 403
    assert discard.status_code == 403
    assert publish.status_code == 403
    assert history.status_code == 403
    assert ("local", "LOG_LEVEL") in store.drafts
    assert store.active == {}
    assert store.events == []
    assert audit_calls == []


# --------------------------------------------------------------------------- #
# Drafts do not change the active configuration                               #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_drafts_do_not_change_active_config(
    client_factory, store, audit_calls, monkeypatch
):
    def _must_not_apply(values):
        raise AssertionError("a draft must not reach the running process")

    monkeypatch.setattr(config_overrides, "apply_overrides", _must_not_apply)
    async with client_factory(UserRole.super_admin) as c:
        saved = await c.put("/api/admin/config/LOG_LEVEL", json=_draft_body())
        listing = await c.get("/api/admin/config?environment=local")

    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "draft_saved"
    assert saved.json()["active"] is False
    assert saved.json()["restart_required"] is False
    assert saved.json()["publish_required"] is True
    assert store.active == {}
    assert store.events == []
    item = next(i for i in listing.json()["items"] if i["name"] == "LOG_LEVEL")
    assert item["overridden"] is False
    assert item["draft_pending"] is True
    assert item["value"] == "WARNING"  # the process value, untouched
    assert listing.json()["draft_count"] == 1


@pytest.mark.asyncio
async def test_draft_value_is_stored_encrypted(client_factory, store, audit_calls):
    async with client_factory(UserRole.super_admin) as c:
        await c.put(
            "/api/admin/config/OPENROUTER_API_KEY",
            json=_draft_body(value=DRAFT_SECRET, confirm="OPENROUTER_API_KEY"),
        )
    stored = store.drafts[("local", "OPENROUTER_API_KEY")]
    assert DRAFT_SECRET not in stored.value_encrypted
    assert decrypt(stored.value_encrypted) == DRAFT_SECRET


@pytest.mark.asyncio
async def test_clearing_a_key_with_nothing_active_leaves_no_draft(
    client_factory, store, audit_calls
):
    async with client_factory(UserRole.super_admin) as c:
        r = await c.put("/api/admin/config/LOG_LEVEL", json=_draft_body(value=None))
    assert r.status_code == 200
    assert r.json()["status"] == "unchanged"
    assert store.drafts == {}


@pytest.mark.asyncio
async def test_discard_removes_draft_and_keeps_active_value(
    client_factory, store, audit_calls
):
    _seed_active(store, "local", "LOG_LEVEL", "INFO")
    _seed_draft(store, "local", "LOG_LEVEL", "DEBUG")
    async with client_factory(UserRole.super_admin) as c:
        r = await c.delete("/api/admin/config/drafts/LOG_LEVEL?environment=local")
        missing = await c.delete("/api/admin/config/drafts/LOG_LEVEL?environment=local")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "discarded"
    assert missing.status_code == 404
    assert store.drafts == {}
    assert decrypt(store.active[("local", "LOG_LEVEL")].value_encrypted) == "INFO"
    assert any(action == "draft_discard" for action, _ in audit_calls)


# --------------------------------------------------------------------------- #
# Publish: confirmation and reason                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_publish_requires_typed_environment_name(
    store, client_factory, audit_calls
):
    _seed_draft(store, "local", "LOG_LEVEL", "DEBUG")
    async with client_factory(UserRole.super_admin) as c:
        wrong = await c.post(
            "/api/admin/config/publish",
            json=_publish_body(store, confirm="LOCAL"),
        )
        missing = await c.post(
            "/api/admin/config/publish",
            json=_publish_body(store, confirm=None),
        )
    assert wrong.status_code == 400
    assert missing.status_code == 400
    assert ("local", "LOG_LEVEL") in store.drafts
    assert store.active == {}
    assert store.events == []
    codes = [
        kw["meta"]["reason_code"]
        for action, kw in audit_calls
        if action == "config_write_rejected"
    ]
    assert codes == ["confirm_mismatch", "confirm_mismatch"]


@pytest.mark.asyncio
async def test_publish_requires_a_reason_of_ten_characters(
    store, client_factory, audit_calls
):
    _seed_draft(store, "local", "LOG_LEVEL", "DEBUG")
    async with client_factory(UserRole.super_admin) as c:
        none = await c.post(
            "/api/admin/config/publish", json=_publish_body(store, reason=None)
        )
        short = await c.post(
            "/api/admin/config/publish", json=_publish_body(store, reason="123456789")
        )
        ok = await c.post(
            "/api/admin/config/publish", json=_publish_body(store, reason="1234567890")
        )
    assert none.status_code == 400
    assert short.status_code == 400
    assert ok.status_code == 200, ok.text
    codes = [
        kw["meta"]["reason_code"]
        for action, kw in audit_calls
        if action == "config_write_rejected"
    ]
    assert codes == ["reason_length", "reason_length"]


@pytest.mark.asyncio
async def test_publish_refuses_when_drafts_changed_after_review(
    store, client_factory, audit_calls
):
    _seed_draft(store, "local", "LOG_LEVEL", "DEBUG")
    _seed_draft(store, "local", "ORAONE_VERSION", "2.0")
    async with client_factory(UserRole.super_admin) as c:
        stale = await c.post(
            "/api/admin/config/publish",
            json=_publish_body(store, reviewed=["LOG_LEVEL"]),
        )
    assert stale.status_code == 409
    assert store.active == {}
    assert len(store.drafts) == 2


@pytest.mark.asyncio
async def test_publish_with_no_drafts_is_a_conflict(store, client_factory, audit_calls):
    async with client_factory(UserRole.super_admin) as c:
        r = await c.post("/api/admin/config/publish", json=_publish_body(store))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_publish_refuses_a_draft_for_a_key_that_cannot_be_set(
    store, client_factory, audit_calls
):
    store.drafts[("local", "DATABASE_URL")] = AdminConfigDraft(
        environment="local",
        name="DATABASE_URL",
        action="set",
        value_encrypted=encrypt("postgresql://x"),
        updated_at=datetime.now(timezone.utc),
    )
    async with client_factory(UserRole.super_admin) as c:
        r = await c.post("/api/admin/config/publish", json=_publish_body(store))
    assert r.status_code == 400
    assert r.json()["detail"].startswith("A draft is for a key")
    assert store.active == {}
    assert ("local", "DATABASE_URL") in store.drafts


# --------------------------------------------------------------------------- #
# Publish applies drafts and records history                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_publish_applies_drafts_and_says_restart_is_required(
    store, client_factory, audit_calls
):
    _seed_active(store, "local", "ORAONE_VERSION", "1.0")
    _seed_draft(store, "local", "LOG_LEVEL", "DEBUG")
    store.drafts[("local", "ORAONE_VERSION")] = AdminConfigDraft(
        environment="local",
        name="ORAONE_VERSION",
        action="clear",
        value_encrypted=None,
        updated_at=datetime.now(timezone.utc),
    )
    async with client_factory(UserRole.super_admin) as c:
        r = await c.post("/api/admin/config/publish", json=_publish_body(store))
        listing = await c.get("/api/admin/config?environment=local")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "published"
    assert body["changed_keys"] == ["LOG_LEVEL", "ORAONE_VERSION"]
    assert body["restart_required"] is True
    assert decrypt(store.active[("local", "LOG_LEVEL")].value_encrypted) == "DEBUG"
    assert ("local", "ORAONE_VERSION") not in store.active
    assert store.drafts == {}
    assert listing.json()["restart_required"] is True


@pytest.mark.asyncio
async def test_publish_is_audited_with_key_names_and_no_values(
    store, client_factory, audit_calls
):
    _seed_draft(store, "local", "OPENROUTER_API_KEY", DRAFT_SECRET)
    async with client_factory(UserRole.super_admin) as c:
        saved = await c.put(
            "/api/admin/config/OPENROUTER_API_KEY",
            json=_draft_body(value=DRAFT_SECRET, confirm="OPENROUTER_API_KEY"),
        )
        published = await c.post("/api/admin/config/publish", json=_publish_body(store))
    assert saved.status_code == 200
    assert published.status_code == 200

    publish_records = [kw for action, kw in audit_calls if action == "publish"]
    assert len(publish_records) == 1
    meta = publish_records[0]["meta"]
    assert meta["admin_email"] == "admin@example.com"
    assert publish_records[0]["user_id"] == ADMIN_ID
    assert meta["changed_keys"] == ["OPENROUTER_API_KEY"]
    assert meta["changes"] == ["OPENROUTER_API_KEY:set"]
    assert meta["reason"] == REASON
    assert meta["environment"] == "local"

    assert DRAFT_SECRET not in json.dumps(audit_calls, default=str)
    assert SECRET_VALUE not in json.dumps(audit_calls, default=str)


# --------------------------------------------------------------------------- #
# Diff masks secrets                                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_diff_masks_secrets_on_both_sides(store, client_factory, audit_calls):
    _seed_active(store, "local", "OPENROUTER_API_KEY", SECRET_VALUE)
    _seed_draft(store, "local", "OPENROUTER_API_KEY", DRAFT_SECRET)
    async with client_factory(UserRole.super_admin) as c:
        r = await c.get("/api/admin/config/drafts?environment=local")
    assert r.status_code == 200
    text = r.text
    assert SECRET_VALUE not in text
    assert DRAFT_SECRET not in text
    entry = r.json()["drafts"][0]
    assert entry["name"] == "OPENROUTER_API_KEY"
    assert entry["kind"] == "secret"
    assert entry["changed"] is True
    assert entry["before"] == {"is_set": True, "masked_tail": "9876", "value": None}
    assert entry["after"] == {"is_set": True, "masked_tail": "5555", "value": None}


@pytest.mark.asyncio
async def test_diff_shows_plain_values_locally_but_hides_them_for_production(
    store, client_factory, audit_calls
):
    _seed_active(store, "local", "LOG_LEVEL", "INFO")
    _seed_draft(store, "local", "LOG_LEVEL", "DEBUG")
    _seed_draft(store, "production", "LOG_LEVEL", "ERROR")
    async with client_factory(UserRole.super_admin) as c:
        local = await c.get("/api/admin/config/drafts?environment=local")
        production = await c.get("/api/admin/config/drafts?environment=production")
    local_entry = local.json()["drafts"][0]
    assert local_entry["before"]["value"] == "INFO"
    assert local_entry["after"]["value"] == "DEBUG"
    prod_entry = production.json()["drafts"][0]
    assert prod_entry["after"] == {"is_set": True, "masked_tail": None, "value": None}
    assert "ERROR" not in production.text


@pytest.mark.asyncio
async def test_diff_marks_unchanged_when_draft_equals_active(
    store, client_factory, audit_calls
):
    _seed_active(store, "local", "LOG_LEVEL", "DEBUG")
    _seed_draft(store, "local", "LOG_LEVEL", "DEBUG")
    async with client_factory(UserRole.super_admin) as c:
        r = await c.get("/api/admin/config/drafts?environment=local")
    assert r.json()["drafts"][0]["changed"] is False


# --------------------------------------------------------------------------- #
# History: last 50 publishes, audited and masked                              #
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_history_lists_publishes_newest_first_with_key_names_only(
    store, client_factory, audit_calls
):
    _seed_draft(store, "local", "OPENROUTER_API_KEY", DRAFT_SECRET)
    async with client_factory(UserRole.super_admin) as c:
        await c.put(
            "/api/admin/config/OPENROUTER_API_KEY",
            json=_draft_body(value=DRAFT_SECRET, confirm="OPENROUTER_API_KEY"),
        )
        await c.post("/api/admin/config/publish", json=_publish_body(store))
        history = await c.get("/api/admin/config/history?environment=local")
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) == 1
    assert items[0]["changes"] == [{"name": "OPENROUTER_API_KEY", "change": "set"}]
    assert items[0]["published_by_email"] == "admin@example.com"
    assert items[0]["reason"] == REASON
    assert DRAFT_SECRET not in history.text
    assert SECRET_VALUE not in history.text


@pytest.mark.asyncio
async def test_history_returns_at_most_the_last_fifty_publishes(
    store, client_factory, audit_calls
):
    base = datetime.now(timezone.utc) - timedelta(days=1)
    for index in range(55):
        store.events.append(
            AdminConfigPublishEvent(
                id=uuid.uuid4(),
                environment="local",
                published_by=None,
                published_by_email="admin@example.com",
                published_at=base + timedelta(minutes=index),
                reason=REASON,
                changes=[{"name": "LOG_LEVEL", "change": "set"}],
            )
        )
    async with client_factory(UserRole.super_admin) as c:
        r = await c.get("/api/admin/config/history?environment=local")
    items = r.json()["items"]
    assert len(items) == 50
    times = [item["published_at"] for item in items]
    assert times == sorted(times, reverse=True)
    assert items[0]["published_at"] == (base + timedelta(minutes=54)).isoformat()


@pytest.mark.asyncio
async def test_history_is_separated_by_environment(store, client_factory, audit_calls):
    _seed_draft(store, "production", "LOG_LEVEL", "ERROR")
    async with client_factory(UserRole.super_admin) as c:
        await c.post(
            "/api/admin/config/publish",
            json=_publish_body(store, environment="production"),
        )
        local = await c.get("/api/admin/config/history?environment=local")
        production = await c.get("/api/admin/config/history?environment=production")
    assert local.json()["items"] == []
    assert len(production.json()["items"]) == 1


@pytest.mark.asyncio
async def test_draft_save_and_discard_are_audited_without_values(
    store, client_factory, audit_calls
):
    async with client_factory(UserRole.super_admin) as c:
        await c.put(
            "/api/admin/config/OPENROUTER_API_KEY",
            json=_draft_body(value=DRAFT_SECRET, confirm="OPENROUTER_API_KEY"),
        )
        await c.delete("/api/admin/config/drafts/OPENROUTER_API_KEY?environment=local")
    actions = [action for action, _ in audit_calls]
    assert actions == ["draft_save", "draft_discard"]
    assert audit_calls[0][1]["meta"]["change"] == "set"
    assert audit_calls[0][1]["meta"]["reason"] == REASON
    assert DRAFT_SECRET not in json.dumps(audit_calls, default=str)
