"""Outbound contact policy: may we call or message this person right now?

Every outbound call or message must pass :func:`check_outbound` before it is
sent. The module is pure (no database, no network) so the rules are easy to
audit and test. Callers pass in the contact's current consent and suppression
state and receive a decision with plain-language reasons.

Rules, in order:
1. Suppressed or opted out: never contact.
2. Consent withdrawn: never contact.
3. Consent: outbound needs consent, except a reply (``is_reply=True``) to an
   inbound message received within the last 24 hours. The reply window waives
   consent only.
4. Quiet hours in the contact's local time: blocked for every outbound call or
   message, replies included (default 08:00 to 21:00 local).
5. Attempt cap: no more than ``max_attempts_per_day`` outbound attempts per
   contact in a rolling 24 hours, replies included.

``is_reply`` defaults to False, so a caller that does not say it is replying is
treated as proactive. Only the caller that handles an inbound message in the
window may pass ``is_reply=True``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

Consent = Literal["given", "unknown", "withdrawn"]
Channel = Literal["call", "whatsapp", "sms", "email", "instagram"]

DEFAULT_QUIET_START = time(21, 0)  # no outbound after 21:00 local
DEFAULT_QUIET_END = time(8, 0)  # ...or before 08:00 local
DEFAULT_MAX_ATTEMPTS_PER_DAY = 2
REPLY_WINDOW = timedelta(hours=24)


@dataclass(frozen=True)
class ContactState:
    consent: Consent = "unknown"
    suppressed: bool = False  # on the organization's do-not-contact list
    opted_out: bool = False  # contact replied STOP / asked not to be contacted
    timezone: Optional[str] = None  # IANA name, e.g. "Europe/London"
    last_inbound_at: Optional[datetime] = None  # last time the contact messaged us
    attempts_last_24h: int = 0


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


def _local_time(now: datetime, tz_name: Optional[str], fallback: str) -> time:
    try:
        zone = ZoneInfo(tz_name or fallback)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo(fallback)
    local = now.astimezone(zone) if now.tzinfo else now.replace(tzinfo=zone)
    return local.time()


def _inside_reply_window(last_inbound_at: Optional[datetime], now: datetime) -> bool:
    """True when the contact messaged us within the last 24 hours, not in the future."""
    if last_inbound_at is None:
        return False
    return timedelta(0) <= now - last_inbound_at <= REPLY_WINDOW


def in_quiet_hours(
    local: time, start: time = DEFAULT_QUIET_START, end: time = DEFAULT_QUIET_END
) -> bool:
    """True when ``local`` falls in the quiet window, which may wrap past midnight."""
    if start <= end:
        return start <= local < end
    return local >= start or local < end


def check_outbound(
    *,
    contact: ContactState,
    channel: Channel,
    now: datetime,
    org_timezone: str = "UTC",
    max_attempts_per_day: int = DEFAULT_MAX_ATTEMPTS_PER_DAY,
    is_reply: bool = False,
) -> Decision:
    """Decide whether we may contact this person on ``channel`` at ``now``.

    ``is_reply`` must be True only when answering an inbound message. It waives
    the consent requirement when the inbound message is inside the reply window.
    It never waives quiet hours or the attempt cap.
    """
    if contact.suppressed:
        return Decision(False, ["This contact is on your do-not-contact list."])
    if contact.opted_out:
        return Decision(False, ["This contact asked not to be contacted."])
    if contact.consent == "withdrawn":
        return Decision(False, ["This contact withdrew consent."])

    replying = is_reply and _inside_reply_window(contact.last_inbound_at, now)

    reasons: list[str] = []
    if contact.consent != "given" and not replying:
        reasons.append("We do not have this contact's consent to reach out.")
    if in_quiet_hours(_local_time(now, contact.timezone, org_timezone)):
        reasons.append(
            "It is outside calling hours for this contact (08:00 to 21:00 local)."
        )
    if contact.attempts_last_24h >= max_attempts_per_day:
        reasons.append(
            f"This contact has reached today's limit of {max_attempts_per_day} attempts."
        )
    return Decision(not reasons, reasons)
