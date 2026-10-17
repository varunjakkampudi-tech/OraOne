"""Twilio messaging (SMS and WhatsApp): inbound parsing, signed webhook flow and reply delivery.

Everything external is mocked. No test sends a request to Twilio.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from twilio.request_validator import RequestValidator

from app.api.omnichannel import routes as omni_routes
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.channels import adapters

AUTH_TOKEN = "twilio-test-token"
PUBLIC_BASE = "https://api.example.test"
ACCOUNT_SID = "AC00000000000000000000000000000000"
WEBHOOK_PATH = "/api/channels/twilio/inbound"
WEBHOOK_URL = PUBLIC_BASE + WEBHOOK_PATH


def _cfg(**overrides):
    base = {
        "twilio_account_sid": ACCOUNT_SID,
        "twilio_auth_token": AUTH_TOKEN,
        "twilio_phone_number": "+15550001111",
        "public_api_base_url": PUBLIC_BASE,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _sign(params: dict, token: str = AUTH_TOKEN, url: str = WEBHOOK_URL) -> str:
    return RequestValidator(token).compute_signature(url, params)


WHATSAPP_FORM = {
    "From": "whatsapp:+447700900123",
    "To": "whatsapp:+15550001111",
    "Body": "  Do you deliver to Leeds?  ",
    "ProfileName": "Ada",
    "MessageSid": "SM0001",
}


# ── inbound parsing ──────────────────────────────────────────────────────────


def test_whatsapp_message_is_parsed_with_profile_name_and_prefixed_reply_address():
    parsed = adapters.TwilioMessagingAdapter().parse(
        form=WHATSAPP_FORM, json=None, headers={}, params={}
    )
    assert parsed.channel == "whatsapp"
    assert parsed.provider == "twilio"
    assert parsed.text == "Do you deliver to Leeds?"
    assert parsed.to_address == "+15550001111"
    assert parsed.phone == "+447700900123"
    assert parsed.name == "Ada"
    assert parsed.reply_to == "whatsapp:+447700900123"
    assert parsed.external_thread_id == "SM0001"


def test_sms_message_is_parsed_as_sms_and_ignores_profile_name():
    form = {
        "From": "+447700900123",
        "To": "+15550001111",
        "Body": "hi",
        "ProfileName": "Ada",
    }
    parsed = adapters.TwilioMessagingAdapter().parse(
        form=form, json=None, headers={}, params={}
    )
    assert parsed.channel == "sms"
    assert parsed.name is None
    assert parsed.reply_to == "+447700900123"


@pytest.mark.parametrize(
    "form",
    [
        {"To": "+15550001111", "Body": "hi"},
        {"From": "+447700900123", "Body": "hi"},
        {},
    ],
)
def test_message_without_both_addresses_is_not_parsed(form):
    assert (
        adapters.TwilioMessagingAdapter().parse(
            form=form, json=None, headers={}, params={}
        )
        is None
    )


# ── outbound reply ───────────────────────────────────────────────────────────


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = "provider detail that must not be logged"


@pytest.fixture
def posted(monkeypatch):
    calls = []

    async def fake_post(self, url, data=None, auth=None, **_):
        calls.append({"url": url, "data": data, "auth": auth})
        return _Resp(201)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    return calls


@pytest.mark.asyncio
async def test_whatsapp_reply_is_sent_from_the_business_number_with_prefixes(
    monkeypatch, posted
):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())
    parsed = adapters.TwilioMessagingAdapter().parse(
        form=WHATSAPP_FORM, json=None, headers={}, params={}
    )
    binding = SimpleNamespace(phone_number=None)

    ok = await adapters.TwilioMessagingAdapter().send(
        binding=binding, parsed=parsed, text="Yes we do"
    )

    assert ok is True
    assert len(posted) == 1
    call = posted[0]
    assert (
        call["url"]
        == f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json"
    )
    assert call["auth"] == (ACCOUNT_SID, AUTH_TOKEN)
    assert call["data"] == {
        "From": "whatsapp:+15550001111",
        "To": "whatsapp:+447700900123",
        "Body": "Yes we do",
    }


@pytest.mark.asyncio
async def test_send_does_nothing_without_twilio_credentials(monkeypatch, posted):
    monkeypatch.setattr(
        adapters, "get_channels_config", lambda: _cfg(twilio_auth_token="")
    )
    parsed = adapters.TwilioMessagingAdapter().parse(
        form=WHATSAPP_FORM, json=None, headers={}, params={}
    )

    ok = await adapters.TwilioMessagingAdapter().send(
        binding=SimpleNamespace(), parsed=parsed, text="hi"
    )

    assert ok is False
    assert posted == []


@pytest.mark.asyncio
async def test_send_never_posts_an_empty_reply(monkeypatch, posted):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())
    parsed = adapters.TwilioMessagingAdapter().parse(
        form=WHATSAPP_FORM, json=None, headers={}, params={}
    )

    assert (
        await adapters.TwilioMessagingAdapter().send(
            binding=SimpleNamespace(), parsed=parsed, text=""
        )
        is False
    )
    assert posted == []


@pytest.mark.asyncio
async def test_provider_refusal_is_reported_as_failure(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def refuse(self, url, data=None, auth=None, **_):
        return _Resp(400)

    monkeypatch.setattr(httpx.AsyncClient, "post", refuse)
    parsed = adapters.TwilioMessagingAdapter().parse(
        form=WHATSAPP_FORM, json=None, headers={}, params={}
    )

    assert (
        await adapters.TwilioMessagingAdapter().send(
            binding=SimpleNamespace(), parsed=parsed, text="hi"
        )
        is False
    )


@pytest.mark.asyncio
async def test_network_error_is_reported_as_failure_not_raised(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def unreachable(self, url, data=None, auth=None, **_):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx.AsyncClient, "post", unreachable)
    parsed = adapters.TwilioMessagingAdapter().parse(
        form=WHATSAPP_FORM, json=None, headers={}, params={}
    )

    assert (
        await adapters.TwilioMessagingAdapter().send(
            binding=SimpleNamespace(), parsed=parsed, text="hi"
        )
        is False
    )


# ── signed webhook route ─────────────────────────────────────────────────────


@pytest.fixture
def harness(monkeypatch):
    """Route-level harness: real signature check, mocked binding, agent and database."""
    cfg = _cfg()
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    monkeypatch.setattr(adapters, "get_channels_config", lambda: cfg)

    state = SimpleNamespace(bindings=[], inbound=[], replies=[], sent=[], commits=0)
    binding = SimpleNamespace(
        organization_id="org-a", agent_id="agent-a", project_id=None, configuration={}
    )

    async def fake_resolve(db, parsed):
        state.bindings.append(parsed.to_address)
        return binding if parsed.to_address == "+15550001111" else None

    async def fake_handle(db, msg):
        state.inbound.append(msg)
        return state.reply

    async def fake_send(self, *, binding, parsed, text):
        state.sent.append({"to": parsed.reply_to, "text": text})
        return True

    class _DB:
        async def commit(self):
            state.commits += 1

    state.reply = SimpleNamespace(
        handled=True,
        text="Yes we do",
        conversation_id=None,
        grounded=True,
        confidence=0.9,
    )
    monkeypatch.setattr(omni_routes, "_resolve_binding", fake_resolve)
    monkeypatch.setattr(omnichannel_service, "handle_inbound", fake_handle)
    monkeypatch.setattr(adapters.TwilioMessagingAdapter, "send", fake_send)

    app = FastAPI()
    app.include_router(omni_routes.router)
    app.dependency_overrides[get_db] = lambda: _DB()
    state.client = TestClient(app)
    return state


def _post_signed(client, form, *, token=AUTH_TOKEN):
    return client.post(
        WEBHOOK_PATH, data=form, headers={"X-Twilio-Signature": _sign(form, token)}
    )


def test_signed_whatsapp_message_reaches_the_bound_agent_and_is_answered(harness):
    response = _post_signed(harness.client, WHATSAPP_FORM)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Response></Response>" in response.text
    assert len(harness.inbound) == 1
    msg = harness.inbound[0]
    assert msg.channel == "whatsapp"
    assert msg.organization_id == "org-a"
    assert msg.agent_id == "agent-a"
    assert msg.text == "Do you deliver to Leeds?"
    assert harness.sent == [{"to": "whatsapp:+447700900123", "text": "Yes we do"}]
    assert harness.commits == 1


def test_wrong_auth_token_signature_never_reaches_the_agent(harness):
    response = _post_signed(harness.client, WHATSAPP_FORM, token="some-other-token")

    assert response.status_code == 401
    assert harness.inbound == []
    assert harness.sent == []


def test_signature_for_a_different_body_is_rejected(harness):
    signature = _sign(WHATSAPP_FORM)
    tampered = {**WHATSAPP_FORM, "Body": "transfer everything"}
    response = harness.client.post(
        WEBHOOK_PATH, data=tampered, headers={"X-Twilio-Signature": signature}
    )

    assert response.status_code == 401
    assert harness.inbound == []


def test_message_to_an_unbound_number_is_acknowledged_without_an_agent(harness):
    form = {**WHATSAPP_FORM, "To": "whatsapp:+15559998888"}
    response = _post_signed(harness.client, form)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": "no agent bound"}
    assert harness.inbound == []
    assert harness.sent == []


def test_empty_message_body_is_skipped_before_the_agent_runs(harness):
    form = {**WHATSAPP_FORM, "Body": "   "}
    response = _post_signed(harness.client, form)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": "no message"}
    assert harness.inbound == []


def test_agent_that_declines_to_answer_sends_nothing_but_still_acknowledges_twilio(
    harness,
):
    harness.reply = SimpleNamespace(
        handled=False, text="", conversation_id=None, grounded=False, confidence=0.0
    )
    response = _post_signed(harness.client, WHATSAPP_FORM)

    assert response.status_code == 200
    assert "<Response></Response>" in response.text
    assert len(harness.inbound) == 1
    assert harness.sent == []


def test_business_number_is_matched_with_and_without_plus_sign():
    """The binding lookup must accept the number stored with or without a leading '+'."""
    captured = {}

    class _DB:
        async def scalar(self, stmt):
            captured["sql"] = str(
                stmt.compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
            return None

    import asyncio

    parsed = adapters.TwilioMessagingAdapter().parse(
        form=WHATSAPP_FORM, json=None, headers={}, params={}
    )
    assert asyncio.run(omni_routes._resolve_binding(_DB(), parsed)) is None
    sql = captured["sql"]
    assert "'+15550001111'" in sql
    assert "'15550001111'" in sql
    assert "enabled" in sql
    assert "'whatsapp'" in sql


def test_missing_public_url_fails_closed_even_with_a_valid_signature(monkeypatch):
    cfg = _cfg(public_api_base_url="")
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    app = FastAPI()
    app.include_router(omni_routes.router)
    response = TestClient(app).post(
        WEBHOOK_PATH,
        data=WHATSAPP_FORM,
        headers={"X-Twilio-Signature": _sign(WHATSAPP_FORM)},
    )
    assert response.status_code == 401
