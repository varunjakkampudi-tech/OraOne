"""Signed unsubscribe links for marketing email.

A token names the organization, the campaign recipient and an expiry. It carries no
email address, so the link does not expose the contact. The signature is an HMAC over
the payload, keyed from the server's JWT secret with a purpose label so the same secret
cannot be replayed for another token type. Tokens expire 90 days after they are issued.

Verification is pure (no database). Applying a token adds an ``email`` do-not-contact
entry through :mod:`app.services.contact_policy_service`; the caller commits.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models.lead import Lead
from app.database.models.marketing import MarketingRecipient
from app.services import contact_policy_service
from app.services.visitor_service import normalize_email

TOKEN_TTL = timedelta(days=90)
UNSUBSCRIBE_REASON = "Marketing unsubscribe"
_KEY_PURPOSE = b"oraone:marketing-unsubscribe:v1"


class InvalidUnsubscribeToken(ValueError):
    """Plain-language reason a link cannot be used."""


@dataclass(frozen=True)
class UnsubscribeClaim:
    organization_id: uuid.UUID
    recipient_id: uuid.UUID
    expires_at: datetime


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _signing_key() -> bytes:
    # Derive a purpose-specific key from the server secret; the raw secret never signs anything directly.
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"), _KEY_PURPOSE, hashlib.sha256
    ).digest()


def _sign(body: str) -> str:
    return _b64encode(
        hmac.new(_signing_key(), body.encode("ascii"), hashlib.sha256).digest()
    )


def make_unsubscribe_token(
    *,
    organization_id: uuid.UUID,
    recipient_id: uuid.UUID,
    now: Optional[datetime] = None,
) -> str:
    issued = now or _utcnow()
    payload = {
        "o": str(organization_id),
        "r": str(recipient_id),
        "e": int((issued + TOKEN_TTL).timestamp()),
    }
    body = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    return f"{body}.{_sign(body)}"


def parse_unsubscribe_token(
    token: str, *, now: Optional[datetime] = None
) -> UnsubscribeClaim:
    """Check the signature and expiry, then return the claim. Raises InvalidUnsubscribeToken."""
    invalid = InvalidUnsubscribeToken("This unsubscribe link is not valid.")
    if not token or token.count(".") != 1 or len(token) > 1024:
        raise invalid
    body, signature = token.split(".", 1)
    if not hmac.compare_digest(_sign(body), signature):
        raise invalid
    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
        claim = UnsubscribeClaim(
            organization_id=uuid.UUID(str(payload["o"])),
            recipient_id=uuid.UUID(str(payload["r"])),
            expires_at=datetime.fromtimestamp(int(payload["e"]), tz=timezone.utc),
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        binascii.Error,
        json.JSONDecodeError,
    ) as exc:
        raise invalid from exc
    current = now or _utcnow()
    if current >= claim.expires_at:
        raise InvalidUnsubscribeToken(
            "This unsubscribe link has expired. Ask the sender for a new one."
        )
    return claim


async def apply_unsubscribe(
    session: AsyncSession, token: str, *, now: Optional[datetime] = None
) -> str:
    """Add an email do-not-contact entry for the recipient named in the token. Returns the entry reason.

    Only the signed organization is used, so one token cannot reach another tenant's list.
    """
    claim = parse_unsubscribe_token(token, now=now)
    recipient = await session.scalar(
        select(MarketingRecipient)
        .where(MarketingRecipient.id == claim.recipient_id)
        .where(MarketingRecipient.organization_id == claim.organization_id)
    )
    if recipient is None:
        raise InvalidUnsubscribeToken("This unsubscribe link is not valid.")
    lead = await session.scalar(
        select(Lead)
        .where(Lead.id == recipient.lead_id)
        .where(Lead.organization_id == claim.organization_id)
    )
    address = normalize_email(lead.email) if lead is not None and lead.email else None
    if not address:
        raise InvalidUnsubscribeToken(
            "We could not find an email address for this link."
        )
    try:
        await contact_policy_service.add_entry(
            session,
            organization_id=claim.organization_id,
            raw_value=address,
            channel_scope="email",
            reason=UNSUBSCRIBE_REASON,
            created_by=None,
        )
    except contact_policy_service.ContactEntryError as exc:
        raise InvalidUnsubscribeToken(
            "We could not find a valid email address for this link."
        ) from exc
    return UNSUBSCRIBE_REASON
