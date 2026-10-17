"""Meta Instagram DM adapter: parsing, webhook signature, handshake and reply path."""

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
IG_ACCESS_TOKEN = "test-ig-access-token"
IG_ACCOUNT_ID = "17841400000000001"
SENDER_ID = "9988776655"


def _cfg(**overrides):
    base = {
        "meta_instagram_access_token": IG_ACCESS_TOKEN,
        "meta_whatsapp_app_secret": APP_SECRET,
        "meta_whatsapp_verify_token": VERIFY_TOKEN,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _event(
    text="Hello",
    mid="m_1",
    is_echo=None,
    sender=SENDER_ID,
    recipient=IG_ACCOUNT_ID,
    message=None,
):
    if message is None:
        message = {"mid": mid, "text": text}
        if is_echo is not None:
            message["is_echo"] = is_echo
    return {
        "sender": {"id": sender},
        "recipient": {"id": recipient},
        "timestamp": 1700000000,
        "message": message,
    }


def _inbound(events=None, obj="instagram"):
    return {
        "object": obj,
        "entry": [
            {"id": IG_ACCOUNT_ID, "time": 1700000000, "messaging": events or [_event()]}
        ],
    }


def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ── parsing ──────────────────────────────────────────────────────────────────


def test_parse_text_dm_routes_by_instagram_account_id():
    parsed = adapters.MetaInstagramAdapter().parse(
        form={}, json=_inbound(), headers={}, params={}
    )
    assert parsed is not None
    assert parsed.channel == "instagram"
    assert parsed.provider == "meta_instagram"
    assert parsed.text == "Hello"
    assert parsed.to_address == IG_ACCOUNT_ID
    assert parsed.reply_to == SENDER_ID
    assert parsed.external_id == SENDER_ID
    assert parsed.meta == {"message_id": "m_1"}


def test_echo_of_our_own_reply_is_skipped():
    payload = _inbound([_event(text="Our reply", is_echo=True)])
    assert (
        adapters.MetaInstagramAdapter().parse(
            form={}, json=payload, headers={}, params={}
        )
        is None
    )


def test_echo_is_skipped_but_following_customer_dm_is_used():
    payload = _inbound(
        [
            _event(text="Our reply", is_echo=True),
            _event(text="Real question", mid="m_2"),
        ]
    )
    parsed = adapters.MetaInstagramAdapter().parse(
        form={}, json=payload, headers={}, params={}
    )
    assert parsed is not None
    assert parsed.text == "Real question"


def test_non_text_message_is_skipped():
    attachment_only = {
        "mid": "m_3",
        "attachments": [
            {"type": "image", "payload": {"url": "https://example.test/x.png"}}
        ],
    }
    payload = _inbound([_event(message=attachment_only)])
    assert (
        adapters.MetaInstagramAdapter().parse(
            form={}, json=payload, headers={}, params={}
        )
        is None
    )


def test_read_receipt_without_message_is_skipped():
    payload = _inbound(
        [
            {
                "sender": {"id": SENDER_ID},
                "recipient": {"id": IG_ACCOUNT_ID},
                "read": {"mid": "m_1"},
            }
        ]
    )
    assert (
        adapters.MetaInstagramAdapter().parse(
            form={}, json=payload, headers={}, params={}
        )
        is None
    )


def test_non_instagram_payload_is_ignored():
    parsed = adapters.MetaInstagramAdapter().parse(
        form={}, json=_inbound(obj="whatsapp_business_account"), headers={}, params={}
    )
    assert parsed is None


def test_meta_instagram_adapter_is_registered():
    assert adapters.get_adapter("meta_instagram") is not None
    assert "meta_instagram" in adapters.supported_providers()


# ── reply path ───────────────────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def _parsed():
    return adapters.MetaInstagramAdapter().parse(
        form={}, json=_inbound(), headers={}, params={}
    )


@pytest.mark.asyncio
async def test_send_posts_text_dm_with_bearer_token(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())
    sent = {}

    async def fake_post(self, url, headers=None, json=None, **_):
        sent.update(url=url, headers=headers, json=json)
        return _FakeResponse(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    binding = SimpleNamespace(configuration={"instagram_account_id": IG_ACCOUNT_ID})

    ok = await adapters.MetaInstagramAdapter().send(
        binding=binding, parsed=_parsed(), text="Hi there"
    )

    assert ok is True
    assert sent["url"] == "https://graph.facebook.com/v21.0/me/messages"
    assert sent["headers"] == {"Authorization": f"Bearer {IG_ACCESS_TOKEN}"}
    assert sent["json"] == {
        "recipient": {"id": SENDER_ID},
        "message": {"text": "Hi there"},
    }


@pytest.mark.asyncio
async def test_send_reports_failure_without_raising(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def fake_post(self, url, headers=None, json=None, **_):
        return _FakeResponse(400)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    binding = SimpleNamespace(configuration={})

    assert (
        await adapters.MetaInstagramAdapter().send(
            binding=binding, parsed=_parsed(), text="Hi"
        )
        is False
    )


@pytest.mark.asyncio
async def test_send_without_access_token_fails_closed(monkeypatch):
    monkeypatch.setattr(
        adapters, "get_channels_config", lambda: _cfg(meta_instagram_access_token="")
    )

    async def must_not_post(self, *a, **k):
        raise AssertionError("no request should be made without a token")

    monkeypatch.setattr(httpx.AsyncClient, "post", must_not_post)
    binding = SimpleNamespace(configuration={})

    assert (
        await adapters.MetaInstagramAdapter().send(
            binding=binding, parsed=_parsed(), text="Hi"
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


def test_handshake_echoes_challenge_when_verify_token_matches(client):
    response = client.get(
        "/api/channels/meta_instagram/inbound",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "54321",
        },
    )
    assert response.status_code == 200
    assert response.text == "54321"


def test_handshake_rejects_wrong_verify_token(client):
    response = client.get(
        "/api/channels/meta_instagram/inbound",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "nope",
            "hub.challenge": "54321",
        },
    )
    assert response.status_code == 403


def test_inbound_rejects_unsigned_request_before_parsing(client):
    body = json.dumps(_inbound()).encode()
    response = client.post(
        "/api/channels/meta_instagram/inbound",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401


def test_inbound_rejects_bad_signature(client):
    body = json.dumps(_inbound()).encode()
    response = client.post(
        "/api/channels/meta_instagram/inbound",
        content=body,
        headers={
            "content-type": "application/json",
            "x-hub-signature-256": _sign(body, "wrong"),
        },
    )
    assert response.status_code == 401
