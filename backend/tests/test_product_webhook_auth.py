"""Inbound channel webhook authentication, Telegram path-token handling, dedupe and log hygiene.

SDK, email and Telegram inbound had no verification. These tests pin the fail-closed
behaviour: a missing or wrong secret is refused before any reply is generated.
Complements test_product_whatsapp.py and test_product_twilio.py. Nothing reaches a real
provider: outbound sends are counted by a patched httpx client.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.omnichannel import routes as omni_routes
from app.database.models.channel_inbound_receipt import ChannelInboundReceipt
from app.database.session import get_db
from app.services import omnichannel_service, visitor_service, workflow_triggers
from app.services.channels import adapters

TEST_PROJECT_ID = uuid.uuid4()

SDK_SECRET = "sdk-binding-secret"
EMAIL_SECRET = "email-provider-secret"
TG_SECRET = "telegram-webhook-secret"
BOT_TOKEN = "123456:bot-token-value"
ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
AGENT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
INBOUND_ADDR = "support@inbound.example.test"

SDK_PATH = "/api/channels/sdk/inbound"
EMAIL_PATH = "/api/channels/email/inbound"
TG_PATH = f"/api/channels/telegram/{BOT_TOKEN}/inbound"


def _cfg(**overrides):
    base = {
        "meta_whatsapp_access_token": "",
        "meta_whatsapp_app_secret": "",
        "meta_whatsapp_verify_token": "",
        "meta_instagram_access_token": "",
        "public_api_base_url": "https://api.example.test",
        "twilio_auth_token": "",
        "twilio_account_sid": "",
        "email_inbound_secret": EMAIL_SECRET,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class _Resp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class _DB:
    async def commit(self):
        return None


@pytest.fixture
def env(monkeypatch):
    cfg = _cfg()
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    monkeypatch.setattr(adapters, "get_channels_config", lambda: cfg)

    bindings = {
        "sdk": SimpleNamespace(
            organization_id=ORG_ID,
            agent_id=AGENT_ID,
            project_id=None,
            configuration={"sdk_secret": SDK_SECRET},
        ),
        "email": SimpleNamespace(
            organization_id=ORG_ID,
            agent_id=AGENT_ID,
            project_id=None,
            configuration={"inbound_address": INBOUND_ADDR},
        ),
        "telegram": SimpleNamespace(
            organization_id=ORG_ID,
            agent_id=AGENT_ID,
            project_id=None,
            configuration={
                "bot_token": BOT_TOKEN,
                "telegram_webhook_secret": TG_SECRET,
            },
        ),
    }
    state = SimpleNamespace(
        cfg=cfg, bindings=bindings, resolved=[], inbound=[], sends=[]
    )
    state.reply = SimpleNamespace(
        handled=True,
        text="Here is the answer.",
        conversation_id=None,
        grounded=True,
        confidence=0.9,
    )

    async def fake_resolve(db, parsed):
        state.resolved.append((parsed.provider, parsed.bot_token))
        if parsed.provider == "sdk" and parsed.route_value == str(AGENT_ID):
            return bindings["sdk"]
        if parsed.provider == "email" and parsed.to_address == INBOUND_ADDR:
            return bindings["email"]
        if parsed.provider == "telegram" and parsed.bot_token == BOT_TOKEN:
            return bindings["telegram"]
        return None

    async def fake_handle(db, msg):
        state.inbound.append(msg)
        return state.reply

    async def fake_post(self, url, **kwargs):
        state.sends.append(url)
        return _Resp(200)

    monkeypatch.setattr(omni_routes, "_resolve_binding", fake_resolve)
    monkeypatch.setattr(omnichannel_service, "handle_inbound", fake_handle)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    app = FastAPI()
    app.include_router(omni_routes.router)
    app.dependency_overrides[get_db] = lambda: _DB()
    state.client = TestClient(app)
    return state


def _sdk_body(text="Hi from the app") -> bytes:
    return json.dumps(
        {
            "text": text,
            "agent_id": str(AGENT_ID),
            "session_id": "sess-1",
            "user": {"id": "device-7", "name": "Ada"},
        }
    ).encode()


def _email_body(sender="Customer@Example.com") -> bytes:
    return json.dumps(
        {
            "from": sender,
            "to": INBOUND_ADDR,
            "subject": "Pricing",
            "text": "How much is the pro plan?",
            "Message-Id": "<abc123@mail.example.test>",
        }
    ).encode()


def _tg_body(update_id=42, text="Hello bot") -> bytes:
    return json.dumps(
        {
            "update_id": update_id,
            "message": {
                "text": text,
                "chat": {"id": 555},
                "from": {"id": 9, "first_name": "Ada", "username": "ada"},
            },
        }
    ).encode()


JSON_HEADERS = {"content-type": "application/json"}


# ── SDK: per-binding HMAC signature ─────────────────────────────────────────


def test_sdk_request_without_signature_is_rejected(env):
    response = env.client.post(SDK_PATH, content=_sdk_body(), headers=JSON_HEADERS)

    assert response.status_code == 401
    assert env.inbound == []
    assert env.sends == []


def test_sdk_request_with_wrong_secret_is_rejected(env):
    body = _sdk_body()
    response = env.client.post(
        SDK_PATH,
        content=body,
        headers={**JSON_HEADERS, "x-oraone-signature": _sign(body, "attacker-secret")},
    )

    assert response.status_code == 401
    assert env.inbound == []


def test_sdk_signature_over_a_different_body_is_rejected(env):
    signed = _sdk_body("original")
    response = env.client.post(
        SDK_PATH,
        content=_sdk_body("tampered"),
        headers={**JSON_HEADERS, "x-oraone-signature": _sign(signed, SDK_SECRET)},
    )

    assert response.status_code == 401
    assert env.inbound == []


def test_sdk_binding_without_a_secret_fails_closed(env):
    env.bindings["sdk"].configuration = {}
    body = _sdk_body()
    response = env.client.post(
        SDK_PATH,
        content=body,
        headers={**JSON_HEADERS, "x-oraone-signature": _sign(body, "")},
    )

    assert response.status_code == 401
    assert env.inbound == []


def test_sdk_request_with_correct_secret_is_answered_inline(env):
    body = _sdk_body()
    response = env.client.post(
        SDK_PATH,
        content=body,
        headers={**JSON_HEADERS, "x-oraone-signature": _sign(body, SDK_SECRET)},
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Here is the answer."
    assert len(env.inbound) == 1
    assert env.inbound[0].channel == "mobile"
    assert env.inbound[0].agent_id == AGENT_ID


# ── Email: deployment-wide shared secret ────────────────────────────────────


def test_email_request_without_the_secret_is_rejected(env):
    response = env.client.post(EMAIL_PATH, content=_email_body(), headers=JSON_HEADERS)

    assert response.status_code == 401
    assert env.resolved == []
    assert env.inbound == []


def test_email_request_with_a_wrong_secret_is_rejected(env):
    response = env.client.post(
        EMAIL_PATH,
        content=_email_body(),
        headers={**JSON_HEADERS, "x-email-inbound-secret": "guessed"},
    )

    assert response.status_code == 401
    assert env.inbound == []


def test_email_refuses_everything_when_no_secret_is_configured(env):
    env.cfg.email_inbound_secret = ""
    response = env.client.post(
        EMAIL_PATH,
        content=_email_body(),
        headers={**JSON_HEADERS, "x-email-inbound-secret": ""},
    )

    assert response.status_code == 401
    assert env.inbound == []


def test_email_with_the_secret_is_routed_without_trusting_the_from_field(env):
    response = env.client.post(
        EMAIL_PATH,
        content=_email_body(),
        headers={**JSON_HEADERS, "x-email-inbound-secret": EMAIL_SECRET},
    )

    assert response.status_code == 200
    assert len(env.inbound) == 1
    msg = env.inbound[0]
    # The sender address is used only to key the thread and route the reply.
    assert msg.email is None
    assert msg.external_id == "customer@example.com"
    assert msg.agent_id == AGENT_ID


# ── Telegram: header secret, path token, no query token ─────────────────────


def test_telegram_request_without_the_header_is_rejected(env):
    response = env.client.post(TG_PATH, content=_tg_body(), headers=JSON_HEADERS)

    assert response.status_code == 401
    assert env.inbound == []
    assert env.sends == []


def test_telegram_request_with_a_wrong_header_is_rejected(env):
    response = env.client.post(
        TG_PATH,
        content=_tg_body(),
        headers={**JSON_HEADERS, "x-telegram-bot-api-secret-token": "guessed"},
    )

    assert response.status_code == 401
    assert env.inbound == []


def test_telegram_binding_without_a_webhook_secret_fails_closed(env):
    env.bindings["telegram"].configuration = {"bot_token": BOT_TOKEN}
    response = env.client.post(
        TG_PATH,
        content=_tg_body(),
        headers={**JSON_HEADERS, "x-telegram-bot-api-secret-token": ""},
    )

    assert response.status_code == 401
    assert env.inbound == []


def test_telegram_request_with_the_correct_header_is_answered(env):
    response = env.client.post(
        TG_PATH,
        content=_tg_body(),
        headers={**JSON_HEADERS, "x-telegram-bot-api-secret-token": TG_SECRET},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(env.inbound) == 1
    assert env.inbound[0].text == "Hello bot"
    assert any("api.telegram.org" in url for url in env.sends)


def test_telegram_token_in_the_query_string_is_not_used_for_routing(env):
    # The path token is wrong; the real token is only in the query string. It must not
    # select the binding, so the request is skipped even with a correct header.
    response = env.client.post(
        f"/api/channels/telegram/000000:wrong/inbound?token={BOT_TOKEN}",
        content=_tg_body(),
        headers={**JSON_HEADERS, "x-telegram-bot-api-secret-token": TG_SECRET},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": "no agent bound"}
    assert env.resolved == [("telegram", "000000:wrong")]
    assert env.inbound == []


def test_telegram_generic_route_with_query_token_is_not_served(env):
    response = env.client.post(
        f"/api/channels/telegram/inbound?token={BOT_TOKEN}",
        content=_tg_body(),
        headers={**JSON_HEADERS, "x-telegram-bot-api-secret-token": TG_SECRET},
    )

    assert response.status_code == 404
    assert env.resolved == []
    assert env.inbound == []


# ── Duplicate delivery: one turn, one reply ─────────────────────────────────


class _Savepoint:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    """Enforces the receipt unique constraint the way Postgres would, per flush."""

    def __init__(self, receipts: set):
        self.receipts = receipts
        self._pending: list = []
        self.commits = 0

    async def scalar(self, *args, **kwargs):
        return None

    def add(self, obj):
        self._pending.append(obj)

    def begin_nested(self):
        return _Savepoint()

    async def flush(self):
        pending, self._pending = self._pending, []
        for obj in pending:
            if isinstance(obj, ChannelInboundReceipt):
                key = (obj.agent_id, obj.message_key)
                if key in self.receipts:
                    raise IntegrityError(
                        "INSERT channel_inbound_receipts", {}, Exception("duplicate")
                    )
                self.receipts.add(key)

    async def commit(self):
        self.commits += 1


@pytest.fixture
def dedupe_env(env, monkeypatch):
    """Real handle_inbound pipeline; only the model, storage and thread lookups are stubbed."""
    answers: list[str] = []
    receipts: set = set()

    async def fake_answer(session, text, org_id, **kwargs):
        answers.append(text)
        return {
            "answer": f"answer {len(answers)}",
            "grounded": True,
            "confidence": 0.9,
            "model": "stub",
        }

    async def fake_upsert_profile(session, **kwargs):
        return SimpleNamespace(id=uuid.uuid4())

    async def fake_thread(session, msg, profile, channel_enum):
        return SimpleNamespace(id=uuid.uuid4(), last_message_at=None)

    async def fake_fire(session, **kwargs):
        return None

    monkeypatch.setattr(omnichannel_service, "answer_query", fake_answer)
    monkeypatch.setattr(omnichannel_service, "_find_or_create_thread", fake_thread)
    monkeypatch.setattr(visitor_service, "upsert_profile", fake_upsert_profile)
    monkeypatch.setattr(visitor_service, "link_conversation", lambda *a, **k: None)
    monkeypatch.setattr(visitor_service, "build_memory_digest", lambda *a, **k: "")
    monkeypatch.setattr(visitor_service, "append_memory", lambda *a, **k: None)
    monkeypatch.setattr(workflow_triggers, "fire_message_received", fake_fire)

    # Use the real handle_inbound, not the stub installed by the env fixture.
    monkeypatch.setattr(omnichannel_service, "handle_inbound", _REAL_HANDLE_INBOUND)

    app = FastAPI()
    app.include_router(omni_routes.router)
    app.dependency_overrides[get_db] = lambda: _FakeSession(receipts)
    env.client = TestClient(app)
    env.answers = answers
    env.receipts = receipts
    return env


_REAL_HANDLE_INBOUND = omnichannel_service.handle_inbound


def _tg_post(client, update_id: int, text: str = "Hello bot"):
    return client.post(
        TG_PATH,
        content=_tg_body(update_id=update_id, text=text),
        headers={**JSON_HEADERS, "x-telegram-bot-api-secret-token": TG_SECRET},
    )


def test_redelivered_telegram_update_produces_one_reply(dedupe_env):
    first = _tg_post(dedupe_env.client, update_id=42)
    second = _tg_post(dedupe_env.client, update_id=42)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == {"ok": True}
    assert len(dedupe_env.answers) == 1
    telegram_sends = [u for u in dedupe_env.sends if "sendMessage" in u]
    assert len(telegram_sends) == 1
    assert len(dedupe_env.receipts) == 1


def test_a_new_update_id_is_still_answered(dedupe_env):
    _tg_post(dedupe_env.client, update_id=42)
    _tg_post(dedupe_env.client, update_id=43, text="Second question")

    assert len(dedupe_env.answers) == 2
    assert len([u for u in dedupe_env.sends if "sendMessage" in u]) == 2


# ── Log hygiene ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_twilio_failure_log_has_status_but_not_the_response_body(
    monkeypatch, caplog
):
    cfg = _cfg(twilio_account_sid="AC" + "0" * 32, twilio_auth_token="auth")
    monkeypatch.setattr(adapters, "get_channels_config", lambda: cfg)

    async def rejected(self, *a, **k):
        return _Resp(400, text="Invalid To number +15551234567")

    monkeypatch.setattr(httpx.AsyncClient, "post", rejected)
    parsed = adapters.ParsedInbound(
        channel="sms",
        provider="twilio",
        text="hi",
        to_address="+15550000000",
        reply_to="+15551234567",
    )
    binding = SimpleNamespace(configuration={}, phone_number=None)

    with caplog.at_level(logging.WARNING, logger="app.channels.adapters"):
        ok = await adapters.TwilioMessagingAdapter().send(
            binding=binding, parsed=parsed, text="reply"
        )

    assert ok is False
    assert "HTTP 400" in caplog.text
    assert "+1555" not in caplog.text


@pytest.mark.asyncio
async def test_email_reply_log_does_not_include_the_recipient(monkeypatch, caplog):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())
    parsed = adapters.ParsedInbound(
        channel="email", provider="email", text="hi", reply_to="victim@example.com"
    )

    with caplog.at_level(logging.INFO, logger="app.channels.adapters"):
        await adapters.EmailAdapter().send(
            binding=SimpleNamespace(configuration={}), parsed=parsed, text="x"
        )

    assert "victim@example.com" not in caplog.text


@pytest.mark.asyncio
async def test_telegram_transport_error_log_does_not_leak_the_bot_token(
    monkeypatch, caplog
):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def unreachable(self, url, **kwargs):
        raise httpx.ConnectError(f"failed for {url}")

    monkeypatch.setattr(httpx.AsyncClient, "post", unreachable)
    parsed = adapters.ParsedInbound(
        channel="telegram", provider="telegram", text="hi", reply_to="555"
    )
    binding = SimpleNamespace(configuration={"bot_token": BOT_TOKEN})

    with caplog.at_level(logging.WARNING, logger="app.channels.adapters"):
        ok = await adapters.TelegramAdapter().send(
            binding=binding, parsed=parsed, text="reply"
        )

    assert ok is False
    assert "bot-token-value" not in caplog.text
    assert "ConnectError" in caplog.text


@pytest.fixture(autouse=True)
def _default_project_for_tests(monkeypatch):
    """Customer paths resolve a project. These tests have no project rows, so
    the organization default is pinned to one fixed project."""
    from app.services import project_scope

    project = uuid.uuid4()

    async def _default(_session, _organization_id):
        return project

    monkeypatch.setattr(project_scope, "default_project_id", _default)
