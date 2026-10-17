"""Meta WhatsApp Cloud API: signed webhook flow, binding, reply delivery and handshake refusals.

Complements test_meta_whatsapp.py (parsing and signature primitives). Everything external is
mocked; nothing reaches Meta.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.omnichannel import routes as omni_routes
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.channels import adapters

APP_SECRET = "meta-app-secret"
VERIFY_TOKEN = "meta-verify-token"
ACCESS_TOKEN = "meta-access-token"
WEBHOOK_PATH = "/api/channels/meta/inbound"


def _cfg(**overrides):
    base = {
        "meta_whatsapp_access_token": ACCESS_TOKEN,
        "meta_whatsapp_app_secret": APP_SECRET,
        "meta_whatsapp_verify_token": VERIFY_TOKEN,
        "meta_instagram_access_token": "",
        "public_api_base_url": "https://api.example.test",
        "twilio_auth_token": "",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _payload(text="Need a quote", msg_type="text", phone_number_id="1000001"):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": phone_number_id,
                            },
                            "contacts": [
                                {"profile": {"name": "Ada"}, "wa_id": "447700900123"}
                            ],
                            "messages": [
                                {
                                    "from": "447700900123",
                                    "id": "wamid.1",
                                    "type": msg_type,
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.fixture
def harness(monkeypatch):
    cfg = _cfg()
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    monkeypatch.setattr(adapters, "get_channels_config", lambda: cfg)

    state = SimpleNamespace(
        resolved=[],
        inbound=[],
        posts=[],
        commits=0,
        binding=SimpleNamespace(
            organization_id="org-a",
            agent_id="agent-a",
            project_id=None,
            configuration={"phone_number_id": "1000001"},
        ),
        reply=SimpleNamespace(
            handled=True,
            text="We can help.",
            conversation_id=None,
            grounded=True,
            confidence=0.8,
        ),
        post_status=200,
    )

    async def fake_resolve(db, parsed):
        state.resolved.append(parsed.to_address)
        return state.binding if parsed.to_address == "1000001" else None

    async def fake_handle(db, msg):
        state.inbound.append(msg)
        return state.reply

    async def fake_post(self, url, headers=None, json=None, **_):
        state.posts.append({"url": url, "headers": headers, "json": json})
        return _Resp(state.post_status)

    class _DB:
        async def commit(self):
            state.commits += 1

    monkeypatch.setattr(omni_routes, "_resolve_binding", fake_resolve)
    monkeypatch.setattr(omnichannel_service, "handle_inbound", fake_handle)
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    app = FastAPI()
    app.include_router(omni_routes.router)
    app.dependency_overrides[get_db] = lambda: _DB()
    state.client = TestClient(app)
    return state


def _post(client, body: dict, *, secret: str = APP_SECRET):
    raw = json.dumps(body).encode()
    return client.post(
        WEBHOOK_PATH,
        content=raw,
        headers={
            "content-type": "application/json",
            "x-hub-signature-256": _sign(raw, secret),
        },
    )


# ── signed inbound flow ──────────────────────────────────────────────────────


def test_signed_message_is_answered_once_on_the_bound_phone_number(harness):
    response = _post(harness.client, _payload("Need a quote"))

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(harness.inbound) == 1
    msg = harness.inbound[0]
    assert msg.channel == "whatsapp"
    assert msg.organization_id == "org-a"
    assert msg.agent_id == "agent-a"
    assert msg.text == "Need a quote"
    assert len(harness.posts) == 1
    post = harness.posts[0]
    assert post["url"].endswith("/1000001/messages")
    assert post["headers"] == {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    assert post["json"]["to"] == "447700900123"
    assert post["json"]["text"] == {"body": "We can help."}
    assert harness.commits == 1


def test_message_to_an_unbound_phone_number_is_skipped_and_nothing_is_sent(harness):
    response = _post(harness.client, _payload(phone_number_id="9999999"))

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": "no agent bound"}
    assert harness.inbound == []
    assert harness.posts == []


def test_unhandled_reply_is_not_sent_back_to_the_customer(harness):
    harness.reply = SimpleNamespace(
        handled=False, text="", conversation_id=None, grounded=False, confidence=0.0
    )
    response = _post(harness.client, _payload())

    assert response.status_code == 200
    assert len(harness.inbound) == 1
    assert harness.posts == []


def test_status_callback_is_acknowledged_without_touching_the_agent(harness):
    body = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {"value": {"statuses": [{"id": "wamid.1", "status": "read"}]}}
                ]
            }
        ],
    }
    response = _post(harness.client, body)

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": "no message"}
    assert harness.inbound == []


def test_image_message_is_skipped_until_media_is_supported(harness):
    response = _post(harness.client, _payload(msg_type="image"))

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": "no message"}
    assert harness.inbound == []


def test_forged_signature_is_rejected_before_any_lookup(harness):
    response = _post(harness.client, _payload(), secret="attacker-secret")

    assert response.status_code == 401
    assert harness.resolved == []
    assert harness.inbound == []
    assert harness.posts == []


def test_signed_request_with_a_non_json_body_is_skipped_safely(harness):
    raw = b"{not json"
    response = harness.client.post(
        WEBHOOK_PATH,
        content=raw,
        headers={"content-type": "application/json", "x-hub-signature-256": _sign(raw)},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": "no message"}
    assert harness.inbound == []


# ── reply delivery edge cases ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reply_is_refused_when_the_customer_address_is_missing(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def must_not_post(self, *a, **k):
        raise AssertionError("no request without a recipient")

    monkeypatch.setattr(httpx.AsyncClient, "post", must_not_post)
    parsed = adapters.ParsedInbound(
        channel="whatsapp", provider="meta", text="hi", to_address="1000001"
    )
    binding = SimpleNamespace(configuration={"phone_number_id": "1000001"})

    assert (
        await adapters.MetaWhatsAppAdapter().send(
            binding=binding, parsed=parsed, text="reply"
        )
        is False
    )


@pytest.mark.asyncio
async def test_reply_is_refused_when_no_phone_number_id_is_known(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def must_not_post(self, *a, **k):
        raise AssertionError("no request without a sending number")

    monkeypatch.setattr(httpx.AsyncClient, "post", must_not_post)
    parsed = adapters.ParsedInbound(
        channel="whatsapp", provider="meta", text="hi", reply_to="447700900123"
    )

    assert (
        await adapters.MetaWhatsAppAdapter().send(
            binding=SimpleNamespace(configuration={}), parsed=parsed, text="x"
        )
        is False
    )


@pytest.mark.asyncio
async def test_empty_reply_is_never_posted(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def must_not_post(self, *a, **k):
        raise AssertionError("empty replies are not sent")

    monkeypatch.setattr(httpx.AsyncClient, "post", must_not_post)
    parsed = adapters.ParsedInbound(
        channel="whatsapp", provider="meta", text="hi", reply_to="447700900123"
    )

    assert (
        await adapters.MetaWhatsAppAdapter().send(
            binding=SimpleNamespace(configuration={"phone_number_id": "1"}),
            parsed=parsed,
            text="",
        )
        is False
    )


@pytest.mark.asyncio
async def test_redirect_style_status_is_treated_as_a_failed_send(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def redirect(self, *a, **k):
        return _Resp(302)

    monkeypatch.setattr(httpx.AsyncClient, "post", redirect)
    parsed = adapters.ParsedInbound(
        channel="whatsapp", provider="meta", text="hi", reply_to="447700900123"
    )

    assert (
        await adapters.MetaWhatsAppAdapter().send(
            binding=SimpleNamespace(configuration={"phone_number_id": "1"}),
            parsed=parsed,
            text="x",
        )
        is False
    )


@pytest.mark.asyncio
async def test_transport_error_is_reported_without_raising(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def unreachable(self, *a, **k):
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(httpx.AsyncClient, "post", unreachable)
    parsed = adapters.ParsedInbound(
        channel="whatsapp", provider="meta", text="hi", reply_to="447700900123"
    )

    assert (
        await adapters.MetaWhatsAppAdapter().send(
            binding=SimpleNamespace(configuration={"phone_number_id": "1"}),
            parsed=parsed,
            text="x",
        )
        is False
    )


# ── Meta handshake ───────────────────────────────────────────────────────────


def test_handshake_fails_closed_when_no_verify_token_is_configured(monkeypatch):
    monkeypatch.setattr(
        omni_routes, "get_channels_config", lambda: _cfg(meta_whatsapp_verify_token="")
    )
    app = FastAPI()
    app.include_router(omni_routes.router)
    response = TestClient(app).get(
        WEBHOOK_PATH,
        params={"hub.mode": "subscribe", "hub.verify_token": "", "hub.challenge": "42"},
    )
    assert response.status_code == 403


def test_handshake_rejects_any_mode_other_than_subscribe(harness):
    response = harness.client.get(
        WEBHOOK_PATH,
        params={
            "hub.mode": "unsubscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "42",
        },
    )
    assert response.status_code == 403


def test_handshake_with_the_right_token_returns_plain_text_challenge(harness):
    response = harness.client.get(
        WEBHOOK_PATH,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "777",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "777"
