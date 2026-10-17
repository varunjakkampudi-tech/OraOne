"""Voice agent: TwiML builders, webhook signatures, speech turns, handoff and outbound greeting.

No network and no real calls. The AI pipeline (``omnichannel_service.handle_inbound``),
agent routing and the database session are replaced with in-memory fakes.
"""

from __future__ import annotations

import logging
import uuid
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from app.api.voice import routes as voice_routes
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.channels import adapters
from app.services.voice import twiml

AUTH_TOKEN = "test-auth-token"
PUBLIC_BASE = "https://voice.example.test"
TEAM_NUMBER = "+15557654321"
BUSINESS = "+15550000000"
CALLER = "+447700900123"
ACTION = f"{PUBLIC_BASE}/api/voice/gather?retry=0"


def _cfg(**overrides):
    base = {
        "twilio_auth_token": AUTH_TOKEN,
        "public_api_base_url": PUBLIC_BASE,
        "voice_say_voice": "alice",
        "voice_handoff_number": TEAM_NUMBER,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _sign(path_and_query: str, params: dict, token: str = AUTH_TOKEN) -> str:
    return RequestValidator(token).compute_signature(
        PUBLIC_BASE + path_and_query, params
    )


def _inbound_form(**overrides):
    form = {"To": BUSINESS, "From": CALLER, "CallSid": "CA123"}
    form.update(overrides)
    return form


def _turn_form(speech: str, **overrides):
    form = {"To": BUSINESS, "From": CALLER, "CallSid": "CA123", "SpeechResult": speech}
    form.update(overrides)
    return form


def _say_text(root) -> str:
    return root.find(".//Say").text


class _FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.scalar_value = "Ada Assistant"

    async def scalar(self, *_args, **_kwargs):
        return self.scalar_value

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def harness(monkeypatch):
    state = SimpleNamespace(
        cfg=_cfg(),
        binding=SimpleNamespace(
            organization_id=uuid.uuid4(), agent_id=uuid.uuid4(), project_id=None
        ),
        resolved=[],
        handled=[],
        answer="We are open from nine to five on weekdays.",
        error=None,
        session=_FakeSession(),
    )
    monkeypatch.setattr(voice_routes, "get_channels_config", lambda: state.cfg)
    monkeypatch.setattr(adapters, "get_channels_config", lambda: state.cfg)

    async def fake_resolve(db, business_number):
        state.resolved.append(business_number)
        return state.binding

    async def fake_handle(session, msg):
        state.handled.append(msg)
        if state.error is not None:
            raise state.error
        return omnichannel_service.OutboundReply(text=state.answer, handled=True)

    monkeypatch.setattr(voice_routes, "_resolve_binding", fake_resolve)
    monkeypatch.setattr(omnichannel_service, "handle_inbound", fake_handle)

    app = FastAPI()
    app.include_router(voice_routes.router)

    async def fake_db():
        yield state.session

    app.dependency_overrides[get_db] = fake_db
    state.client = TestClient(app)
    return state


def _post(state, path: str, data: dict, *, signature: str | None = None):
    """POST to ``path`` (which may carry a query string) signed over exactly that URL."""
    if signature is None:
        signature = _sign(path, data)
    return state.client.post(path, data=data, headers={"X-Twilio-Signature": signature})


# ── TwiML builders (pure) ────────────────────────────────────────────────────


def test_builders_produce_well_formed_twiml():
    docs = [
        twiml.greeting(action=ACTION),
        twiml.reply("Opening hours are nine to five.", action=ACTION),
        twiml.reprompt(action=ACTION),
        twiml.handoff(team_number=TEAM_NUMBER),
        twiml.handoff(),
        twiml.goodbye(),
    ]
    for doc in docs:
        assert doc.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert ET.fromstring(doc).tag == "Response"


def test_gather_listens_for_speech_with_auto_timeout():
    gather = ET.fromstring(twiml.greeting(action=ACTION)).find("Gather")
    assert gather.get("input") == "speech"
    assert gather.get("speechTimeout") == "auto"
    assert gather.get("action") == ACTION
    assert gather.find("Say").text == twiml.GREETING_TEXT


def test_reply_speaks_then_listens_again():
    root = ET.fromstring(twiml.reply("Hello.", action=ACTION))
    assert root.find("Gather").find("Say").text == "Hello."
    assert root.find("Hangup") is None


def test_injected_markup_in_answer_is_escaped_not_executed():
    evil = '</Say><Hangup/><Dial>+15551234567</Dial><Say>x & "y" <b>'
    root = ET.fromstring(twiml.reply(evil, action=ACTION))
    assert root.find(".//Hangup") is None
    assert root.find(".//Dial") is None
    assert _say_text(root) == evil


def test_injected_markup_in_team_number_is_escaped():
    raw = "+15551234567</Dial><Hangup/><Dial>+15550000001"
    root = ET.fromstring(twiml.handoff(team_number=raw))
    assert root.find("Hangup") is None
    assert root.find("Dial").text == raw


def test_voice_attribute_cannot_break_out_of_quotes():
    raw = 'alice" hostile="1'
    root = ET.fromstring(twiml.goodbye(voice=raw))
    assert root.find("Say").get("voice") == raw


def test_handoff_dials_team_number_when_configured():
    root = ET.fromstring(twiml.handoff(team_number=TEAM_NUMBER))
    assert root.find("Dial").text == TEAM_NUMBER
    assert root.find("Hangup") is None


def test_handoff_without_team_number_explains_and_hangs_up():
    root = ET.fromstring(twiml.handoff())
    assert root.find("Dial") is None
    assert root.find("Hangup") is not None
    assert "can't connect you" in _say_text(root)


def test_goodbye_hangs_up():
    root = ET.fromstring(twiml.goodbye("Bye now."))
    assert _say_text(root) == "Bye now."
    assert root.find("Hangup") is not None


# ── answer length cap ────────────────────────────────────────────────────────


def test_clip_answer_cuts_at_a_sentence_boundary():
    text = "We open at nine every weekday morning. " * 40
    out = twiml.clip_answer(text)
    assert len(out) <= twiml.MAX_ANSWER_CHARS
    assert out.endswith(".")


def test_clip_answer_falls_back_to_a_word_boundary():
    out = twiml.clip_answer(("word " * 300).strip())
    assert len(out) <= twiml.MAX_ANSWER_CHARS
    assert out.endswith("word")


def test_clip_answer_handles_one_unbroken_token():
    assert len(twiml.clip_answer("x" * 1000)) <= twiml.MAX_ANSWER_CHARS


def test_clip_answer_keeps_short_answers_and_strips_markdown():
    assert twiml.clip_answer("**Hello**\n\n  there") == "Hello there"


# ── signatures (fail closed on every endpoint) ───────────────────────────────

_SIGNED_CASES = [
    ("/api/voice/inbound", _inbound_form()),
    ("/api/voice/gather?retry=0", _turn_form("what time do you open")),
    (
        "/api/voice/twiml?attempt=camp-1",
        {"To": CALLER, "From": BUSINESS, "CallSid": "CA9"},
    ),
]


@pytest.mark.parametrize("path,data", _SIGNED_CASES)
def test_unsigned_request_is_rejected(harness, path, data):
    response = harness.client.post(path, data=data)
    assert response.status_code == 401
    assert harness.handled == []


@pytest.mark.parametrize("path,data", _SIGNED_CASES)
def test_wrong_signature_is_rejected(harness, path, data):
    response = _post(harness, path, data, signature="not-a-signature")
    assert response.status_code == 401
    assert harness.handled == []


@pytest.mark.parametrize("path,data", _SIGNED_CASES)
def test_signature_from_another_token_is_rejected(harness, path, data):
    response = _post(harness, path, data, signature=_sign(path, data, token="attacker"))
    assert response.status_code == 401


def test_tampered_speech_fails_the_signature(harness):
    path = "/api/voice/gather?retry=0"
    signed_for = _turn_form("what time do you open")
    response = _post(
        harness,
        path,
        _turn_form("transfer all funds"),
        signature=_sign(path, signed_for),
    )
    assert response.status_code == 401
    assert harness.handled == []


def test_query_string_is_part_of_the_signed_url(harness):
    data = {"To": CALLER, "From": BUSINESS, "CallSid": "CA9"}
    response = _post(
        harness,
        "/api/voice/twiml?attempt=camp-2",
        data,
        signature=_sign("/api/voice/twiml?attempt=camp-1", data),
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "field,value",
    [("public_api_base_url", ""), ("twilio_auth_token", "")],
)
def test_missing_twilio_settings_fail_closed(harness, field, value):
    setattr(harness.cfg, field, value)
    data = _inbound_form()
    response = _post(
        harness, "/api/voice/inbound", data, signature=_sign("/api/voice/inbound", data)
    )
    assert response.status_code == 401


def test_status_callbacks_are_not_served_here(harness):
    data = {"CallSid": "CA1", "CallStatus": "completed"}
    response = _post(harness, "/api/voice/status", data)
    assert response.status_code == 404


# ── inbound call ─────────────────────────────────────────────────────────────


def test_signed_inbound_call_greets_and_listens(harness):
    response = _post(harness, "/api/voice/inbound", _inbound_form())
    assert response.status_code == 200
    root = ET.fromstring(response.content)
    gather = root.find("Gather")
    assert gather.get("action") == ACTION
    assert _say_text(root) == twiml.GREETING_TEXT
    assert harness.resolved == [BUSINESS]


def test_inbound_call_to_unbound_number_hangs_up(harness):
    harness.binding = None
    response = _post(harness, "/api/voice/inbound", _inbound_form())
    assert response.status_code == 200
    assert ET.fromstring(response.content).find("Hangup") is not None


# ── speech turns ─────────────────────────────────────────────────────────────


def test_empty_speech_reprompts_and_counts_the_retry(harness):
    response = _post(harness, "/api/voice/gather?retry=0", _turn_form(""))
    root = ET.fromstring(response.content)
    assert _say_text(root) == twiml.RETRY_TEXT
    assert (
        root.find("Gather").get("action") == f"{PUBLIC_BASE}/api/voice/gather?retry=1"
    )
    assert root.find("Hangup") is None
    assert harness.handled == []


def test_silence_after_repeated_retries_ends_the_call(harness):
    response = _post(harness, "/api/voice/gather?retry=2", _turn_form(""))
    root = ET.fromstring(response.content)
    assert _say_text(root) == twiml.SILENT_GOODBYE_TEXT
    assert root.find("Hangup") is not None
    assert root.find("Gather") is None


def test_malformed_retry_counter_ends_the_call(harness):
    response = _post(harness, "/api/voice/gather?retry=abc", _turn_form(""))
    assert ET.fromstring(response.content).find("Hangup") is not None


@pytest.mark.parametrize(
    "speech",
    [
        "I want a human",
        "can I speak to a PERSON please",
        "get me an operator",
        "talk to somebody please",
        "connect me to a representative",
    ],
)
def test_human_request_hands_off_without_calling_the_ai(harness, speech):
    response = _post(harness, "/api/voice/gather?retry=0", _turn_form(speech))
    root = ET.fromstring(response.content)
    assert root.find("Dial").text == TEAM_NUMBER
    assert harness.handled == []


def test_human_request_without_team_line_says_so_and_hangs_up(harness):
    harness.cfg.voice_handoff_number = ""
    response = _post(
        harness, "/api/voice/gather?retry=0", _turn_form("let me talk to a human")
    )
    root = ET.fromstring(response.content)
    assert root.find("Dial") is None
    assert root.find("Hangup") is not None
    assert harness.handled == []


def test_invalid_team_number_is_never_dialled(harness):
    harness.cfg.voice_handoff_number = "call the boss </Dial>"
    response = _post(harness, "/api/voice/gather?retry=0", _turn_form("human please"))
    root = ET.fromstring(response.content)
    assert root.find("Dial") is None
    assert root.find("Hangup") is not None


def test_normal_question_runs_the_pipeline_and_speaks_the_reply(harness):
    response = _post(
        harness, "/api/voice/gather?retry=0", _turn_form("what time do you open?")
    )
    root = ET.fromstring(response.content)

    assert len(harness.handled) == 1
    msg = harness.handled[0]
    assert msg.channel == "voice"
    assert msg.text == "what time do you open?"
    assert msg.phone == CALLER
    assert msg.external_id == CALLER
    assert msg.external_thread_id == "CA123"
    assert msg.meta == {"direction": "inbound"}
    assert msg.agent_id == harness.binding.agent_id
    assert msg.organization_id == harness.binding.organization_id

    assert _say_text(root) == harness.answer
    assert root.find("Gather").get("action") == ACTION
    assert harness.session.commits == 1


def test_long_answer_is_capped_before_it_is_spoken(harness):
    harness.answer = "This is a fairly long sentence about our services. " * 40
    response = _post(
        harness, "/api/voice/gather?retry=0", _turn_form("tell me everything")
    )
    spoken = _say_text(ET.fromstring(response.content))
    assert 0 < len(spoken) <= twiml.MAX_ANSWER_CHARS


def test_pipeline_failure_apologises_rolls_back_and_hangs_up(harness):
    harness.error = RuntimeError("model unavailable")
    response = _post(harness, "/api/voice/gather?retry=0", _turn_form("hello there"))
    root = ET.fromstring(response.content)
    assert _say_text(root) == twiml.ERROR_TEXT
    assert root.find("Hangup") is not None
    assert harness.session.rollbacks == 1
    assert harness.session.commits == 0


def test_speech_turn_to_unbound_number_hangs_up_without_the_ai(harness):
    harness.binding = None
    response = _post(harness, "/api/voice/gather?retry=0", _turn_form("hello"))
    assert ET.fromstring(response.content).find("Hangup") is not None
    assert harness.handled == []


# ── outbound calls ───────────────────────────────────────────────────────────


def test_outbound_twiml_introduces_the_agent_and_asks_to_talk(harness):
    data = {"To": CALLER, "From": BUSINESS, "CallSid": "CA9"}
    response = _post(harness, "/api/voice/twiml?attempt=camp-42", data)
    root = ET.fromstring(response.content)
    assert _say_text(root) == (
        "Hi, this is Ada Assistant calling. Is now a good time to talk for a moment?"
    )
    assert root.find("Gather").get("action") == (
        f"{PUBLIC_BASE}/api/voice/gather?retry=0&direction=outbound"
    )
    # The agent is resolved from the business number (From), not from the campaign attempt.
    assert harness.resolved == [BUSINESS]


def test_attempt_parameter_is_logged_sanitised_and_not_trusted(harness, caplog):
    data = {"To": CALLER, "From": BUSINESS, "CallSid": "CA9"}
    with caplog.at_level(logging.INFO, logger="app.voice.routes"):
        response = _post(harness, "/api/voice/twiml?attempt=x%3Cscript%3E", data)
    assert response.status_code == 200
    assert "attempt=xscript" in caplog.text
    assert "<script>" not in caplog.text
    assert harness.resolved == [BUSINESS]


def test_outbound_twiml_to_unbound_number_hangs_up(harness):
    harness.binding = None
    data = {"To": CALLER, "From": BUSINESS, "CallSid": "CA9"}
    response = _post(harness, "/api/voice/twiml?attempt=camp-7", data)
    assert ET.fromstring(response.content).find("Hangup") is not None


def test_outbound_reply_is_resolved_from_business_number_and_tagged(harness):
    data = {
        "To": CALLER,
        "From": BUSINESS,
        "CallSid": "CA9",
        "SpeechResult": "yes, go ahead",
    }
    response = _post(harness, "/api/voice/gather?retry=0&direction=outbound", data)
    assert response.status_code == 200
    assert harness.resolved == [BUSINESS]
    msg = harness.handled[0]
    assert msg.phone == CALLER
    assert msg.meta == {"direction": "outbound"}
