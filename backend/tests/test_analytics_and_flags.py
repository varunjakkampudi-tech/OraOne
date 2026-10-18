"""Admin analytics and beta feature flags.

No test touches a real database or provider. Sessions are recording fakes, the
flag override store is an in-memory dict, and audit calls are captured. HTTP
tests use the real FastAPI app with auth and DB dependencies overridden.
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.models.feature_flag_override import FeatureFlagOverride
from app.database.models.user import UserRole
from app.database.session import get_db
from app.api.feature_flags import routes as feature_flags_routes
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.platform_context import (
    PlatformContext,
    get_current_platform_context,
)
from app.services import admin_analytics_service
from app.services import feature_flags as flags

ORG_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
OTHER_ORG_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
ACTOR_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
MEMBER_EMAIL = "beta.member@example.com"
PERSONAL_MARKERS = ("@", "beta.member", "Jane Customer", "+15551234567")
FORBIDDEN_KEYS = {
    "email",
    "emails",
    "name",
    "full_name",
    "phone",
    "text",
    "content",
    "body",
}


# --------------------------------------------------------------------------- #
# Fakes                                                                       #
# --------------------------------------------------------------------------- #
class _Rows:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return self._rows

    def scalars(self):
        return self


class RecordingSession:
    """Records every statement and returns empty or zero results."""

    def __init__(self, scalar_value=None, store=None):
        self.statements: list = []
        self.scalar_value = scalar_value
        self.store = store
        self.added: list = []
        self.commits = 0

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return self.scalar_value

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _Rows([])

    def add(self, obj):
        self.added.append(obj)
        if self.store is not None:
            self.store.store(obj)

    async def delete(self, obj):
        self.added = [o for o in self.added if o is not obj]
        if self.store is not None:
            self.store.remove(obj)

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None


class OverrideStore:
    """In-memory replacement for the feature_flag_overrides table."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, str], FeatureFlagOverride] = {}
        self.load_calls = 0

    def find(self, flag_key, scope, scope_value):
        return self.rows.get((flag_key, scope, scope_value))

    def store(self, obj):
        self.rows[(obj.flag_key, obj.scope, obj.scope_value)] = obj

    def remove(self, obj):
        self.rows.pop((obj.flag_key, obj.scope, obj.scope_value), None)

    def set(self, flag_key, scope, scope_value, enabled):
        self.store(
            FeatureFlagOverride(
                flag_key=flag_key,
                scope=scope,
                scope_value=scope_value,
                enabled=enabled,
            )
        )


@pytest.fixture
def store(monkeypatch):
    s = OverrideStore()

    async def _find(session, flag_key, scope, scope_value):
        return s.find(flag_key, scope, scope_value)

    async def _load(session, email_hash, organization_id):
        s.load_calls += 1
        org_map, member_map = {}, {}
        for (flag_key, scope, value), row in s.rows.items():
            if scope == flags.SCOPE_COHORT_MEMBER and value == email_hash:
                member_map[flag_key] = bool(row.enabled)
            if (
                scope == flags.SCOPE_ORGANIZATION
                and organization_id
                and value == organization_id
            ):
                org_map[flag_key] = bool(row.enabled)
        return org_map, member_map

    monkeypatch.setattr(flags, "_find_override", _find)
    monkeypatch.setattr(flags, "_load_overrides", _load)
    flags.invalidate_cache()
    yield s
    flags.invalidate_cache()


@pytest.fixture
def audit_calls(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def _capture(action, **kwargs):
        calls.append((action, kwargs))

    async def _noop_flush(session):
        return 0

    monkeypatch.setattr(flags, "audit", _capture)
    monkeypatch.setattr(feature_flags_routes, "flush_pending", _noop_flush)
    return calls


@pytest.fixture
def clock(monkeypatch):
    now = {"t": 1000.0}
    monkeypatch.setattr(flags, "_clock", lambda: now["t"])
    return now


def _platform_ctx(role: UserRole, email: str = MEMBER_EMAIL) -> PlatformContext:
    user = SimpleNamespace(
        id=ACTOR_ID, email=email, full_name="Jane Customer", role=role
    )
    return PlatformContext(user=user, auth_subject="sub-test", role=role)


@pytest.fixture
def client_factory():
    from server import app

    def _make(*, role: UserRole, session=None, org_role: str | None = None):
        session = session or RecordingSession()
        app.dependency_overrides[get_current_platform_context] = lambda: _platform_ctx(
            role
        )
        app.dependency_overrides[get_db] = lambda: session
        if org_role is not None:
            app.dependency_overrides[get_current_organization] = lambda: OrgContext(
                user_id=ACTOR_ID,
                auth_subject="sub-test",
                organization_id=ORG_ID,
                membership_role=org_role,
                platform_role="user",
            )
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    yield _make
    for dep in (get_current_platform_context, get_db, get_current_organization):
        app.dependency_overrides.pop(dep, None)


def _walk_keys(value, out: set[str]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            out.add(str(k).lower())
            _walk_keys(v, out)
    elif isinstance(value, list):
        for item in value:
            _walk_keys(item, out)


def _walk_strings(value, out: list[str]) -> None:
    if isinstance(value, dict):
        for v in value.values():
            _walk_strings(v, out)
    elif isinstance(value, list):
        for item in value:
            _walk_strings(item, out)
    elif isinstance(value, str):
        out.append(value)


# --------------------------------------------------------------------------- #
# Analytics: no personal data                                                 #
# --------------------------------------------------------------------------- #
async def test_platform_overview_returns_no_personal_data_fields():
    session = RecordingSession(scalar_value=3)
    data = await admin_analytics_service.platform_overview(session)

    keys: set[str] = set()
    _walk_keys(data, keys)
    assert keys.isdisjoint(FORBIDDEN_KEYS)

    strings: list[str] = []
    _walk_strings(data, strings)
    for text in strings:
        for marker in PERSONAL_MARKERS:
            assert marker not in text

    assert data["totals"]["organizations"] == 3
    assert set(data["totals"]) == {
        "organizations",
        "active_users_30d",
        "conversations_30d",
        "messages_30d",
        "leads_30d",
        "calls_placed_30d",
        "workflows_run_30d",
    }
    assert len(data["daily"]["conversations"]) == 30
    assert len(data["daily"]["messages"]) == 30
    assert len(data["daily"]["server_errors"]) == 30


async def test_platform_overview_uses_only_counting_statements():
    session = RecordingSession()
    await admin_analytics_service.platform_overview(session)
    assert session.statements, "expected aggregate queries"
    for stmt in session.statements:
        sql = str(stmt.compile()).upper()
        assert "SELECT" in sql
        # Only COUNT or GROUP BY keys are selected; no free-text columns.
        selected = sql.split("FROM", 1)[0]
        for banned in ("CONTENT", "EMAIL", "PHONE", "FULL_NAME", "TEXT", "NAME"):
            assert banned not in selected, f"{banned} selected in {selected}"


async def test_admin_analytics_endpoint_allows_super_admin_and_admin(client_factory):
    for role in (UserRole.super_admin, UserRole.admin):
        client = client_factory(role=role, session=RecordingSession(scalar_value=1))
        async with client:
            response = await client.get("/api/admin/analytics/overview")
        assert response.status_code == 200, role
        body = response.json()
        assert body["window_days"] == 30
        keys: set[str] = set()
        _walk_keys(body, keys)
        assert keys.isdisjoint(FORBIDDEN_KEYS)


async def test_admin_analytics_endpoint_refuses_regular_users(client_factory):
    client = client_factory(role=UserRole.user)
    async with client:
        response = await client.get("/api/admin/analytics/overview")
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Analytics: organisation scoping                                             #
# --------------------------------------------------------------------------- #
async def test_org_summary_binds_every_query_to_the_caller_organization():
    session = RecordingSession()
    await admin_analytics_service.org_summary(session, ORG_ID)
    assert session.statements
    for stmt in session.statements:
        params = list(stmt.compile().params.values())
        assert ORG_ID in params, f"query not scoped to organization: {stmt}"
        assert OTHER_ORG_ID not in params


async def test_org_summary_scopes_to_the_requested_organization_only():
    first = RecordingSession()
    second = RecordingSession()
    await admin_analytics_service.org_summary(first, ORG_ID)
    await admin_analytics_service.org_summary(second, OTHER_ORG_ID)
    first_params = [list(s.compile().params.values()) for s in first.statements]
    second_params = [list(s.compile().params.values()) for s in second.statements]
    assert all(OTHER_ORG_ID not in p for p in first_params)
    assert all(ORG_ID not in p for p in second_params)


async def test_summary_endpoint_is_owner_only_and_uses_caller_org(client_factory):
    session = RecordingSession()
    client = client_factory(role=UserRole.user, session=session, org_role="member")
    async with client:
        response = await client.get("/api/analytics/summary")
    assert response.status_code == 403

    session = RecordingSession()
    client = client_factory(role=UserRole.user, session=session, org_role="owner")
    async with client:
        response = await client.get("/api/analytics/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == str(ORG_ID)
    keys: set[str] = set()
    _walk_keys(body, keys)
    assert keys.isdisjoint(FORBIDDEN_KEYS)
    for stmt in session.statements:
        assert ORG_ID in list(stmt.compile().params.values())


# --------------------------------------------------------------------------- #
# Feature flags: defaults and precedence                                      #
# --------------------------------------------------------------------------- #
def test_flags_default_off_without_overrides():
    for definition in flags.FLAG_DEFINITIONS:
        assert definition.default_enabled is False
        resolved = flags.resolve_flag(
            definition,
            organization_id=str(ORG_ID),
            email_hash=flags.hash_email(MEMBER_EMAIL),
            org_override=None,
            member_override=None,
        )
        assert resolved is False


def test_code_rollout_lists_turn_flags_on_for_listed_org_or_member():
    definition = flags.FlagDefinition(
        key="test_rollout",
        description="test",
        rollout_organization_ids=frozenset({str(ORG_ID)}),
        rollout_email_hashes=frozenset({flags.hash_email(MEMBER_EMAIL)}),
    )
    assert flags.resolve_flag(
        definition,
        organization_id=str(ORG_ID),
        email_hash="other",
        org_override=None,
        member_override=None,
    )
    assert flags.resolve_flag(
        definition,
        organization_id=None,
        email_hash=flags.hash_email(MEMBER_EMAIL),
        org_override=None,
        member_override=None,
    )


def test_organisation_override_beats_cohort_and_code_rules():
    definition = flags.FlagDefinition(
        key="test_precedence",
        description="test",
        default_enabled=True,
    )
    email_hash = flags.hash_email(MEMBER_EMAIL)
    assert (
        flags.resolve_flag(
            definition,
            organization_id=str(ORG_ID),
            email_hash=email_hash,
            org_override=False,
            member_override=True,
        )
        is False
    )


def test_email_hash_is_normalised_and_not_the_address():
    assert flags.hash_email("Beta.Member@Example.com ") == flags.hash_email(
        MEMBER_EMAIL
    )
    assert MEMBER_EMAIL not in flags.hash_email(MEMBER_EMAIL)


async def test_enabled_flags_empty_by_default(store):
    keys = await flags.enabled_flag_keys(RecordingSession(), email=MEMBER_EMAIL)
    assert keys == []


async def test_member_cohort_override_enables_flag_for_that_user_only(store):
    key = flags.FLAG_DEFINITIONS[0].key
    store.set(key, flags.SCOPE_COHORT_MEMBER, flags.hash_email(MEMBER_EMAIL), True)
    assert key in await flags.enabled_flag_keys(RecordingSession(), email=MEMBER_EMAIL)
    assert (
        await flags.enabled_flag_keys(RecordingSession(), email="someone@example.com")
        == []
    )


# --------------------------------------------------------------------------- #
# Feature flags: cache refresh                                                #
# --------------------------------------------------------------------------- #
async def test_cached_flags_are_served_for_60_seconds_then_refresh(store, clock):
    key = flags.FLAG_DEFINITIONS[0].key
    session = RecordingSession()

    assert await flags.enabled_flag_keys(session, email=MEMBER_EMAIL) == []
    # A change made elsewhere is not seen inside the TTL.
    store.set(key, flags.SCOPE_COHORT_MEMBER, flags.hash_email(MEMBER_EMAIL), True)
    clock["t"] += 59
    assert await flags.enabled_flag_keys(session, email=MEMBER_EMAIL) == []
    assert store.load_calls == 1

    clock["t"] += 2
    assert key in await flags.enabled_flag_keys(session, email=MEMBER_EMAIL)
    assert store.load_calls == 2


async def test_admin_write_refreshes_cached_flags_immediately(
    store, clock, audit_calls
):
    key = flags.FLAG_DEFINITIONS[0].key
    session = RecordingSession(store=store)
    assert (
        await flags.enabled_flag_keys(
            session, email=MEMBER_EMAIL, organization_id=ORG_ID
        )
        == []
    )

    await flags.set_organization_override(
        session,
        flag_key=key,
        organization_id=ORG_ID,
        enabled=True,
        actor_id=ACTOR_ID,
    )
    assert key in await flags.enabled_flag_keys(
        session, email=MEMBER_EMAIL, organization_id=ORG_ID
    )


# --------------------------------------------------------------------------- #
# Feature flags: endpoints, authorization and audit                           #
# --------------------------------------------------------------------------- #
async def test_get_feature_flags_returns_enabled_keys_for_caller(client_factory, store):
    key = flags.FLAG_DEFINITIONS[0].key
    store.set(key, flags.SCOPE_COHORT_MEMBER, flags.hash_email(MEMBER_EMAIL), True)
    client = client_factory(role=UserRole.user)
    async with client:
        response = await client.get("/api/feature-flags")
    assert response.status_code == 200
    assert response.json()["enabled"] == [key]
    assert "private" in response.headers["cache-control"]


async def test_get_feature_flags_with_org_requires_membership(client_factory, store):
    client = client_factory(
        role=UserRole.user, session=RecordingSession(scalar_value=None)
    )
    async with client:
        response = await client.get(f"/api/feature-flags?organization_id={ORG_ID}")
    assert response.status_code == 403


async def test_get_feature_flags_response_holds_no_email(client_factory, store):
    client = client_factory(role=UserRole.user)
    async with client:
        response = await client.get("/api/feature-flags")
    assert MEMBER_EMAIL not in response.text


async def test_only_super_admin_can_change_flags(client_factory, store, audit_calls):
    key = flags.FLAG_DEFINITIONS[0].key
    path = f"/api/admin/feature-flags/{key}/organizations/{ORG_ID}"
    for role in (UserRole.admin, UserRole.manager, UserRole.user):
        client = client_factory(role=role)
        async with client:
            response = await client.put(path, json={"enabled": True})
        assert response.status_code == 403, role
    assert store.rows == {}
    assert audit_calls == []

    client = client_factory(
        role=UserRole.super_admin, session=RecordingSession(store=store)
    )
    async with client:
        response = await client.put(path, json={"enabled": True})
    assert response.status_code == 200
    assert response.json() == {
        "flag_key": key,
        "scope": "organization",
        "enabled": True,
    }


async def test_only_super_admin_can_read_admin_flag_list(client_factory, store):
    client = client_factory(role=UserRole.admin)
    async with client:
        response = await client.get("/api/admin/feature-flags")
    assert response.status_code == 403

    client = client_factory(role=UserRole.super_admin)
    async with client:
        response = await client.get("/api/admin/feature-flags")
    assert response.status_code == 200
    assert {f["key"] for f in response.json()["flags"]} == {
        f.key for f in flags.FLAG_DEFINITIONS
    }


async def test_organisation_flag_change_is_audited(store, audit_calls):
    key = flags.FLAG_DEFINITIONS[0].key
    await flags.set_organization_override(
        RecordingSession(),
        flag_key=key,
        organization_id=ORG_ID,
        enabled=True,
        actor_id=ACTOR_ID,
    )
    assert len(audit_calls) == 1
    action, kwargs = audit_calls[0]
    assert action == "feature_flag.organization_override_set"
    assert kwargs["organization_id"] == str(ORG_ID)
    assert kwargs["user_id"] == str(ACTOR_ID)
    assert kwargs["resource_id"] == key
    assert kwargs["before"] == {"enabled": None}
    assert kwargs["after"] == {"enabled": True}


async def test_cohort_change_is_audited_without_the_email(store, audit_calls):
    key = flags.FLAG_DEFINITIONS[0].key
    await flags.set_cohort_member(
        RecordingSession(),
        flag_key=key,
        email=MEMBER_EMAIL,
        enabled=True,
        actor_id=ACTOR_ID,
    )
    assert len(audit_calls) == 1
    action, kwargs = audit_calls[0]
    assert action == "feature_flag.cohort_member_set"
    assert kwargs["meta"]["member_hash"] == flags.hash_email(MEMBER_EMAIL)
    assert MEMBER_EMAIL not in json.dumps(kwargs, default=str)


async def test_cohort_endpoint_stores_hash_not_email(
    client_factory, store, audit_calls
):
    key = flags.FLAG_DEFINITIONS[0].key
    client = client_factory(
        role=UserRole.super_admin, session=RecordingSession(store=store)
    )
    async with client:
        response = await client.put(
            f"/api/admin/feature-flags/{key}/cohort/members",
            json={"email": MEMBER_EMAIL, "enabled": True},
        )
    assert response.status_code == 200
    assert MEMBER_EMAIL not in response.text
    stored = store.find(key, flags.SCOPE_COHORT_MEMBER, flags.hash_email(MEMBER_EMAIL))
    assert stored is not None and stored.enabled is True
    assert all(MEMBER_EMAIL not in value for (_, _, value) in store.rows)


async def test_clearing_an_override_removes_it_and_is_audited(store, audit_calls):
    key = flags.FLAG_DEFINITIONS[0].key
    store.set(key, flags.SCOPE_ORGANIZATION, str(ORG_ID), True)
    result = await flags.set_organization_override(
        RecordingSession(store=store),
        flag_key=key,
        organization_id=ORG_ID,
        enabled=None,
        actor_id=ACTOR_ID,
    )
    assert result["enabled"] is None
    assert store.find(key, flags.SCOPE_ORGANIZATION, str(ORG_ID)) is None
    assert audit_calls[-1][1]["before"] == {"enabled": True}


async def test_unknown_flag_is_refused(client_factory, store, audit_calls):
    client = client_factory(role=UserRole.super_admin)
    async with client:
        response = await client.put(
            f"/api/admin/feature-flags/not_a_flag/organizations/{ORG_ID}",
            json={"enabled": True},
        )
    assert response.status_code == 404
    assert audit_calls == []
