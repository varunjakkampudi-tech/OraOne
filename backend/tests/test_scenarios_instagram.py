"""Instagram direct-message scenarios (Messenger Platform): signed inbound, reply, echoes,
Graph outage and tenant routing by Instagram account id.

External calls are replaced: binding lookup, AI pipeline and the Graph POST.
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
IG_TOKEN = "scenario-ig-page-token"
WEBHOOK = "/api/channels/meta_instagram/inbound"
GRAPH_ME_MESSAGES = "https://graph.facebook.com/v21.0/me/messages"
ACCOUNT_A = "17841400000000001"
ACCOUNT_B = "17841400000000002"
FAN = "igsid-scenario-77"
AGENT_A = uuid.UUID("aaaaaaaa-0000-4000-8000-0000000000a3")
AGENT_B = uuid.UUID("bbbbbbbb-0000-4000-8000-0000000000b3")


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _dm_payload(
    text: str = "Do you ship to Leeds?", recipient: str = ACCOUNT_A, is_echo=False
) -> dict:
    message = {"mid": "aWdfZAG1.scenario", "text": text}
    if is_echo:
        message["is_echo"] = True
    return {
        "object": "instagram",
        "entry": [
            {
                "id": recipient,
                "messaging": [
                    {
                        "sender": {"id": FAN},
                        "recipient": {"id": recipient},
                        "message": message,
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
def ig(monkeypatch):
    cfg = channels_config(
        meta_instagram_access_token=IG_TOKEN,
        meta_whatsapp_app_secret=APP_SECRET,
        meta_whatsapp_verify_token="scenario-verify",
    )
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    monkeypatch.setattr(adapters, "get_channels_config", lambda: cfg)

    bindings = {
        ACCOUNT_A: SimpleNamespace(
            id=uuid.uuid4(),
            organization_id=ORG_A,
            agent_id=AGENT_A,
            project_id=None,
            configuration={"instagram_account_id": ACCOUNT_A},
        ),
        ACCOUNT_B: SimpleNamespace(
            id=uuid.uuid4(),
            organization_id=ORG_B,
            agent_id=AGENT_B,
            project_id=None,
            configuration={"instagram_account_id": ACCOUNT_B},
        ),
    }
    state = SimpleNamespace(
        handled=[],
        posts=[],
        status=200,
        error=None,
        reply=SimpleNamespace(
            handled=True,
            text="Yes, we ship across the UK.",
            conversation_id=None,
            grounded=True,
            confidence=0.7,
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
def test_signed_dm_is_answered_through_the_owning_account(ig):
    response = _post(ig.client, _dm_payload())

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert [m.channel for m in ig.handled] == ["instagram"]
    assert ig.handled[0].organization_id == ORG_A
    assert ig.handled[0].external_id == FAN
    assert len(ig.posts) == 1
    sent = ig.posts[0]
    assert sent["url"] == GRAPH_ME_MESSAGES
    assert sent["headers"] == {"Authorization": f"Bearer {IG_TOKEN}"}
    assert sent["json"] == {
        "recipient": {"id": FAN},
        "message": {"text": "Yes, we ship across the UK."},
    }


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
@pytest.mark.parametrize(
    "signature",
    ["sha256=" + "f" * 64, ""],
    ids=["wrong-digest", "missing"],
)
def test_unsigned_dm_webhook_is_refused(ig, signature):
    response = _post(ig.client, _dm_payload(), signature=signature)

    assert response.status_code == 401
    assert ig.handled == []
    assert ig.posts == []


@pytest.mark.critical
def test_our_own_echoed_messages_are_never_answered(ig):
    response = _post(ig.client, _dm_payload(is_echo=True))

    assert response.json() == {"ok": True, "skipped": "no message"}
    assert ig.handled == []
    assert ig.posts == []


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
@pytest.mark.parametrize("failure", ["graph-403", "transport-error"])
def test_instagram_send_failure_is_logged_and_the_webhook_still_acknowledges(
    ig, failure
):
    if failure == "graph-403":
        ig.status = 403
    else:
        ig.error = httpx.ReadTimeout("scenario timeout")

    response = _post(ig.client, _dm_payload())

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(ig.handled) == 1
    assert len(ig.posts) == 1


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
def test_dm_to_another_tenants_account_is_routed_to_that_tenant(ig):
    response = _post(ig.client, _dm_payload(recipient=ACCOUNT_B))

    assert response.status_code == 200
    assert [m.organization_id for m in ig.handled] == [ORG_B]
    assert [m.agent_id for m in ig.handled] == [AGENT_B]


@pytest.mark.critical
def test_organization_id_in_the_payload_is_ignored_for_routing(ig):
    payload = _dm_payload(recipient=ACCOUNT_B)
    payload["organization_id"] = str(ORG_A)

    response = _post(ig.client, payload)

    assert response.status_code == 200
    assert [m.organization_id for m in ig.handled] == [ORG_B]
