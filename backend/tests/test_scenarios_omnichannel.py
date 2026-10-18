"""Omnichannel scenarios: the shared inbound pipeline reached from the SDK, Twilio and email
webhooks. Covers authenticated delivery, rejected secrets and signatures, a Twilio outage,
and routing that cannot be steered by the request body.

The AI pipeline and channel bindings are replaced with fakes. Twilio signatures use Twilio's
RequestValidator, and the SDK signature is an HMAC over the raw body.
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
from twilio.request_validator import RequestValidator

from app.api.omnichannel import routes as omni_routes
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.channels import adapters
from scenario_support import ORG_A, ORG_B, FakeSession, channels_config, sql

BASE = "https://api.example.test"
TWILIO_TOKEN = "scenario-twilio-auth-token"
TWILIO_ACCOUNT = "ACscenario0000000000000000000000"
SDK_SECRET = "scenario-sdk-shared-secret"
EMAIL_SECRET = "scenario-email-inbound-secret"
AGENT_A = uuid.UUID("aaaaaaaa-0000-4000-8000-0000000000a5")
AGENT_B = uuid.UUID("bbbbbbbb-0000-4000-8000-0000000000b5")
BUSINESS_A = "+15550001111"
CUSTOMER = "+447700900123"


def _sdk_signature(body: bytes, secret: str = SDK_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _sdk_body(agent_id: uuid.UUID = AGENT_A, **extra) -> bytes:
    payload = {
        "text": "Where is my order?",
        "agent_id": str(agent_id),
        "user": {"id": "device-scenario-1", "name": "Ada"},
        "session_id": "sdk-session-1",
    }
    payload.update(extra)
    return jsonlib.dumps(payload).encode()


@pytest.fixture
def channels(monkeypatch):
    cfg = channels_config(
        twilio_account_sid=TWILIO_ACCOUNT,
        twilio_auth_token=TWILIO_TOKEN,
        twilio_phone_number=BUSINESS_A,
        public_api_base_url=BASE,
        email_inbound_secret=EMAIL_SECRET,
        twilio_configured=True,
    )
    monkeypatch.setattr(omni_routes, "get_channels_config", lambda: cfg)
    monkeypatch.setattr(adapters, "get_channels_config", lambda: cfg)
    return cfg


@pytest.fixture
def pipeline(monkeypatch, channels):
    """Bindings keyed by agent id (SDK) and by business number (Twilio)."""
    sdk_bindings = {
        str(AGENT_A): SimpleNamespace(
            id=uuid.uuid4(),
            organization_id=ORG_A,
            agent_id=AGENT_A,
            project_id=None,
            configuration={"sdk_secret": SDK_SECRET},
        ),
        str(AGENT_B): SimpleNamespace(
            id=uuid.uuid4(),
            organization_id=ORG_B,
            agent_id=AGENT_B,
            project_id=None,
            configuration={"sdk_secret": "scenario-sdk-secret-b"},
        ),
    }
    twilio_binding = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=ORG_A,
        agent_id=AGENT_A,
        project_id=None,
        phone_number=BUSINESS_A,
        configuration={},
    )
    state = SimpleNamespace(
        handled=[],
        twilio_posts=[],
        twilio_status=201,
        twilio_error=None,
        reply=SimpleNamespace(
            handled=True,
            text="Your order ships today.",
            conversation_id=uuid.UUID("cccccccc-0000-4000-8000-0000000000c5"),
            grounded=True,
            confidence=0.91,
            generated=True,
        ),
    )

    async def resolve(db, parsed):
        if parsed.provider == "sdk":
            return sdk_bindings.get(parsed.route_value or "")
        if parsed.provider == "twilio":
            return twilio_binding if parsed.to_address == BUSINESS_A else None
        return None

    async def handle(db, msg):
        state.handled.append(msg)
        return state.reply

    async def post(self, url, data=None, auth=None, **_):
        state.twilio_posts.append({"url": url, "data": data, "auth": auth})
        if state.twilio_error is not None:
            raise state.twilio_error
        return SimpleNamespace(status_code=state.twilio_status)

    monkeypatch.setattr(omni_routes, "_resolve_binding", resolve)
    monkeypatch.setattr(omnichannel_service, "handle_inbound", handle)
    monkeypatch.setattr(httpx.AsyncClient, "post", post)

    app = FastAPI()
    app.include_router(omni_routes.router)
    app.dependency_overrides[get_db] = lambda: FakeSession()
    state.client = TestClient(app)
    return state


def _post_sdk(client: TestClient, body: bytes, signature: str | None = None):
    header = _sdk_signature(body) if signature is None else signature
    return client.post(
        "/api/channels/sdk/inbound",
        content=body,
        headers={"content-type": "application/json", "x-oraone-signature": header},
    )


def _twilio_form(to_number: str = BUSINESS_A) -> dict:
    return {
        "From": CUSTOMER,
        "To": to_number,
        "Body": "Do you open on Sunday?",
        "MessageSid": "SMscenario0001",
    }


def _post_twilio(client: TestClient, form: dict, *, token: str = TWILIO_TOKEN):
    url = BASE + "/api/channels/twilio/inbound"
    signature = RequestValidator(token).compute_signature(url, form)
    return client.post(
        "/api/channels/twilio/inbound",
        data=form,
        headers={"x-twilio-signature": signature},
    )


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
def test_authenticated_sdk_message_gets_its_reply_in_the_same_response(pipeline):
    response = _post_sdk(pipeline.client, _sdk_body())

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["reply"] == "Your order ships today."
    assert body["conversation_id"] == str(pipeline.reply.conversation_id)
    assert body["grounded"] is True
    assert body["generated"] is True
    assert [m.organization_id for m in pipeline.handled] == [ORG_A]
    assert [m.channel for m in pipeline.handled] == ["mobile"]


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
@pytest.mark.parametrize(
    "signature",
    [
        "sha256=" + "1" * 64,
        "",
        "sha256="
        + hmac.new(b"not-the-secret", _sdk_body(), hashlib.sha256).hexdigest(),
    ],
    ids=["wrong-digest", "missing", "signed-with-another-secret"],
)
def test_sdk_message_without_a_valid_binding_signature_is_refused(pipeline, signature):
    response = _post_sdk(pipeline.client, _sdk_body(), signature=signature)

    assert response.status_code == 401
    assert pipeline.handled == []


@pytest.mark.critical
def test_twilio_webhook_without_a_valid_signature_is_refused(pipeline):
    response = pipeline.client.post("/api/channels/twilio/inbound", data=_twilio_form())
    forged = _post_twilio(pipeline.client, _twilio_form(), token="someone-else")

    assert response.status_code == 401
    assert forged.status_code == 401
    assert pipeline.handled == []
    assert pipeline.twilio_posts == []


@pytest.mark.critical
@pytest.mark.parametrize(
    ("configured", "presented"),
    [(EMAIL_SECRET, "wrong-secret"), (EMAIL_SECRET, ""), ("", "")],
    ids=["wrong-secret", "missing-secret", "unconfigured-fails-closed"],
)
def test_email_webhook_fails_closed_without_the_shared_secret(
    pipeline, monkeypatch, configured, presented
):
    monkeypatch.setattr(
        omni_routes,
        "get_channels_config",
        lambda: channels_config(email_inbound_secret=configured),
    )
    headers = {"x-email-inbound-secret": presented} if presented else {}

    response = pipeline.client.post(
        "/api/channels/email/inbound",
        json={"from": CUSTOMER, "to": "help@tenant.example", "text": "Hello"},
        headers=headers,
    )

    assert response.status_code == 401
    assert pipeline.handled == []


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
@pytest.mark.parametrize("failure", ["twilio-500", "transport-error"])
def test_twilio_send_failure_still_acknowledges_the_webhook(pipeline, failure):
    if failure == "twilio-500":
        pipeline.twilio_status = 500
    else:
        pipeline.twilio_error = httpx.ConnectError("scenario outage")

    response = _post_twilio(pipeline.client, _twilio_form())

    # Twilio retries anything that is not a 2xx, so the answer is still acknowledged.
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert len(pipeline.handled) == 1
    assert len(pipeline.twilio_posts) == 1


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
def test_sdk_request_for_another_tenants_agent_is_answered_by_that_tenant(pipeline):
    response = _post_sdk(
        pipeline.client,
        _sdk_body(agent_id=AGENT_B, organization_id=str(ORG_A)),
        signature=_sdk_signature(
            _sdk_body(agent_id=AGENT_B, organization_id=str(ORG_A)),
            secret="scenario-sdk-secret-b",
        ),
    )

    assert response.status_code == 200
    assert [m.organization_id for m in pipeline.handled] == [ORG_B]
    assert [m.agent_id for m in pipeline.handled] == [AGENT_B]


@pytest.mark.critical
async def test_sdk_binding_lookup_is_limited_to_enabled_sdk_channels_for_that_agent():
    session = FakeSession()
    parsed = adapters.ParsedInbound(
        channel="mobile",
        provider="sdk",
        text="hi",
        route_value=str(AGENT_B),
    )

    await omni_routes._resolve_binding(session, parsed)

    statement = sql(session.statements[0])
    assert "'sdk'" in statement
    assert "enabled" in statement
    assert str(AGENT_B) in statement
    assert str(ORG_A) not in statement


@pytest.mark.critical
def test_twilio_message_to_an_unbound_number_is_skipped(pipeline):
    response = _post_twilio(pipeline.client, _twilio_form(to_number="+15559990000"))

    assert response.status_code == 200
    assert pipeline.handled == []
    assert pipeline.twilio_posts == []
