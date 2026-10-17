"""Instagram DMs (Meta Messenger Platform): signed webhook flow, account binding and replies.

Complements test_meta_instagram.py. Everything external is mocked; nothing reaches Meta.
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
from sqlalchemy.dialects import postgresql

from app.api.omnichannel import routes as omni_routes
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.channels import adapters

APP_SECRET = "meta-app-secret"
VERIFY_TOKEN = "meta-verify-token"
IG_TOKEN = "ig-page-token"
IG_ACCOUNT = "17841400000000000"
WEBHOOK_PATH = "/api/channels/meta_instagram/inbound"


def _cfg(**overrides):
    base = {
        "meta_whatsapp_access_token": "",
        "meta_whatsapp_app_secret": APP_SECRET,
        "meta_whatsapp_verify_token": VERIFY_TOKEN,
        "meta_instagram_access_token": IG_TOKEN,
        "public_api_base_url": "https://api.example.test",
        "twilio_auth_token": "",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _dm(
    text="Do you ship?",
    *,
    sender="ig-user-1",
    recipient=IG_ACCOUNT,
    echo=False,
    mid="m.1",
):
    message = {"mid": mid, "text": text}
    if echo:
        message["is_echo"] = True
    return {
        "object": "instagram",
        "entry": [
            {
                "id": IG_ACCOUNT,
                "messaging": [
                    {
                        "sender": {"id": sender},
                        "recipient": {"id": recipient},
                        "message": message,
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


# ── parsing ──────────────────────────────────────────────────────────────────


def test_attachment_only_dm_has_no_text_and_is_skipped():
    body = _dm()
    body["entry"][0]["messaging"][0]["message"] = {
        "mid": "m.2",
        "attachments": [{"type": "image"}],
    }
    assert (
        adapters.MetaInstagramAdapter().parse(form={}, json=body, headers={}, params={})
        is None
    )


def test_dm_without_a_recipient_account_is_skipped():
    body = _dm(recipient="")
    assert (
        adapters.MetaInstagramAdapter().parse(form={}, json=body, headers={}, params={})
        is None
    )


def test_parsed_dm_keeps_the_message_id_and_routes_replies_to_the_sender():
    parsed = adapters.MetaInstagramAdapter().parse(
        form={}, json=_dm(mid="m.9"), headers={}, params={}
    )
    assert parsed.channel == "instagram"
    assert parsed.provider == "meta_instagram"
    assert parsed.to_address == IG_ACCOUNT
    assert parsed.reply_to == "ig-user-1"
    assert parsed.meta == {"message_id": "m.9"}


# ── outbound reply ───────────────────────────────────────────────────────────


@pytest.fixture
def posted(monkeypatch):
    calls = []

    async def fake_post(self, url, headers=None, json=None, **_):
        calls.append({"url": url, "headers": headers, "json": json})
        return _Resp(200)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    return calls


@pytest.mark.asyncio
async def test_reply_is_posted_to_the_sender_with_the_page_token(monkeypatch, posted):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())
    parsed = adapters.MetaInstagramAdapter().parse(
        form={}, json=_dm(), headers={}, params={}
    )

    ok = await adapters.MetaInstagramAdapter().send(
        binding=SimpleNamespace(), parsed=parsed, text="Yes, we ship."
    )

    assert ok is True
    assert posted == [
        {
            "url": "https://graph.facebook.com/v21.0/me/messages",
            "headers": {"Authorization": f"Bearer {IG_TOKEN}"},
            "json": {
                "recipient": {"id": "ig-user-1"},
                "message": {"text": "Yes, we ship."},
            },
        }
    ]


@pytest.mark.asyncio
async def test_empty_reply_is_never_sent(monkeypatch, posted):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())
    parsed = adapters.MetaInstagramAdapter().parse(
        form={}, json=_dm(), headers={}, params={}
    )

    assert (
        await adapters.MetaInstagramAdapter().send(
            binding=SimpleNamespace(), parsed=parsed, text=""
        )
        is False
    )
    assert posted == []


@pytest.mark.asyncio
async def test_meta_error_status_is_reported_as_failure(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def rejected(self, *a, **k):
        return _Resp(403)

    monkeypatch.setattr(httpx.AsyncClient, "post", rejected)
    parsed = adapters.MetaInstagramAdapter().parse(
        form={}, json=_dm(), headers={}, params={}
    )

    assert (
        await adapters.MetaInstagramAdapter().send(
            binding=SimpleNamespace(), parsed=parsed, text="hi"
        )
        is False
    )


@pytest.mark.asyncio
async def test_transport_error_is_reported_as_failure_not_raised(monkeypatch):
    monkeypatch.setattr(adapters, "get_channels_config", lambda: _cfg())

    async def unreachable(self, *a, **k):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(httpx.AsyncClient, "post", unreachable)
    parsed = adapters.MetaInstagramAdapter().parse(
        form={}, json=_dm(), headers={}, params={}
    )

    assert (
        await adapters.MetaInstagramAdapter().send(
            binding=SimpleNamespace(), parsed=parsed, text="hi"
        )
        is False
    )


# ── signed webhook route ─────────────────────────────────────────────────────


@pytest.fixture
def harness(monkeypatch):
    cfg = _cfg()
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    monkeypatch.setattr(adapters, "get_channels_config", lambda: cfg)

    state = SimpleNamespace(resolved=[], inbound=[], posts=[], commits=0)
    state.binding = SimpleNamespace(
        organization_id="org-ig",
        agent_id="agent-ig",
        project_id=None,
        configuration={"instagram_account_id": IG_ACCOUNT},
    )
    state.reply = SimpleNamespace(
        handled=True,
        text="We ship worldwide.",
        conversation_id=None,
        grounded=True,
        confidence=0.7,
    )

    async def fake_resolve(db, parsed):
        state.resolved.append(parsed.to_address)
        return state.binding if parsed.to_address == IG_ACCOUNT else None

    async def fake_handle(db, msg):
        state.inbound.append(msg)
        return state.reply

    async def fake_post(self, url, headers=None, json=None, **_):
        state.posts.append({"url": url, "json": json})
        return _Resp(200)

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


def _post(client, body, *, secret=APP_SECRET):
    raw = json.dumps(body).encode()
    return client.post(
        WEBHOOK_PATH,
        content=raw,
        headers={
            "content-type": "application/json",
            "x-hub-signature-256": _sign(raw, secret),
        },
    )


def test_signed_dm_is_answered_for_the_bound_instagram_account(harness):
    response = _post(harness.client, _dm("Do you ship?"))

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(harness.inbound) == 1
    msg = harness.inbound[0]
    assert msg.channel == "instagram"
    assert msg.organization_id == "org-ig"
    assert msg.agent_id == "agent-ig"
    assert msg.external_id == "ig-user-1"
    assert harness.posts == [
        {
            "url": "https://graph.facebook.com/v21.0/me/messages",
            "json": {
                "recipient": {"id": "ig-user-1"},
                "message": {"text": "We ship worldwide."},
            },
        }
    ]
    assert harness.commits == 1


def test_dm_to_an_account_no_agent_is_bound_to_is_skipped(harness):
    response = _post(harness.client, _dm(recipient="99999"))

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": "no agent bound"}
    assert harness.inbound == []
    assert harness.posts == []


def test_echo_of_our_own_reply_never_triggers_another_answer(harness):
    response = _post(harness.client, _dm("We ship worldwide.", echo=True))

    assert response.status_code == 200
    assert response.json() == {"ok": True, "skipped": "no message"}
    assert harness.inbound == []
    assert harness.posts == []


def test_forged_dm_signature_is_rejected_before_routing(harness):
    response = _post(harness.client, _dm(), secret="attacker")

    assert response.status_code == 401
    assert harness.resolved == []
    assert harness.posts == []


def test_unhandled_reply_is_not_sent(harness):
    harness.reply = SimpleNamespace(
        handled=False, text="", conversation_id=None, grounded=False, confidence=0.0
    )
    response = _post(harness.client, _dm())

    assert response.status_code == 200
    assert len(harness.inbound) == 1
    assert harness.posts == []


def test_instagram_account_binding_matches_the_stored_account_id():
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

    parsed = adapters.MetaInstagramAdapter().parse(
        form={}, json=_dm(), headers={}, params={}
    )
    assert asyncio.run(omni_routes._resolve_binding(_DB(), parsed)) is None
    assert "instagram_account_id" in captured["sql"]
    assert IG_ACCOUNT in captured["sql"]
    assert "'instagram'" in captured["sql"]


def test_handshake_with_the_shared_verify_token_is_accepted(harness):
    response = harness.client.get(
        "/api/channels/meta_instagram/inbound",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "101",
        },
    )
    assert response.status_code == 200
    assert response.text == "101"


def test_handshake_with_a_wrong_token_is_refused(harness):
    response = harness.client.get(
        "/api/channels/meta_instagram/inbound",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "nope",
            "hub.challenge": "101",
        },
    )
    assert response.status_code == 403
