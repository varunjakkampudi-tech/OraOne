"""Voice agent scenarios: signed inbound calls, outbound campaign TwiML, fail-closed signing,
speech fallback when ElevenLabs fails, and tenant routing by business number.

Twilio signatures are computed with Twilio's own RequestValidator, so the webhook check runs
for real. Bindings and agent names come from fakes. No call is placed and no audio is made.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from app.api.voice import routes as voice_routes
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.voice import tts
from app.services.voice import twiml
from scenario_support import FakeSession, channels_config

AUTH_TOKEN = "scenario-voice-auth-token"
BASE = "https://api.example.test"
BUSINESS_A = "+15550001111"
BUSINESS_B = "+15550002222"
CALLER = "+447700900123"
AGENT_A = uuid.UUID("aaaaaaaa-0000-4000-8000-0000000000a4")
AGENT_B = uuid.UUID("bbbbbbbb-0000-4000-8000-0000000000b4")
INBOUND = "/api/voice/inbound"
OUTBOUND = "/api/voice/twiml"


def _signed(path: str, form: dict, *, token: str = AUTH_TOKEN, query: str = "") -> dict:
    """Headers Twilio would send for ``path`` with these form fields."""
    url = BASE + path + (f"?{query}" if query else "")
    return {"x-twilio-signature": RequestValidator(token).compute_signature(url, form)}


@pytest.fixture
def voice(monkeypatch):
    cfg = channels_config(
        twilio_auth_token=AUTH_TOKEN,
        public_api_base_url=BASE,
        voice_say_voice="alice",
    )
    monkeypatch.setattr(voice_routes, "get_channels_config", lambda: cfg)

    bindings = {
        BUSINESS_A: SimpleNamespace(
            agent_id=AGENT_A, organization_id="org-a", project_id=None
        ),
        BUSINESS_B: SimpleNamespace(
            agent_id=AGENT_B, organization_id="org-b", project_id=None
        ),
    }
    names = {AGENT_A: "Ada Assistant", AGENT_B: "Bruno Bot"}
    state = SimpleNamespace(resolved=[], cfg=cfg, events=[], fail_commit=False)

    async def resolve(db, business_number):
        state.resolved.append(business_number)
        return bindings.get(f"+{business_number.lstrip('+')}")

    async def agent_name(db, agent_id):
        return names[agent_id]

    session = FakeSession()

    async def commit():
        state.events.append("commit")
        if state.fail_commit:
            raise RuntimeError("scenario database outage")
        session.commits += 1

    session.commit = commit
    state.session = session

    monkeypatch.setattr(voice_routes, "_resolve_binding", resolve)
    monkeypatch.setattr(voice_routes, "_agent_name", agent_name)

    async def handle(db, msg):
        state.events.append("handled")
        return SimpleNamespace(
            handled=True, text="Your order is on its way.", opted_out=False
        )

    monkeypatch.setattr(omnichannel_service, "handle_inbound", handle)

    app = FastAPI()
    app.include_router(voice_routes.router)
    app.dependency_overrides[get_db] = lambda: session
    state.client = TestClient(app)
    return state


def _inbound_form(to_number: str = BUSINESS_A) -> dict:
    return {"To": to_number, "From": CALLER, "CallSid": "CAscenario1"}


def _outbound_form(business: str = BUSINESS_A, contact: str = CALLER) -> dict:
    return {"From": business, "To": contact, "CallSid": "CAscenario2"}


def test_signed_voice_turn_commits_before_acknowledging(voice):
    path = "/api/voice/gather"
    form = {**_inbound_form(), "SpeechResult": "Where is my order?"}
    response = voice.client.post(path, data=form, headers=_signed(path, form))

    assert response.status_code == 200
    assert voice.events == ["handled", "commit"]
    assert voice.session.commits == 1


def test_voice_turn_persistence_failure_returns_retryable_server_error(voice):
    voice.fail_commit = True
    path = "/api/voice/gather"
    form = {**_inbound_form(), "SpeechResult": "Where is my order?"}

    response = voice.client.post(path, data=form, headers=_signed(path, form))

    assert response.status_code == 503
    assert voice.events == ["handled", "commit"]


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
def test_signed_inbound_call_greets_the_caller_and_listens(voice):
    form = _inbound_form()
    response = voice.client.post(INBOUND, data=form, headers=_signed(INBOUND, form))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert twiml.GREETING_TEXT in response.text
    assert "<Gather" in response.text
    assert voice.resolved == [BUSINESS_A]


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
@pytest.mark.parametrize(
    "headers_for",
    [
        lambda form: {},
        lambda form: {
            "x-twilio-signature": RequestValidator("someone-else").compute_signature(
                BASE + INBOUND, form
            )
        },
    ],
    ids=["unsigned", "signed-with-another-token"],
)
def test_unsigned_inbound_call_is_refused_before_any_tenant_lookup(voice, headers_for):
    form = _inbound_form()
    response = voice.client.post(INBOUND, data=form, headers=headers_for(form))

    assert response.status_code == 401
    assert voice.resolved == []


@pytest.mark.critical
def test_signature_check_fails_closed_when_the_auth_token_is_not_configured(
    monkeypatch, voice
):
    monkeypatch.setattr(
        voice_routes,
        "get_channels_config",
        lambda: channels_config(twilio_auth_token="", public_api_base_url=BASE),
    )
    form = _inbound_form()
    response = voice.client.post(INBOUND, data=form, headers=_signed(INBOUND, form))

    assert response.status_code == 401
    assert voice.resolved == []


@pytest.mark.critical
def test_outbound_twiml_request_must_be_signed_too(voice):
    form = _outbound_form()
    response = voice.client.post(OUTBOUND, data=form)

    assert response.status_code == 401
    assert voice.resolved == []


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
def test_elevenlabs_outage_falls_back_to_twilio_say_and_the_call_continues(
    monkeypatch, voice
):
    voice.cfg.elevenlabs_api_key = "scenario-elevenlabs-key"
    voice.cfg.elevenlabs_voice_id = "21mScenarioVoice01"
    voice.cfg.public_api_base_url = BASE

    async def unavailable(self, text):
        raise RuntimeError("scenario elevenlabs outage")

    monkeypatch.setattr(tts.ElevenLabsProvider, "speak", unavailable)
    form = _inbound_form()

    response = voice.client.post(INBOUND, data=form, headers=_signed(INBOUND, form))

    assert response.status_code == 200
    assert "<Say" in response.text
    assert "<Play" not in response.text
    assert twiml.GREETING_TEXT in response.text


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
def test_inbound_call_to_an_unbound_number_gets_the_unavailable_message_only(voice):
    unbound = "+15559990000"
    form = _inbound_form(to_number=unbound)

    response = voice.client.post(INBOUND, data=form, headers=_signed(INBOUND, form))

    assert response.status_code == 200
    assert twiml.UNAVAILABLE_TEXT in response.text
    assert "<Gather" not in response.text


@pytest.mark.critical
def test_outbound_call_is_introduced_by_the_agent_of_the_calling_tenant_only(voice):
    form = _outbound_form(business=BUSINESS_B)

    response = voice.client.post(
        OUTBOUND,
        params={"attempt": "attempt-scenario-1"},
        data=form,
        headers=_signed(OUTBOUND, form, query="attempt=attempt-scenario-1"),
    )

    assert response.status_code == 200
    assert "Bruno Bot" in response.text
    assert "Ada Assistant" not in response.text
    assert voice.resolved == [BUSINESS_B]
