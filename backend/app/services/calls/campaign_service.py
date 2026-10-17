"""Outbound calling queue: plan attempts per lead and dial one call at a time.

Every call decision goes through :func:`app.services.outreach_policy.check_outbound`.
Planning records a ``skipped`` attempt with a plain-language reason for each lead
the policy blocks. Dialing claims one ``queued`` attempt under a row lock on the
campaign, so a campaign never has two calls in progress. The attempt stays
``calling`` until Twilio's status callback reports how the call ended.

Services in this module do not commit, except :func:`dial_next`, which commits
before the Twilio request so the claimed attempt is recorded first. Logs carry
ids and status codes only, never phone numbers.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.call_campaign import (
    AttemptStatus,
    CallAttempt,
    CallCampaign,
    CampaignStatus,
)
from app.database.models.lead import Lead
from app.services import contact_policy_service
from app.services.channels.config import get_channels_config
from app.services.outreach_policy import ContactState, Decision, check_outbound

log = logging.getLogger("app.calls.campaign")

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"
_HTTP_TIMEOUT = 15.0
MAX_CAMPAIGN_LEADS = 1000
#: A call still "calling" after this long lost its status callback. Twilio is asked for
#: its status before the attempt is released (see ``_has_active_call``).
STALE_CALL_AFTER = timedelta(minutes=30)
_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def _now() -> datetime:
    """The single clock for this module. Tests replace it to pin calling hours."""
    return datetime.now(timezone.utc)


_CONSENT_MAP = {"granted": "given", "denied": "withdrawn", "unknown": "unknown"}
# Twilio CallStatus values that end a call.
_COMPLETED_STATUSES = frozenset({"completed"})
_FAILED_STATUSES = frozenset({"busy", "no-answer", "failed", "canceled"})


class CampaignError(Exception):
    """A request-level problem with a message safe to show to the user."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class CallingNotConfigured(CampaignError):
    pass


class DialError(CampaignError):
    pass


@dataclass(frozen=True)
class StatusTransition:
    campaign_id: uuid.UUID


# ─────────────────────────── configuration ───────────────────────────


def missing_calling_config() -> list[str]:
    cfg = get_channels_config()
    missing: list[str] = []
    if not (cfg.twilio_account_sid and cfg.twilio_auth_token):
        missing.append("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
    if not cfg.twilio_phone_number:
        missing.append("TWILIO_PHONE_NUMBER")
    if not cfg.public_api_base_url:
        missing.append("PUBLIC_API_BASE_URL")
    return missing


def require_calling_config() -> None:
    missing = missing_calling_config()
    if missing:
        raise CallingNotConfigured(
            503,
            "Calling is not configured. Set " + ", ".join(missing) + " on the server.",
        )


def validate_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise CampaignError(
            422, f"Unknown timezone {name!r}. Use an IANA name such as Europe/London."
        ) from e
    return name


# ─────────────────────────── policy decisions ───────────────────────────


def _phone_problem(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return "This lead has no phone number."
    if not _E164.match(phone):
        return "The phone number needs a country code starting with + before it can be called."
    return None


def _valid_zone(name: object) -> Optional[str]:
    if not isinstance(name, str) or not name.strip():
        return None
    try:
        ZoneInfo(name.strip())
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return name.strip()


def _contact_timezone(lead: Lead) -> Optional[str]:
    """The lead's own IANA timezone from ``lead.extra["timezone"]``, if it is valid."""
    return _valid_zone((lead.extra or {}).get("timezone"))


def _country_code_known(phone: Optional[str]) -> bool:
    """True when an E.164 number starts with a recognised country calling code.

    A recognised code is the evidence that the campaign's timezone is a reasonable
    proxy for the contact's local time. The list covers common codes; an unlisted
    code counts as unknown, so the lead is not dialed.
    """
    digits = (phone or "").lstrip("+")
    return any(digits[:n] in _CALLING_CODES for n in (1, 2, 3))


# Recognised country calling codes (ITU-T E.164), as 1 to 3 digit prefixes.
_CALLING_CODES = frozenset(
    {
        "1",
        "7",
        "20",
        "27",
        "30",
        "31",
        "32",
        "33",
        "34",
        "36",
        "39",
        "40",
        "41",
        "43",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "51",
        "52",
        "53",
        "54",
        "55",
        "56",
        "57",
        "58",
        "60",
        "61",
        "62",
        "63",
        "64",
        "65",
        "66",
        "81",
        "82",
        "84",
        "86",
        "90",
        "91",
        "92",
        "93",
        "94",
        "95",
        "98",
        "212",
        "213",
        "216",
        "218",
        "220",
        "221",
        "233",
        "234",
        "254",
        "255",
        "256",
        "260",
        "263",
        "351",
        "352",
        "353",
        "354",
        "355",
        "356",
        "357",
        "358",
        "359",
        "370",
        "371",
        "372",
        "373",
        "374",
        "375",
        "376",
        "377",
        "378",
        "380",
        "381",
        "382",
        "385",
        "386",
        "387",
        "389",
        "420",
        "421",
        "423",
        "852",
        "853",
        "855",
        "856",
        "880",
        "886",
        "961",
        "962",
        "965",
        "966",
        "968",
        "971",
        "972",
        "973",
        "974",
    }
)


def contact_state_for(
    lead: Lead, *, attempts_last_24h: int, suppressed: bool = False
) -> ContactState:
    """Build the policy input from a lead.

    Consent comes from ``lead.extra["consent"]`` (set by lead import). ``suppressed``
    is True when the organization's do-not-contact list has a call entry for this
    lead's phone or email; ``lead.extra["suppressed"]`` is still honoured. Opt-out
    is read from ``lead.extra["opted_out"]``. Inbound-reply windows are deliberately
    not used for calls, so a call always needs explicit consent.

    The timezone is the lead's own valid IANA name when it has one. Otherwise it is
    left None here and :func:`evaluate_lead` decides the fallback.
    """
    extra = lead.extra or {}
    raw_consent = str(extra.get("consent") or "unknown").lower()
    return ContactState(
        consent=_CONSENT_MAP.get(raw_consent, "unknown"),  # type: ignore[arg-type]
        suppressed=suppressed or bool(extra.get("suppressed")),
        opted_out=bool(extra.get("opted_out")),
        timezone=_contact_timezone(lead),
        last_inbound_at=None,
        attempts_last_24h=attempts_last_24h,
    )


def evaluate_lead(
    lead: Lead,
    *,
    attempts_last_24h: int,
    now: datetime,
    org_timezone: str,
    suppressed: bool = False,
) -> Decision:
    """Decide whether this lead may be dialed now.

    Quiet hours are judged in one timezone, chosen in this order:
    1. The contact's own timezone (``lead.extra["timezone"]``, a valid IANA name).
    2. The campaign timezone, but only when the number's country calling code is
       recognised. Without a recognised code the campaign timezone says nothing about
       the contact, so the lead is not dialed.
    """
    reasons: list[str] = []
    problem = _phone_problem(lead.phone)
    if problem:
        reasons.append(problem)

    state = contact_state_for(
        lead, attempts_last_24h=attempts_last_24h, suppressed=suppressed
    )
    if state.timezone is None:
        if _country_code_known(lead.phone):
            state = replace(state, timezone=org_timezone)
        else:
            reasons.append(
                "We cannot tell this contact's timezone. Add a timezone to the lead, "
                "or use a number that starts with a recognised country code."
            )

    policy = check_outbound(
        contact=state, channel="call", now=now, org_timezone=org_timezone
    )
    reasons.extend(policy.reasons)
    return Decision(not reasons, reasons)


async def _recent_attempt_counts(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    lead_ids: Iterable[uuid.UUID],
    now: datetime,
) -> dict[uuid.UUID, int]:
    ids = list(lead_ids)
    if not ids:
        return {}
    rows = await session.execute(
        select(CallAttempt.lead_id, func.count(CallAttempt.id))
        .where(CallAttempt.organization_id == organization_id)
        .where(CallAttempt.lead_id.in_(ids))
        .where(CallAttempt.status.in_(AttemptStatus.COUNTED))
        .where(CallAttempt.attempted_at >= now - timedelta(hours=24))
        .group_by(CallAttempt.lead_id)
    )
    return {lead_id: int(n) for lead_id, n in rows.all()}


# ─────────────────────────── campaigns and planning ───────────────────────────


async def select_leads(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    lead_ids: Optional[list[uuid.UUID]] = None,
    lead_status: Optional[str] = None,
    lead_temperature: Optional[str] = None,
) -> list[Lead]:
    stmt = (
        select(Lead)
        .where(Lead.organization_id == organization_id)
        .where(Lead.project_id == project_id)
        .where(Lead.deleted_at.is_(None))
    )
    if lead_ids:
        stmt = stmt.where(Lead.id.in_(lead_ids))
    if lead_status:
        stmt = stmt.where(Lead.status == lead_status)
    if lead_temperature:
        stmt = stmt.where(Lead.temperature == lead_temperature)
    stmt = stmt.order_by(Lead.created_at, Lead.id).limit(MAX_CAMPAIGN_LEADS)
    return list((await session.scalars(stmt)).all())


async def create_campaign(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    created_by: uuid.UUID,
    name: str,
    timezone_name: str,
    leads: list[Lead],
    now: Optional[datetime] = None,
) -> CallCampaign:
    """Create a draft campaign and plan its attempts. The caller commits."""
    if not leads:
        raise CampaignError(422, "No leads matched, so there is nothing to call.")
    campaign = CallCampaign(
        id=uuid.uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        name=name,
        status=CampaignStatus.draft,
        timezone=validate_timezone(timezone_name),
        created_by=created_by,
    )
    session.add(campaign)
    await session.flush()
    await plan_attempts(session, campaign=campaign, leads=leads, now=now)
    return campaign


async def plan_attempts(
    session: AsyncSession,
    *,
    campaign: CallCampaign,
    leads: list[Lead],
    now: Optional[datetime] = None,
) -> dict[str, int]:
    """Create one attempt per distinct lead: ``queued`` if allowed, else ``skipped``."""
    now = now or _now()
    unique: dict[uuid.UUID, Lead] = {}
    for lead in leads:
        if lead.organization_id == campaign.organization_id:
            unique.setdefault(lead.id, lead)
    counts = await _recent_attempt_counts(
        session,
        organization_id=campaign.organization_id,
        lead_ids=unique.keys(),
        now=now,
    )
    suppressed = await contact_policy_service.suppressed_lead_ids(
        session,
        organization_id=campaign.organization_id,
        leads=unique.values(),
        channel="call",
    )
    summary = {"queued": 0, "skipped": 0}
    for lead in unique.values():
        decision = evaluate_lead(
            lead,
            attempts_last_24h=counts.get(lead.id, 0),
            now=now,
            org_timezone=campaign.timezone,
            suppressed=lead.id in suppressed,
        )
        if decision.allowed:
            status, reason = AttemptStatus.queued, None
            summary["queued"] += 1
        else:
            status, reason = AttemptStatus.skipped, " ".join(decision.reasons)
            summary["skipped"] += 1
        session.add(
            CallAttempt(
                id=uuid.uuid4(),
                organization_id=campaign.organization_id,
                campaign_id=campaign.id,
                lead_id=lead.id,
                status=status,
                skip_reason=reason,
            )
        )
    await session.flush()
    return summary


# ─────────────────────────── queue ───────────────────────────


class CallLookupError(Exception):
    """Twilio could not tell us whether a call is still active. Not proof that it ended."""


async def fetch_call_status(call_sid: str) -> Optional[str]:
    """Ask Twilio for a call's status with ``GET Calls/{sid}.json``.

    Returns the lowercase CallStatus (for example ``in-progress`` or ``completed``).
    Returns None when Twilio answers 404, meaning it has no such call. Raises
    :class:`CallLookupError` for any other failure, including missing configuration.
    """
    cfg = get_channels_config()
    if not (cfg.twilio_account_sid and cfg.twilio_auth_token and call_sid):
        raise CallLookupError("Twilio credentials are not configured.")
    url = f"{TWILIO_API_BASE}/Accounts/{cfg.twilio_account_sid}/Calls/{call_sid}.json"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(
                url, auth=(cfg.twilio_account_sid, cfg.twilio_auth_token)
            )
    except httpx.HTTPError as e:
        raise CallLookupError(f"Could not reach Twilio ({type(e).__name__}).") from e
    if resp.status_code == 404:
        return None
    if resp.status_code >= 400:
        raise CallLookupError(
            f"Twilio returned HTTP {resp.status_code} for the call lookup."
        )
    try:
        status = resp.json().get("status")
    except ValueError as e:
        raise CallLookupError("Twilio returned an unreadable call lookup.") from e
    if not isinstance(status, str) or not status:
        raise CallLookupError("Twilio returned no call status.")
    return status.lower()


async def _has_active_call(
    session: AsyncSession, campaign_id: uuid.UUID, now: datetime
) -> bool:
    """True when a call is in progress.

    A ``calling`` attempt older than ``STALE_CALL_AFTER`` has lost its status callback.
    It is released only when Twilio shows the call has ended, or when Twilio says it
    has no such call (404). Every other case, including a failed lookup, keeps the
    attempt ``calling`` so a second dial cannot start over a live call. An attempt
    with no Twilio call id is also kept, because nothing proves it is not live.
    """
    calling = (
        await session.scalars(
            select(CallAttempt)
            .where(CallAttempt.campaign_id == campaign_id)
            .where(CallAttempt.status == AttemptStatus.calling)
        )
    ).all()
    active = False
    changed = False
    for attempt in calling:
        if not attempt.attempted_at or attempt.attempted_at >= now - STALE_CALL_AFTER:
            active = True
            continue
        if not attempt.twilio_call_sid:
            active = True
            continue
        try:
            twilio_status = await fetch_call_status(attempt.twilio_call_sid)
        except CallLookupError:
            log.warning("call_status_lookup_failed attempt=%s", attempt.id)
            active = True
            continue
        if twilio_status is None:
            attempt.status = AttemptStatus.failed
            attempt.outcome = "not_found_at_twilio"
        elif twilio_status in _COMPLETED_STATUSES:
            attempt.status = AttemptStatus.completed
            attempt.outcome = twilio_status
        elif twilio_status in _FAILED_STATUSES:
            attempt.status = AttemptStatus.failed
            attempt.outcome = twilio_status
        else:
            active = True
            continue
        changed = True
    if changed:
        await session.flush()
    return active


async def next_call(
    session: AsyncSession, *, campaign_id: uuid.UUID
) -> Optional[CallAttempt]:
    """Return the next queued attempt, or None when a call is already in progress."""
    now = _now()
    if await _has_active_call(session, campaign_id, now):
        return None
    return await session.scalar(
        select(CallAttempt)
        .where(CallAttempt.campaign_id == campaign_id)
        .where(CallAttempt.status == AttemptStatus.queued)
        .order_by(CallAttempt.created_at, CallAttempt.id)
        .limit(1)
    )


async def dial_next(
    session: AsyncSession, *, campaign_id: uuid.UUID, now: Optional[datetime] = None
) -> Optional[CallAttempt]:
    """Claim the next allowed attempt and place its call. Commits.

    Returns the attempt that was dialed (its status says whether Twilio accepted
    it), or None when nothing was dialed: the campaign is not running, a call is
    already in progress, or the queue is empty (the campaign is then completed).
    Raises :class:`CallingNotConfigured` before claiming anything when calling is
    not configured.
    """
    require_calling_config()
    now = now or _now()

    campaign = await session.scalar(
        select(CallCampaign).where(CallCampaign.id == campaign_id).with_for_update()
    )
    if campaign is None or campaign.status != CampaignStatus.running:
        await session.commit()
        return None
    if await _has_active_call(session, campaign.id, now):
        await session.commit()
        return None

    claimed: Optional[CallAttempt] = None
    lead: Optional[Lead] = None
    while True:
        attempt = await session.scalar(
            select(CallAttempt)
            .where(CallAttempt.campaign_id == campaign.id)
            .where(CallAttempt.status == AttemptStatus.queued)
            .order_by(CallAttempt.created_at, CallAttempt.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if attempt is None:
            campaign.status = CampaignStatus.completed
            await session.commit()
            return None

        candidate = await session.get(Lead, attempt.lead_id)
        if (
            candidate is None
            or candidate.deleted_at is not None
            or candidate.organization_id != campaign.organization_id
        ):
            attempt.status = AttemptStatus.skipped
            attempt.skip_reason = "This lead was removed before it could be called."
            await session.flush()
            continue

        counts = await _recent_attempt_counts(
            session,
            organization_id=campaign.organization_id,
            lead_ids=[candidate.id],
            now=now,
        )
        # Re-checked at dial time: a do-not-call entry may have been added after planning.
        suppressed = await contact_policy_service.is_lead_suppressed(
            session, lead=candidate, channel="call"
        )
        decision = evaluate_lead(
            candidate,
            attempts_last_24h=counts.get(candidate.id, 0),
            now=now,
            org_timezone=campaign.timezone,
            suppressed=suppressed,
        )
        if not decision.allowed:
            # Re-checked at dial time: quiet hours and the daily cap can change after planning.
            attempt.status = AttemptStatus.skipped
            attempt.skip_reason = " ".join(decision.reasons)
            await session.flush()
            continue

        attempt.status = AttemptStatus.calling
        attempt.attempted_at = now
        claimed, lead = attempt, candidate
        break

    # Record the claim before talking to Twilio so the queue stays locked by state.
    await session.commit()

    try:
        sid = await place_call(claimed, to_number=lead.phone or "")
    except DialError as e:
        claimed.status = AttemptStatus.failed
        claimed.outcome = f"dial_error_{e.status_code}"
        await session.commit()
        log.warning(
            "call_dial_failed campaign=%s attempt=%s http=%s",
            campaign_id,
            claimed.id,
            e.status_code,
        )
        return claimed

    claimed.twilio_call_sid = sid
    await session.commit()
    log.info("call_placed campaign=%s attempt=%s", campaign_id, claimed.id)
    return claimed


async def place_call(attempt: CallAttempt, *, to_number: str) -> str:
    """Ask Twilio Voice to call ``to_number``. Returns the Twilio call SID.

    Refuses without calling Twilio when configuration is missing or the number
    is not E.164. Raises :class:`DialError` if Twilio does not accept the call.
    """
    require_calling_config()
    cfg = get_channels_config()
    if not _E164.match(to_number or ""):
        raise DialError(422, "Phone number is not in E.164 format.")

    base = cfg.public_api_base_url
    url = f"{TWILIO_API_BASE}/Accounts/{cfg.twilio_account_sid}/Calls.json"
    data = {
        "From": cfg.twilio_phone_number,
        "To": to_number,
        "Url": f"{base}/api/voice/twiml?attempt={attempt.id}",
        "StatusCallback": f"{base}/api/voice/status",
    }
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                url, data=data, auth=(cfg.twilio_account_sid, cfg.twilio_auth_token)
            )
    except httpx.HTTPError as e:
        raise DialError(502, f"Could not reach Twilio ({type(e).__name__}).") from e
    if resp.status_code >= 400:
        raise DialError(
            resp.status_code, f"Twilio refused the call (HTTP {resp.status_code})."
        )
    try:
        sid = str(resp.json().get("sid") or "")
    except ValueError:
        sid = ""
    if not sid:
        raise DialError(502, "Twilio returned no call id.")
    return sid


# ─────────────────────────── status callback ───────────────────────────


async def record_call_status(
    session: AsyncSession,
    *,
    call_sid: str,
    call_status: str,
    duration: Optional[str] = None,
) -> Optional[StatusTransition]:
    """Apply a Twilio CallStatus to the attempt. Does not commit.

    Returns a transition only when the attempt moved from ``calling`` to a final
    state, so the caller can advance the queue exactly once per call.
    """
    attempt = await session.scalar(
        select(CallAttempt)
        .where(CallAttempt.twilio_call_sid == call_sid)
        .with_for_update()
    )
    if attempt is None or attempt.status != AttemptStatus.calling:
        return None
    if call_status in _COMPLETED_STATUSES:
        attempt.status = AttemptStatus.completed
    elif call_status in _FAILED_STATUSES:
        attempt.status = AttemptStatus.failed
    else:
        return None  # queued / initiated / ringing / in-progress: still calling
    attempt.outcome = call_status
    try:
        attempt.duration_seconds = int(duration) if duration not in (None, "") else None
    except (TypeError, ValueError):
        attempt.duration_seconds = None
    await session.flush()
    return StatusTransition(campaign_id=attempt.campaign_id)


# ─────────────────────────── lifecycle ───────────────────────────


def can_start(status: str) -> bool:
    return status in (CampaignStatus.draft, CampaignStatus.paused)


def can_pause(status: str) -> bool:
    return status == CampaignStatus.running


async def campaign_counts(
    session: AsyncSession, campaign_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, dict[str, int]]:
    ids = list(campaign_ids)
    out: dict[uuid.UUID, dict[str, int]] = {
        cid: {s: 0 for s in AttemptStatus.ALL} | {"total": 0} for cid in ids
    }
    if not ids:
        return out
    rows = await session.execute(
        select(CallAttempt.campaign_id, CallAttempt.status, func.count(CallAttempt.id))
        .where(CallAttempt.campaign_id.in_(ids))
        .group_by(CallAttempt.campaign_id, CallAttempt.status)
    )
    for cid, status, n in rows.all():
        out[cid][status] = int(n)
        out[cid]["total"] += int(n)
    return out
