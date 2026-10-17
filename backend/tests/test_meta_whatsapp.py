"""Meta WhatsApp Cloud API adapter: parsing, webhook signature, handshake and reply path."""

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
from app.services.channels import adapters

APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"
ACCESS_TOKEN = "test-access-token"


def _cfg(**overrides):
    base = {
        "meta_whatsapp_access_token": ACCESS_TOKEN,
        "meta_whatsapp_app_secret": APP_SECRET,
        "meta_whatsapp_verify_token": VERIFY_TOKEN,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _inbound(text="Hello", msg_type="text", phone_number_id="1000001"):
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


# ── parsing ──────────────────────────────────────────────────────────────────


def test_parse_text_message_routes_by_phone_number_id():
    parsed = adapters.MetaWhatsAppAdapter().parse(
        form={}, json=_inbound("Need a quote"), headers={}, params={}
    )
    assert parsed is not None
    assert parsed.channel == "whatsapp"
    assert parsed.provider == "meta"
    assert parsed.text == "Need a quote"
    assert parsed.to_address == "1000001"
    assert parsed.reply_to == "447700900123"
    assert parsed.name == "Ada"
    assert parsed.meta == {"message_id": "wamid.1"}


def test_status_callback_without_messages_is_skipped():
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}],
    }
    assert (
        adapters.MetaWhatsAppAdapter().parse(
            form={}, json=payload, headers={}, params={}
        )
        is None
    )


def test_non_text_message_is_skipped_until_supported():
    parsed = adapters.MetaWhatsAppAdapter().parse(
        form={}, json=_inbound(msg_type="image"), headers={}, params={}
    )
    assert parsed is None


def test_non_whatsapp_payload_is_ignored():
    parsed = adapters.MetaWhatsAppAdapter().parse(
        form={}, json={"object": "page"}, headers={}, params={}
    )
    assert parsed is None


def test_meta_adapter_is_registered():
    assert adapters.get_adapter("meta") is not None
    assert "meta" in adapters.supported_providers()


# ── signature ────────────────────────────────────────────────────────────────


def test_valid_signature_is_accepted():
    body = json.dumps(_inbound()).encode()
    assert adapters.verify_meta_signature(APP_SECRET, body, _sign(body))


def test_tampered_body_is_rejected():
    body = json.dumps(_inbound()).encode()
    assert not adapters.verify_meta_signature(APP_SECRET, body + b" ", _sign(body))


def test_wrong_secret_is_rejected():
    body = json.dumps(_inbound()).encode()
    assert not adapters.verify_meta_signature(APP_SECRET, body, _sign(body, "other"))


def test_missing_header_or_secret_fails_closed():
    body = b"{}"
    assert not adapters.verify_meta_signature(APP_SECRET, body, None)
    assert not adapters.verify_meta_signature(APP_SECRET, body, "md5=abc")
    assert not adapters.verify_meta_signature("", body, _sign(body, ""))


# ── reply path ───────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


@pytest.mark.asyncio
async def test_send_posts_text_reply_with_bearer_token(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())
    sent = {}

    async def fake_post(self, url, headers=None, json=None, **_):
        sent.update(url=url, headers=headers, json=json)
        return _FakeResponse(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    parsed = adapters.MetaWhatsAppAdapter().parse(
        form={}, json=_inbound(), headers={}, params={}
    )
    binding = SimpleNamespace(configuration={"phone_number_id": "1000001"})

    ok = await adapters.MetaWhatsAppAdapter().send(
        binding=binding, parsed=parsed, text="Hi Ada"
    )

    assert ok is True
    assert sent["url"].endswith("/1000001/messages")
    assert sent["headers"] == {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    assert sent["json"] == {
        "messaging_product": "whatsapp",
        "to": "447700900123",
        "type": "text",
        "text": {"body": "Hi Ada"},
    }


@pytest.mark.asyncio
async def test_send_reports_failure_without_raising(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def fake_post(self, url, headers=None, json=None, **_):
        return _FakeResponse(401)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    parsed = adapters.MetaWhatsAppAdapter().parse(
        form={}, json=_inbound(), headers={}, params={}
    )
    binding = SimpleNamespace(configuration={"phone_number_id": "1000001"})

    assert (
        await adapters.MetaWhatsAppAdapter().send(
            binding=binding, parsed=parsed, text="Hi"
        )
        is False
    )


@pytest.mark.asyncio
async def test_send_without_access_token_does_nothing(monkeypatch):
    monkeypatch.setattr(
        adapters, "get_channels_config", lambda: _cfg(meta_whatsapp_access_token="")
    )

    async def must_not_post(self, *a, **k):
        raise AssertionError("no request should be made without a token")

    monkeypatch.setattr(httpx.AsyncClient, "post", must_not_post)
    parsed = adapters.MetaWhatsAppAdapter().parse(
        form={}, json=_inbound(), headers={}, params={}
    )
    binding = SimpleNamespace(configuration={"phone_number_id": "1000001"})

    assert (
        await adapters.MetaWhatsAppAdapter().send(
            binding=binding, parsed=parsed, text="Hi"
        )
        is False
    )


# ── webhook routes (no database touched) ─────────────────────────────────────


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: _cfg())
    app = FastAPI()
    app.include_router(omni_routes.router)
    return TestClient(app)


def test_handshake_echoes_challenge_when_token_matches(client):
    response = client.get(
        "/api/channels/meta/inbound",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 200
    assert response.text == "12345"


def test_handshake_rejects_wrong_token(client):
    response = client.get(
        "/api/channels/meta/inbound",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "nope",
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 403


def test_inbound_rejects_unsigned_request_before_parsing(client):
    body = json.dumps(_inbound()).encode()
    response = client.post(
        "/api/channels/meta/inbound",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401
