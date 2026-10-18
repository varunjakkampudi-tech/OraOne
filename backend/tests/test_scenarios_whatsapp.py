"""WhatsApp scenarios (Meta Cloud API): signed inbound, AI reply, opt-out, Graph outage, tenant routing.

Everything external is replaced: the channel binding lookup, the AI pipeline and the Graph
API POST. Nothing reaches Meta, and the webhook clock is not used.
"""

from __future__ import annotations

import hashlib
import hmac
import json as jsonlib
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.omnichannel import routes as omni_routes
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.channels import adapters
from scenario_support import ORG_A, ORG_B, FakeSession, channels_config

APP_SECRET = "scenario-meta-app-secret"
ACCESS_TOKEN = "scenario-wa-access-token"
WEBHOOK = "/api/channels/meta/inbound"
GRAPH_MESSAGES = "https://graph.facebook.com/v21.0/{phone_number_id}/messages"
CUSTOMER = "447700900123"
AGENT_A = uuid.UUID("aaaaaaaa-0000-4000-8000-0000000000a2")
AGENT_B = uuid.UUID("bbbbbbbb-0000-4000-8000-0000000000b2")


def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _text_payload(
    text: str = "Need a quote", phone_number_id: str = "1000001", msg_type: str = "text"
) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-scenario",
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
                                {"profile": {"name": "Ada"}, "wa_id": CUSTOMER}
                            ],
                            "messages": [
                                {
                                    "from": CUSTOMER,
                                    "id": "wamid.scenario.1",
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


def _post(client: TestClient, payload: dict, signature: str | None = None):
    body = jsonlib.dumps(payload).encode()
    header = _sign(body) if signature is None else signature
    return client.post(
        WEBHOOK,
        content=body,
        headers={"content-type": "application/json", "x-hub-signature-256": header},
    )


@pytest.fixture
def wa(monkeypatch):
    cfg = channels_config(
        meta_whatsapp_access_token=ACCESS_TOKEN,
        meta_whatsapp_app_secret=APP_SECRET,
        meta_whatsapp_verify_token="scenario-verify",
    )
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    monkeypatch.setattr(adapters, "get_channels_config", lambda: cfg)

    bindings = {
        "1000001": SimpleNamespace(
            id=uuid.uuid4(),
            organization_id=ORG_A,
            agent_id=AGENT_A,
            project_id=None,
            configuration={"phone_number_id": "1000001"},
        ),
        "2000002": SimpleNamespace(
            id=uuid.uuid4(),
            organization_id=ORG_B,
            agent_id=AGENT_B,
            project_id=None,
            configuration={"phone_number_id": "2000002"},
        ),
    }
    state = SimpleNamespace(
        handled=[],
        posts=[],
        status=200,
        error=None,
        reply=SimpleNamespace(
            handled=True,
            text="We can help.",
            conversation_id=None,
            grounded=True,
            confidence=0.8,
        ),
    )

    async def resolve(db, parsed):
        return bindings.get(parsed.to_address)

    async def handle(db, msg):
        state.handled.append(msg)
        return state.reply

    async def post(self, url, headers=None, json=None, **_):
        state.posts.append({"url": url, "headers": headers, "json": json})
        if state.error is not None:
            raise state.error
        return SimpleNamespace(status_code=state.status)

    monkeypatch.setattr(omni_routes, "_resolve_binding", resolve)
    monkeypatch.setattr(omnichannel_service, "handle_inbound", handle)
    monkeypatch.setattr(httpx.AsyncClient, "post", post)

    app = FastAPI()
    app.include_router(omni_routes.router)
    app.dependency_overrides[get_db] = lambda: FakeSession()
    state.client = TestClient(app)
    return state


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
def test_signed_text_message_is_answered_from_the_bound_number(wa):
    response = _post(wa.client, _text_payload())

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(wa.handled) == 1
    inbound = wa.handled[0]
    assert inbound.channel == "whatsapp"
    assert inbound.organization_id == ORG_A
    assert inbound.agent_id == AGENT_A
    assert inbound.text == "Need a quote"
    assert len(wa.posts) == 1
    sent = wa.posts[0]
    assert sent["url"] == GRAPH_MESSAGES.format(phone_number_id="1000001")
    assert sent["headers"] == {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    assert sent["json"]["to"] == CUSTOMER
    assert sent["json"]["text"] == {"body": "We can help."}


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
@pytest.mark.parametrize(
    "signature",
    ["sha256=" + "0" * 64, "", "md5=deadbeef"],
    ids=["wrong-digest", "missing", "wrong-scheme"],
)
def test_unsigned_or_forged_webhook_is_refused_before_it_is_read(wa, signature):
    response = _post(wa.client, _text_payload(), signature=signature)

    assert response.status_code == 401
    assert wa.handled == []
    assert wa.posts == []


@pytest.mark.critical
def test_stop_message_is_recorded_but_gets_no_ai_reply(wa):
    wa.reply = SimpleNamespace(
        handled=False,
        text="",
        conversation_id=None,
        grounded=False,
        confidence=0.0,
        opted_out=True,
    )

    response = _post(wa.client, _text_payload(text="STOP"))

    assert response.json() == {"ok": True}
    assert len(wa.handled) == 1
    assert wa.posts == []


@pytest.mark.critical
def test_status_callbacks_without_a_message_are_not_answered(wa):
    payload = _text_payload()
    payload["entry"][0]["changes"][0]["value"].pop("messages")

    response = _post(wa.client, payload)

    assert response.json() == {"ok": True, "skipped": "no message"}
    assert wa.handled == []
    assert wa.posts == []


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
@pytest.mark.parametrize("failure", ["graph-500", "transport-error"])
def test_graph_api_outage_does_not_fail_the_webhook_or_retry_inside_it(wa, failure):
    if failure == "graph-500":
        wa.status = 500
    else:
        wa.error = httpx.ConnectError("scenario outage")

    response = _post(wa.client, _text_payload())

    # Meta retries a non-2xx webhook, so the route acknowledges and logs only the status.
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(wa.handled) == 1
    assert len(wa.posts) == 1


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
def test_message_to_another_tenants_number_is_answered_only_by_that_tenant(wa):
    response = _post(wa.client, _text_payload(phone_number_id="2000002"))

    assert response.status_code == 200
    assert [m.organization_id for m in wa.handled] == [ORG_B]
    assert len(wa.posts) == 1
    assert wa.posts[0]["url"] == GRAPH_MESSAGES.format(phone_number_id="2000002")


@pytest.mark.critical
def test_message_to_an_unbound_number_is_skipped_not_routed_to_a_tenant(wa):
    response = _post(wa.client, _text_payload(phone_number_id="9999999"))

    assert response.json() == {"ok": True, "skipped": "no agent bound"}
    assert wa.handled == []
    assert wa.posts == []
