"""Voice agent webhooks (workstream 3): inbound calls, speech turns and outbound calls.

Twilio requests TwiML from these endpoints. Each answer speaks the agent's reply
and listens again until the caller hangs up or asks for a person. The AI is the
shared omnichannel pipeline (:func:`omnichannel_service.handle_inbound`), so this
module only handles telephony: signature checks, agent routing, speech turns and
TwiML. Campaign status callbacks (``/api/voice/status``) belong to the campaign
workstream and are deliberately not served here.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.agent_channel import AgentChannel
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.channels import adapters as channel_adapters
from app.services.channels.config import get_channels_config
from app.services.voice import tts, twiml

router = APIRouter(prefix="/api/voice", tags=["voice"])
log = logging.getLogger("app.voice.routes")

VOICE_CHANNEL = "voice"
# Phone-number channels whose binding also routes voice calls to the same agent.
_PHONE_CHANNELS = ("sms", "whatsapp")
MAX_SILENT_RETRIES = 2
_CAMPAIGN_ID = re.compile(r"[^A-Za-z0-9_-]")
_E164 = re.compile(r"^\+[1-9]\d{6,14}$")
# Caller asks for a person. Matched case-insensitively on whole words.
_HUMAN_REQUEST = re.compile(
    r"\b(human|person|operator|representative|agent|supervisor)\b|\btalk to (?:someone|somebody)\b",
    re.IGNORECASE,
)
_OUTBOUND_GREETING = (
    "Hi, this is {name} calling. Is now a good time to talk for a moment?"
)
_FALLBACK_ANSWER = (
    "Sorry, I couldn't come up with an answer to that. Could you rephrase it?"
)


def _xml(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


def _digits(raw: str | None) -> str:
    """Keep digits and a leading plus; drops prefixes such as ``tel:`` or ``whatsapp:``."""
    return re.sub(r"[^\d+]", "", raw or "")


async def _read_form(request: Request) -> dict:
    return dict((await request.form()).items())


def _is_signed(request: Request, form: dict) -> bool:
    """Verify Twilio's signature over the public URL, query string and form fields.

    Fails closed when the auth token or the public base URL is not configured,
    because the signed URL cannot be reconstructed without the base URL.
    """
    cfg = get_channels_config()
    if not cfg.twilio_auth_token or not cfg.public_api_base_url:
        return False
    url = cfg.public_api_base_url + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    return channel_adapters.verify_twilio_signature(
        cfg.twilio_auth_token,
        url,
        form,
        request.headers.get("x-twilio-signature"),
    )


def _voice() -> str:
    return get_channels_config().voice_say_voice or twiml.DEFAULT_VOICE


async def _speak(text: str) -> str:
    """Speech verb for one spoken turn: ElevenLabs when configured, else Twilio's ``<Say>``."""
    return await tts.render_speech(text, voice=_voice(), cfg=get_channels_config())


def _handoff_number() -> Optional[str]:
    raw = (get_channels_config().voice_handoff_number or "").strip()
    return raw if _E164.match(raw) else None


def _action_url(direction: str, retry: int) -> str:
    """Absolute gather action so Twilio posts back to a URL we can verify."""
    base = get_channels_config().public_api_base_url + "/api/voice/gather"
    params = {"retry": retry}
    if direction == "outbound":
        params["direction"] = "outbound"
    return f"{base}?{urlencode(params)}"


def _call_parties(form: dict, direction: str) -> tuple[str, str]:
    """Return ``(business_number, contact_number)`` for a call in either direction."""
    if direction == "outbound":
        # We placed the call: From is our number, To is the person we called.
        return _digits(form.get("From")), _digits(form.get("To"))
    return _digits(form.get("To")), _digits(form.get("From"))


async def _resolve_binding(
    db: AsyncSession, business_number: str
) -> Optional[AgentChannel]:
    """Find the agent that owns this business number.

    Prefers an explicit ``voice`` binding. Falls back to an enabled SMS or WhatsApp
    binding on the same number so one business line can serve both.
    """
    if not business_number:
        return None
    bare = business_number.lstrip("+")
    variants = [bare, f"+{bare}"]
    base = (
        select(AgentChannel)
        .where(AgentChannel.phone_number.in_(variants))
        .where(AgentChannel.enabled.is_(True))
    )
    binding = await db.scalar(base.where(AgentChannel.channel == VOICE_CHANNEL))
    if binding is None:
        binding = await db.scalar(base.where(AgentChannel.channel.in_(_PHONE_CHANNELS)))
    return binding


async def _agent_name(db: AsyncSession, agent_id) -> str:
    name = await db.scalar(select(Agent.name).where(Agent.id == agent_id))
    return (name or "our assistant")[:80]


def _retry_count(raw: str | None) -> int:
    try:
        value = int(raw or 0)
    except ValueError:
        return MAX_SILENT_RETRIES  # malformed counter: end the call rather than loop
    return max(0, min(value, MAX_SILENT_RETRIES))


@router.post("/inbound")
async def inbound_call(request: Request, db: AsyncSession = Depends(get_db)):
    """Twilio voice webhook for a call to the business number: greet and listen."""
    form = await _read_form(request)
    if not _is_signed(request, form):
        return Response(status_code=401)
    binding = await _resolve_binding(db, _call_parties(form, "inbound")[0])
    if binding is None:
        log.info("inbound voice call to an unbound number")
        return _xml(twiml.goodbye(twiml.UNAVAILABLE_TEXT, voice=_voice()))
    verb = await _speak(twiml.GREETING_TEXT)
    return _xml(
        twiml.greeting(action=_action_url("inbound", 0), voice=_voice(), verb=verb)
    )


@router.post("/gather")
async def gather_speech(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive one caller turn (``SpeechResult``), answer it and listen again."""
    form = await _read_form(request)
    if not _is_signed(request, form):
        return Response(status_code=401)

    direction = (
        "outbound" if request.query_params.get("direction") == "outbound" else "inbound"
    )
    retry = _retry_count(request.query_params.get("retry"))
    business_number, contact_number = _call_parties(form, direction)
    binding = await _resolve_binding(db, business_number)
    if binding is None:
        log.info("voice turn for an unbound number (%s)", direction)
        return _xml(twiml.goodbye(twiml.UNAVAILABLE_TEXT, voice=_voice()))

    speech = (form.get("SpeechResult") or "").strip()
    if not speech:
        if retry >= MAX_SILENT_RETRIES:
            return _xml(twiml.goodbye(twiml.SILENT_GOODBYE_TEXT, voice=_voice()))
        verb = await _speak(twiml.RETRY_TEXT)
        return _xml(
            twiml.reprompt(
                action=_action_url(direction, retry + 1), voice=_voice(), verb=verb
            )
        )

    if _HUMAN_REQUEST.search(speech):
        number = _handoff_number()
        log.info(
            "voice handoff requested (team line %s)", "set" if number else "not set"
        )
        return _xml(twiml.handoff(voice=_voice(), team_number=number))

    msg = omnichannel_service.InboundMessage(
        channel=VOICE_CHANNEL,
        organization_id=binding.organization_id,
        agent_id=binding.agent_id,
        project_id=binding.project_id,
        text=speech,
        phone=contact_number or None,
        external_id=contact_number or None,
        external_thread_id=form.get("CallSid") or None,
        meta={"direction": direction},
    )
    try:
        reply = await omnichannel_service.handle_inbound(db, msg)
    except Exception:  # noqa: BLE001
        await db.rollback()
        log.exception("voice turn failed")
        return _xml(twiml.goodbye(twiml.ERROR_TEXT, voice=_voice()))
    try:
        await db.commit()
    except Exception:  # noqa: BLE001
        await db.rollback()
        log.exception("voice turn persistence failed")
        return Response(status_code=503)

    if reply.opted_out:
        # The caller asked not to be contacted: close the call without an AI answer.
        return _xml(twiml.goodbye(twiml.OPT_OUT_TEXT, voice=_voice()))

    answer = twiml.clip_answer(reply.text) if reply.handled else ""
    spoken = answer or _FALLBACK_ANSWER
    verb = await _speak(spoken)
    return _xml(
        twiml.reply(
            spoken,
            action=_action_url(direction, 0),
            voice=_voice(),
            verb=verb,
        )
    )


@router.get("/audio/{key}.mp3")
async def voice_audio(key: str):
    """Serve MP3 produced by this server for a voice reply, for Twilio's ``<Play>``.

    Public by design: Twilio fetches it without a signature. The key is an HMAC of the
    spoken text, keyed with a server secret, and only audio this process synthesised is
    cached, so unknown or expired keys return 404.
    """
    audio = tts.get_audio(key)
    if audio is None:
        return Response(status_code=404)
    return Response(
        content=audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"}
    )


@router.post("/twiml")
async def outbound_twiml(request: Request, db: AsyncSession = Depends(get_db)):
    """TwiML for an outbound call placed by the campaign queue, fetched when the callee answers.

    The ``attempt`` query parameter is logged for traceability only. It is signed
    with the URL but never used to authorize anything: the agent is resolved from
    the business number on the call.
    """
    form = await _read_form(request)
    if not _is_signed(request, form):
        return Response(status_code=401)

    attempt = _CAMPAIGN_ID.sub("", request.query_params.get("attempt") or "")[:64]
    log.info("outbound voice call answered (attempt=%s)", attempt or "none")

    business_number, _ = _call_parties(form, "outbound")
    binding = await _resolve_binding(db, business_number)
    if binding is None:
        return _xml(twiml.goodbye(twiml.UNAVAILABLE_TEXT, voice=_voice()))

    name = await _agent_name(db, binding.agent_id)
    greeting_text = _OUTBOUND_GREETING.format(name=name)
    verb = await _speak(greeting_text)
    return _xml(
        twiml.greeting(
            greeting_text,
            action=_action_url("outbound", 0),
            voice=_voice(),
            verb=verb,
        )
    )
