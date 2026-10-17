"""Do-not-contact lookups, edits and STOP-reply opt-outs.

This module touches the database. The decision logic stays in
:mod:`app.services.outreach_policy`, which is pure: callers ask this module
whether a contact is suppressed for a channel and pass the answer in as
``suppressed=True``.

Values are normalised before they are stored or matched: emails are lowercased,
phone numbers keep digits and a leading ``+``. Inbound replies and leads go
through the same normalisation, so they match the same rows.

Services here flush but do not commit. The caller commits.
"""

from __future__ import annotations

import re
import uuid
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.do_not_contact import ContactScope, ContactSource, DoNotContact
from app.services.visitor_service import normalize_email, normalize_phone

_STOP_PHRASES = frozenset(
    {"stop", "stopall", "stop all", "unsubscribe", "opt out", "optout", "opt-out"}
)
_PUNCTUATION = re.compile(r"[^\w\s-]")
_E164_LIKE = re.compile(r"^\+[1-9]\d{6,14}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_REASON_LENGTH = 200


class ContactEntryError(ValueError):
    """Plain-language reason an entry cannot be added."""


def normalise_value(raw: Optional[str]) -> Optional[str]:
    """Normalise a phone number or email for matching. Returns None when unusable."""
    if not raw:
        return None
    if "@" in raw:
        return normalize_email(raw)
    return normalize_phone(raw)


def normalise_entry_value(raw: str) -> str:
    """Validate and normalise a value typed in by a user. Raises ContactEntryError."""
    value = (raw or "").strip()
    if not value:
        raise ContactEntryError("Enter a phone number or an email address.")
    if "@" in value:
        email = normalize_email(value)
        if email is None or not _EMAIL.match(email):
            raise ContactEntryError("That email address does not look valid.")
        return email
    phone = normalize_phone(value)
    if phone is None or not _E164_LIKE.match(phone):
        raise ContactEntryError(
            "Enter the phone number in international format, starting with + and the country code."
        )
    return phone


def is_opt_out_message(text: Optional[str]) -> bool:
    """True when the whole message is a STOP-style request (STOP, UNSUBSCRIBE, OPT OUT)."""
    if not text:
        return False
    cleaned = _PUNCTUATION.sub("", text.strip().lower())
    cleaned = " ".join(cleaned.split())
    return cleaned in _STOP_PHRASES


def _scopes_for(channel: str) -> tuple[str, ...]:
    if channel in ContactScope.CHANNELS:
        return (ContactScope.all, channel)
    return (ContactScope.all,)


async def is_suppressed(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    values: Iterable[Optional[str]],
    channel: str,
) -> bool:
    """True when any of ``values`` is on this organization's list for ``channel``."""
    wanted = {v for v in (normalise_value(x) for x in values) if v}
    if not wanted:
        return False
    row = await session.scalar(
        select(DoNotContact.id)
        .where(DoNotContact.organization_id == organization_id)
        .where(DoNotContact.normalised_value.in_(wanted))
        .where(DoNotContact.channel_scope.in_(_scopes_for(channel)))
        .limit(1)
    )
    return row is not None


async def is_lead_suppressed(session: AsyncSession, *, lead, channel: str) -> bool:
    """Suppression check for one lead's phone and email."""
    return await is_suppressed(
        session,
        organization_id=lead.organization_id,
        values=[lead.phone, lead.email],
        channel=channel,
    )


async def suppressed_lead_ids(
    session: AsyncSession, *, organization_id: uuid.UUID, leads: Iterable, channel: str
) -> set[uuid.UUID]:
    """Batch form of :func:`is_lead_suppressed` for campaign planning (one query)."""
    lead_list = [lead for lead in leads if lead.organization_id == organization_id]
    per_lead: dict[uuid.UUID, set[str]] = {}
    for lead in lead_list:
        values = {
            v for v in (normalise_value(lead.phone), normalise_value(lead.email)) if v
        }
        if values:
            per_lead[lead.id] = values
    if not per_lead:
        return set()
    all_values: set[str] = set().union(*per_lead.values())
    rows = await session.scalars(
        select(DoNotContact.normalised_value)
        .where(DoNotContact.organization_id == organization_id)
        .where(DoNotContact.normalised_value.in_(all_values))
        .where(DoNotContact.channel_scope.in_(_scopes_for(channel)))
    )
    hit = set(rows.all())
    return {lead_id for lead_id, values in per_lead.items() if values & hit}


async def record_opt_out(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    values: Iterable[Optional[str]],
    reason: str = "STOP reply",
) -> int:
    """Add an ``all``-channel opt-out for each value. Idempotent. Returns rows added."""
    wanted = sorted({v for v in (normalise_value(x) for x in values) if v})
    if not wanted:
        return 0
    result = await session.execute(
        pg_insert(DoNotContact)
        .values(
            [
                {
                    "id": uuid.uuid4(),
                    "organization_id": organization_id,
                    "normalised_value": value,
                    "channel_scope": ContactScope.all,
                    "reason": reason[:MAX_REASON_LENGTH],
                    "source": ContactSource.opt_out_reply,
                    "created_by": None,
                }
                for value in wanted
            ]
        )
        .on_conflict_do_nothing(constraint="uq_do_not_contact_org_value_scope")
    )
    await session.flush()
    return int(result.rowcount or 0)


async def list_entries(
    session: AsyncSession, *, organization_id: uuid.UUID
) -> list[DoNotContact]:
    rows = await session.scalars(
        select(DoNotContact)
        .where(DoNotContact.organization_id == organization_id)
        .order_by(DoNotContact.created_at.desc(), DoNotContact.id)
        .limit(1000)
    )
    return list(rows.all())


async def add_entry(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    raw_value: str,
    channel_scope: str,
    reason: str,
    created_by: Optional[uuid.UUID],
) -> tuple[DoNotContact, bool]:
    """Add one entry. Returns (entry, created). An existing identical entry is returned as-is."""
    if channel_scope not in ContactScope.ALL:
        raise ContactEntryError(
            "Choose a channel: all, call, sms, whatsapp, email or instagram."
        )
    value = normalise_entry_value(raw_value)
    existing = await session.scalar(
        select(DoNotContact)
        .where(DoNotContact.organization_id == organization_id)
        .where(DoNotContact.normalised_value == value)
        .where(DoNotContact.channel_scope == channel_scope)
    )
    if existing is not None:
        return existing, False
    entry = DoNotContact(
        id=uuid.uuid4(),
        organization_id=organization_id,
        normalised_value=value,
        channel_scope=channel_scope,
        reason=(reason or "").strip()[:MAX_REASON_LENGTH],
        source=ContactSource.user,
        created_by=created_by,
    )
    session.add(entry)
    await session.flush()
    return entry, True


async def remove_entry(
    session: AsyncSession, *, organization_id: uuid.UUID, entry_id: uuid.UUID
) -> bool:
    """Delete one entry in this organization. Returns False when it does not exist here."""
    entry = await session.scalar(
        select(DoNotContact)
        .where(DoNotContact.id == entry_id)
        .where(DoNotContact.organization_id == organization_id)
    )
    if entry is None:
        return False
    await session.delete(entry)
    await session.flush()
    return True
