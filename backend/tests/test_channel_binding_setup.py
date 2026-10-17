"""Channel binding setup: user-settable routing fields, server-issued secrets, and inbound resolution.

Covers the PATCH /api/agents/{agent_id}/channels/{channel} settings, the rotate-secret
endpoint, and proof that a binding configured through the API is then found by the
inbound path. The HTTP routes run for real through FastAPI's TestClient. The database
is an in-memory session that evaluates the real SQLAlchemy statements the routes and
the inbound resolver build, so no Postgres or provider is needed. Nothing is sent
anywhere: audit is captured and no outbound request is made.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import operator
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression, BindParameter, BooleanClauseList

from app.api.channels import routes as channel_routes
from app.api.omnichannel import routes as omni_routes
from app.api.voice import routes as voice_routes
from app.core import crypto
from app.database.models.agent import Agent
from app.database.models.agent_channel import AgentChannel
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.services import channels_service
from app.services.channels import adapters, binding_secrets
from app.services.channels.adapters import ParsedInbound

ORG_A = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
ORG_B = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")
AGENT_A = uuid.UUID("aaaaaaaa-1111-0000-0000-000000000001")
AGENT_B = uuid.UUID("bbbbbbbb-1111-0000-0000-000000000002")
WA_ID = "100200300400500"
IG_ID = "9988776655443"
VOICE_NUMBER = "+14155550123"
INBOUND = "support@acme.example.test"


# ───────────────────────── in-memory session ─────────────────────────


def _value(expr: Any, row: Any) -> Any:
    if isinstance(expr, BindParameter):
        return expr.value
    name = type(expr).__name__
    if name == "True_":
        return True
    if name == "False_":
        return False
    if name == "Null":
        return None
    if (
        isinstance(expr, BinaryExpression)
        and getattr(expr.operator, "opstring", None) == "->>"
    ):
        config = getattr(row, "configuration", None) or {}
        found = config.get(expr.right.value)
        return None if found is None else str(found)
    key = getattr(expr, "key", None)
    if key is not None and hasattr(row, key):
        return getattr(row, key)
    raise AssertionError(f"cannot evaluate {expr!r}")


def _matches(expr: Any, row: Any) -> bool:
    if isinstance(expr, BooleanClauseList):
        return all(_matches(clause, row) for clause in expr.clauses)
    if isinstance(expr, BinaryExpression):
        left = _value(expr.left, row)
        right = _value(expr.right, row)
        op = expr.operator
        if op is operator.eq:
            return left == right
        if op is operator.ne:
            return left != right
        if op is operators.is_:
            return left is right
        if op is operators.in_op:
            return left in right
    raise AssertionError(f"unsupported clause {expr!r}")


class FakeSession:
    """Just enough of AsyncSession for the channel routes and the inbound resolver."""

    def __init__(self) -> None:
        self.agents: list[Agent] = []
        self.channels: list[AgentChannel] = []
        self.commits = 0

    def add_agent(self, agent_id: uuid.UUID, org_id: uuid.UUID, name: str) -> Agent:
        agent = Agent(id=agent_id, organization_id=org_id, name=name, deleted_at=None)
        self.agents.append(agent)
        return agent

    def _select(self, stmt) -> list[Any]:
        desc = stmt.column_descriptions[0]
        pool = self.agents if desc["entity"] is Agent else self.channels
        return [r for r in pool if all(_matches(c, r) for c in stmt._where_criteria)]

    def _project(self, stmt, row):
        desc = stmt.column_descriptions[0]
        if desc["expr"] is desc["entity"]:
            return row
        return getattr(row, desc["name"])

    async def scalar(self, stmt):
        rows = self._select(stmt)
        return self._project(stmt, rows[0]) if rows else None

    async def scalars(self, stmt):
        items = [self._project(stmt, r) for r in self._select(stmt)]
        return SimpleNamespace(all=lambda: items)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


@pytest.fixture
def crypto_key(monkeypatch):
    monkeypatch.setenv("INTEGRATIONS_ENCRYPTION_KEY", Fernet.generate_key().decode())
    crypto._fernet.cache_clear()
    yield
    crypto._fernet.cache_clear()


@pytest.fixture
def world(monkeypatch, crypto_key):
    """Two organizations, one agent each, and captured audit records."""
    db = FakeSession()
    db.add_agent(AGENT_A, ORG_A, "Acme support")
    db.add_agent(AGENT_B, ORG_B, "Other org agent")

    async def ensure_channels(session, agent):
        rows = []
        for defn in channels_service.CHANNEL_DEFS:
            row = next(
                (
                    c
                    for c in session.channels
                    if c.agent_id == agent.id and c.channel == defn["channel"]
                ),
                None,
            )
            if row is None:
                row = AgentChannel(
                    id=uuid.uuid4(),
                    organization_id=agent.organization_id,
                    agent_id=agent.id,
                    channel=defn["channel"],
                    enabled=False,
                    status="disabled",
                    configuration={},
                )
                session.channels.append(row)
            rows.append(row)
        return rows

    audits: list[dict[str, Any]] = []
    monkeypatch.setattr(channels_service, "ensure_channels", ensure_channels)
    monkeypatch.setattr(
        channel_routes,
        "audit",
        lambda action, **kw: audits.append({"action": action, **kw}),
    )
    return SimpleNamespace(db=db, audits=audits)


def _client(world, *, org: uuid.UUID, role: str = "owner") -> TestClient:
    ctx = OrgContext(
        user_id=uuid.uuid4(),
        auth_subject=f"sub-{org}",
        organization_id=org,
        membership_role=role,
    )
    app = FastAPI()
    app.include_router(channel_routes.router)
    app.dependency_overrides[get_db] = lambda: world.db
    app.dependency_overrides[get_current_organization] = lambda: ctx
    return TestClient(app)


def _patch(client: TestClient, agent_id: uuid.UUID, channel: str, body: dict):
    return client.patch(f"/api/agents/{agent_id}/channels/{channel}", json=body)


def _rotate(client: TestClient, agent_id: uuid.UUID, channel: str):
    return client.post(f"/api/agents/{agent_id}/channels/{channel}/rotate-secret")


def _sdk_sig(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ───────────────────────── validation rules ─────────────────────────


@pytest.mark.parametrize(
    "channel, field, value",
    [
        ("whatsapp", "phone_number_id", WA_ID),
        ("instagram", "instagram_account_id", IG_ID),
        ("voice", "phone_number", VOICE_NUMBER),
        ("email", "inbound_address", INBOUND),
    ],
)
def test_valid_settings_are_accepted(channel, field, value):
    cleaned = channels_service.validate_channel_settings(channel, {field: value})
    assert cleaned == {field: value}


@pytest.mark.parametrize(
    "channel, field, value",
    [
        ("whatsapp", "phone_number_id", "1002003004005x"),
        ("whatsapp", "phone_number_id", "+100200300400"),
        ("whatsapp", "phone_number_id", "1234"),  # too short
        ("instagram", "instagram_account_id", "acct-99887766"),
        ("instagram", "instagram_account_id", "9" * 33),  # too long
        ("voice", "phone_number", "4155550123"),  # no plus sign
        ("voice", "phone_number", "+0123456789"),  # cannot start with 0
        ("voice", "phone_number", "+1 415 555 0123"),  # spaces are not E.164
        ("email", "inbound_address", "not-an-email"),
        ("email", "inbound_address", "a@b"),
        ("email", "inbound_address", "x" * 250 + "@example.test"),
    ],
)
def test_invalid_settings_are_refused(channel, field, value):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        channels_service.validate_channel_settings(channel, {field: value})
    assert exc.value.status_code == 422


def test_settings_for_another_channel_are_refused():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        channels_service.validate_channel_settings(
            "whatsapp", {"inbound_address": INBOUND}
        )
    assert exc.value.status_code == 422


def test_email_address_is_normalised_and_empty_clears():
    assert channels_service.validate_channel_settings(
        "email", {"inbound_address": "  Support@ACME.example.test "}
    ) == {"inbound_address": INBOUND}
    assert channels_service.validate_channel_settings(
        "whatsapp", {"phone_number_id": "  "}
    ) == {"phone_number_id": None}


def test_patch_rejects_secret_fields_and_unknown_keys(world):
    client = _client(world, org=ORG_A)
    for body in (
        {"configuration": {"sdk_secret": "attacker-chosen"}},
        {"phone_number": VOICE_NUMBER},
        {"settings": {"sdk_secret": "attacker-chosen"}},
        {"settings": {"bot_token": "123:abc"}},
    ):
        response = _patch(client, AGENT_A, "whatsapp", body)
        assert response.status_code == 422, body
    assert all(c.configuration == {} for c in world.db.channels)


# ───────────────────────── settings and enable rules ─────────────────────────


def test_saving_whatsapp_number_returns_public_setting(world):
    client = _client(world, org=ORG_A)
    response = _patch(
        client, AGENT_A, "whatsapp", {"settings": {"phone_number_id": WA_ID}}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["configuration"] == {"phone_number_id": WA_ID}
    assert body["enabled"] is False


def test_channel_cannot_be_enabled_without_its_identifier(world):
    client = _client(world, org=ORG_A)
    response = _patch(client, AGENT_A, "voice", {"enabled": True})
    assert response.status_code == 422
    assert "phone number" in response.json()["detail"].lower()

    ok = _patch(
        client,
        AGENT_A,
        "voice",
        {"enabled": True, "settings": {"phone_number": VOICE_NUMBER}},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["enabled"] is True
    assert ok.json()["phone_number"] == VOICE_NUMBER


def test_telegram_cannot_be_enabled_from_the_api(world):
    client = _client(world, org=ORG_A)
    response = _patch(client, AGENT_A, "telegram", {"enabled": True})
    assert response.status_code == 422


def test_unknown_channel_is_404(world):
    client = _client(world, org=ORG_A)
    assert (
        _patch(client, AGENT_A, "carrier-pigeon", {"enabled": True}).status_code == 404
    )


# ───────────────────────── secrets ─────────────────────────


def test_enabling_sdk_issues_a_secret_once_and_never_returns_it_again(world):
    client = _client(world, org=ORG_A)
    first = _patch(client, AGENT_A, "sdk", {"enabled": True})
    assert first.status_code == 200, first.text
    issued = first.json()["one_time_secret"]
    assert issued["name"] == "sdk_secret"
    secret = issued["value"]
    assert len(secret) >= 40
    assert first.headers["cache-control"] == "no-store"
    assert first.json()["masked_secrets"] == {"sdk_secret": "••••" + secret[-4:]}

    # Stored encrypted, never in plaintext.
    stored = next(c for c in world.db.channels if c.channel == "sdk").configuration
    assert secret not in json.dumps(stored)
    assert binding_secrets.read_secret(stored, "sdk_secret") == secret

    # A later save does not issue another secret or return this one.
    second = _patch(client, AGENT_A, "sdk", {"enabled": True})
    assert second.json()["one_time_secret"] is None
    listing = client.get(f"/api/agents/{AGENT_A}/channels")
    assert listing.status_code == 200
    assert secret not in listing.text
    assert secret not in json.dumps(second.json())


def test_listing_exposes_only_masked_secrets_and_no_ciphertext(world):
    client = _client(world, org=ORG_A)
    issued = _patch(client, AGENT_A, "sdk", {"enabled": True}).json()[
        "one_time_secret"
    ]["value"]
    listing = client.get(f"/api/agents/{AGENT_A}/channels").json()
    row = next(item for item in listing["items"] if item["channel"] == "sdk")
    text = json.dumps(row)
    assert issued not in text
    assert "_encrypted" not in text
    assert "sdk_secret" in row["masked_secrets"]
    assert row["configuration"] == {}


def test_rotate_returns_a_new_secret_once_and_retires_the_old_one(world):
    client = _client(world, org=ORG_A)
    old = _patch(client, AGENT_A, "sdk", {"enabled": True}).json()["one_time_secret"][
        "value"
    ]

    rotated = _rotate(client, AGENT_A, "sdk")
    assert rotated.status_code == 200, rotated.text
    body = rotated.json()
    new = body["secret"]
    assert new != old
    assert body["shown_once"] is True
    assert body["secret_name"] == "sdk_secret"
    assert rotated.headers["cache-control"] == "no-store"
    assert new not in json.dumps(body["masked"])
    assert body["masked"].endswith(new[-4:])

    # The new secret is the one the inbound path now accepts. The old one is refused.
    payload = json.dumps({"text": "hi"}).encode()
    stored = next(c for c in world.db.channels if c.channel == "sdk").configuration
    current = binding_secrets.read_secret(stored, "sdk_secret")
    assert adapters.verify_sdk_signature(current, payload, _sdk_sig(new, payload))
    assert not adapters.verify_sdk_signature(current, payload, _sdk_sig(old, payload))

    # Rotating again is not echoed back by reads.
    listing = client.get(f"/api/agents/{AGENT_A}/channels")
    assert new not in listing.text


def test_rotate_telegram_webhook_secret(world):
    client = _client(world, org=ORG_A)
    rotated = _rotate(client, AGENT_A, "telegram")
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["secret_name"] == "telegram_webhook_secret"
    stored = next(c for c in world.db.channels if c.channel == "telegram").configuration
    assert (
        binding_secrets.read_secret(stored, "telegram_webhook_secret")
        == rotated.json()["secret"]
    )


@pytest.mark.parametrize("channel", ["email", "whatsapp", "voice", "instagram", "chat"])
def test_rotate_refused_for_channels_without_a_per_binding_secret(world, channel):
    client = _client(world, org=ORG_A)
    response = _rotate(client, AGENT_A, channel)
    assert response.status_code == 400
    assert response.json()["detail"]


def test_rotate_unknown_channel_is_404(world):
    client = _client(world, org=ORG_A)
    assert _rotate(client, AGENT_A, "carrier-pigeon").status_code == 404


def test_audit_records_names_not_values(world):
    client = _client(world, org=ORG_A)
    secret = _patch(client, AGENT_A, "sdk", {"enabled": True}).json()[
        "one_time_secret"
    ]["value"]
    rotated = _rotate(client, AGENT_A, "sdk").json()["secret"]
    _patch(client, AGENT_A, "whatsapp", {"settings": {"phone_number_id": WA_ID}})
    blob = json.dumps(world.audits, default=str)
    assert secret not in blob and rotated not in blob
    assert world.audits[-1]["meta"]["settings_changed"] == ["phone_number_id"]
    actions = [a["action"] for a in world.audits]
    assert "channel.secret.rotate" in actions


# ───────────────────────── permissions and isolation ─────────────────────────


@pytest.mark.parametrize("role", ["viewer"])
def test_members_without_agents_write_are_refused(world, role):
    client = _client(world, org=ORG_A, role=role)
    assert (
        _patch(
            client, AGENT_A, "whatsapp", {"settings": {"phone_number_id": WA_ID}}
        ).status_code
        == 403
    )
    assert _rotate(client, AGENT_A, "sdk").status_code == 403
    assert all(not c.configuration for c in world.db.channels)


@pytest.mark.parametrize("role", ["owner", "admin", "member"])
def test_roles_with_agents_write_can_configure(world, role):
    client = _client(world, org=ORG_A, role=role)
    assert (
        _patch(
            client, AGENT_A, "whatsapp", {"settings": {"phone_number_id": WA_ID}}
        ).status_code
        == 200
    )


def test_other_organization_cannot_touch_this_agent(world):
    client = _client(world, org=ORG_B)
    assert (
        _patch(
            client, AGENT_A, "whatsapp", {"settings": {"phone_number_id": WA_ID}}
        ).status_code
        == 404
    )
    assert _rotate(client, AGENT_A, "sdk").status_code == 404
    assert client.get(f"/api/agents/{AGENT_A}/channels").status_code == 404


def test_other_organization_cannot_claim_a_routing_identifier(world):
    owner = _client(world, org=ORG_A)
    assert (
        _patch(
            owner, AGENT_A, "whatsapp", {"settings": {"phone_number_id": WA_ID}}
        ).status_code
        == 200
    )

    intruder = _client(world, org=ORG_B)
    response = _patch(
        intruder, AGENT_B, "whatsapp", {"settings": {"phone_number_id": WA_ID}}
    )
    assert response.status_code == 409

    voice = _patch(
        owner, AGENT_A, "voice", {"settings": {"phone_number": VOICE_NUMBER}}
    )
    assert voice.status_code == 200
    clash = _patch(
        intruder, AGENT_B, "voice", {"settings": {"phone_number": VOICE_NUMBER}}
    )
    assert clash.status_code == 409


# ───────────────────────── inbound path resolves what was configured ─────────────────────────


def _configure_everything(world):
    client = _client(world, org=ORG_A)
    assert (
        _patch(
            client,
            AGENT_A,
            "whatsapp",
            {"enabled": True, "settings": {"phone_number_id": WA_ID}},
        ).status_code
        == 200
    )
    assert (
        _patch(
            client,
            AGENT_A,
            "instagram",
            {"enabled": True, "settings": {"instagram_account_id": IG_ID}},
        ).status_code
        == 200
    )
    assert (
        _patch(
            client,
            AGENT_A,
            "voice",
            {"enabled": True, "settings": {"phone_number": VOICE_NUMBER}},
        ).status_code
        == 200
    )
    assert (
        _patch(
            client,
            AGENT_A,
            "email",
            {"enabled": True, "settings": {"inbound_address": INBOUND}},
        ).status_code
        == 200
    )
    sdk = _patch(client, AGENT_A, "sdk", {"enabled": True}).json()
    return sdk["one_time_secret"]["value"]


def test_configured_whatsapp_binding_is_resolved_by_meta_inbound(world):
    _configure_everything(world)
    parsed = ParsedInbound(
        channel="whatsapp", provider="meta", text="hi", to_address=WA_ID
    )
    binding = _run(omni_routes._resolve_binding(world.db, parsed))
    assert (
        binding is not None
        and binding.agent_id == AGENT_A
        and binding.organization_id == ORG_A
    )


def test_configured_instagram_binding_is_resolved(world):
    _configure_everything(world)
    parsed = ParsedInbound(
        channel="instagram", provider="meta_instagram", text="hi", to_address=IG_ID
    )
    binding = _run(omni_routes._resolve_binding(world.db, parsed))
    assert binding is not None and binding.agent_id == AGENT_A


def test_configured_email_binding_is_resolved(world):
    _configure_everything(world)
    parsed = ParsedInbound(
        channel="email", provider="email", text="hi", to_address=INBOUND
    )
    binding = _run(omni_routes._resolve_binding(world.db, parsed))
    assert binding is not None and binding.agent_id == AGENT_A


def test_configured_voice_number_is_resolved(world):
    _configure_everything(world)
    binding = _run(voice_routes._resolve_binding(world.db, VOICE_NUMBER))
    assert binding is not None and binding.agent_id == AGENT_A


def test_configured_sdk_binding_is_resolved_and_authenticated(world):
    secret = _configure_everything(world)
    parsed = ParsedInbound(
        channel="mobile", provider="sdk", text="hi", route_value=str(AGENT_A)
    )
    binding = _run(omni_routes._resolve_binding(world.db, parsed))
    assert binding is not None and binding.agent_id == AGENT_A

    body = json.dumps({"text": "hi", "agent_id": str(AGENT_A)}).encode()
    good = SimpleNamespace(
        headers={omni_routes.SDK_SIGNATURE_HEADER: _sdk_sig(secret, body)}
    )
    bad = SimpleNamespace(
        headers={omni_routes.SDK_SIGNATURE_HEADER: _sdk_sig("wrong", body)}
    )
    assert omni_routes._binding_request_is_authentic("sdk", binding, good, body)
    assert not omni_routes._binding_request_is_authentic("sdk", binding, bad, body)


def test_disabled_binding_is_not_resolved(world):
    _configure_everything(world)
    client = _client(world, org=ORG_A)
    assert _patch(client, AGENT_A, "whatsapp", {"enabled": False}).status_code == 200
    parsed = ParsedInbound(
        channel="whatsapp", provider="meta", text="hi", to_address=WA_ID
    )
    assert _run(omni_routes._resolve_binding(world.db, parsed)) is None


def test_other_organizations_number_does_not_resolve_to_this_agent(world):
    _configure_everything(world)
    parsed = ParsedInbound(
        channel="whatsapp", provider="meta", text="hi", to_address="000000000000"
    )
    assert _run(omni_routes._resolve_binding(world.db, parsed)) is None


def _run(coro):
    import asyncio

    return asyncio.run(coro)


def test_refused_change_leaves_the_saved_setting_untouched(world):
    client = _client(world, org=ORG_A)
    assert (
        _patch(
            client, AGENT_A, "whatsapp", {"settings": {"phone_number_id": WA_ID}}
        ).status_code
        == 200
    )

    # Clearing the number and turning the channel on in one request must be refused as a whole.
    refused = _patch(
        client,
        AGENT_A,
        "whatsapp",
        {"enabled": True, "settings": {"phone_number_id": None}},
    )
    assert refused.status_code == 422
    row = next(c for c in world.db.channels if c.channel == "whatsapp")
    assert row.configuration == {"phone_number_id": WA_ID}
    assert row.enabled is False
