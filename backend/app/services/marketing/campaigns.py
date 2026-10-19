"""Marketing campaigns: plan recipients against consent, send through the sender registry.

Planning (``create_campaign``) runs :func:`check_outbound` for every lead with the
reply window switched off (``is_reply=False``), so only consent, do-not-contact,
opt-outs, quiet hours and the daily attempt cap decide. Every skip gets a plain-language
reason that is stored on the recipient.

Sending is batched. ``begin_send`` claims the campaign with one conditional UPDATE
(only ``draft`` or ``scheduled`` can move to ``sending``), so a second send cannot
start while the first is running. ``send_next_batch`` is the worker unit: it takes a
batch of queued recipients, re-checks the policy at send time, and calls the sender
registry. A recipient is ``sent`` only when the sender returns without raising.

Services here flush but do not commit. The caller commits between batches.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.lead import Lead
from app.database.models.marketing import (
    MarketingCampaign,
    MarketingCampaignStatus,
    MarketingChannel,
    MarketingRecipient,
    MarketingRecipientStatus,
)
from app.services import contact_policy_service
from app.services.marketing.unsubscribe import make_unsubscribe_token
from app.services.outreach_policy import ContactState, check_outbound
from app.services.visitor_service import normalize_email
from app.services.workflow_senders import OutboundNotConfigured

log = logging.getLogger("app.marketing.campaigns")

MAX_RECIPIENTS = 500
SEND_BATCH_SIZE = 25
# A recipient still "sending" this long after its claim was taken was interrupted.
SENDING_CLAIM_TIMEOUT = timedelta(minutes=15)
MAX_NAME_LENGTH = 120
MAX_SUBJECT_LENGTH = 200
MAX_BODY_LENGTH = 10_000
EMAIL_NO_PROVIDER_REASON = "No email delivery provider is connected yet"
UNSUBSCRIBE_UNAVAILABLE_REASON = (
    "The unsubscribe link cannot be built because PUBLIC_API_BASE_URL is not set on the server, "
    "so the email was not sent."
)
PROVIDER_REFUSED_REASON = "The provider did not accept the message."

_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CONSENT_STATES = {
    "granted": "given",
    "given": "given",
    "denied": "withdrawn",
    "withdrawn": "withdrawn",
}
_PLAIN_REASONS = {
    "It is outside calling hours for this contact (08:00 to 21:00 local).": (
        "It is outside messaging hours (08:00 to 21:00 in the contact's time zone)."
    ),
}


class CampaignError(ValueError):
    """Plain-language reason a request cannot be completed. Safe to show to users."""


class CampaignNotFound(CampaignError):
    pass


class CampaignConflict(CampaignError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_campaign_input(
    *,
    name: str,
    channel: str,
    subject: Optional[str],
    body: str,
    lead_ids: Sequence[uuid.UUID],
) -> None:
    if not name.strip():
        raise CampaignError("Give the campaign a name.")
    if len(name.strip()) > MAX_NAME_LENGTH:
        raise CampaignError(
            f"The campaign name must be {MAX_NAME_LENGTH} characters or fewer."
        )
    if channel not in MarketingChannel.ALL:
        raise CampaignError("Choose a channel: email, SMS or WhatsApp.")
    if channel == MarketingChannel.email and not (subject or "").strip():
        raise CampaignError("Email campaigns need a subject line.")
    if subject is not None and len(subject) > MAX_SUBJECT_LENGTH:
        raise CampaignError(
            f"The subject must be {MAX_SUBJECT_LENGTH} characters or fewer."
        )
    if not body.strip():
        raise CampaignError("Write the message before saving the campaign.")
    if len(body) > MAX_BODY_LENGTH:
        raise CampaignError(
            f"The message must be {MAX_BODY_LENGTH} characters or fewer."
        )
    if not lead_ids:
        raise CampaignError("Choose at least one lead.")
    if len(set(lead_ids)) > MAX_RECIPIENTS:
        raise CampaignError(f"A campaign can reach at most {MAX_RECIPIENTS} leads.")


def address_for(channel: str, lead: Any) -> tuple[Optional[str], Optional[str]]:
    """The address a message goes to, or a plain-language reason there is none."""
    if channel == MarketingChannel.email:
        email = normalize_email(lead.email) if lead.email else None
        if not email:
            return None, "This lead has no email address."
        if not _EMAIL_SHAPE.match(email):
            return None, "The email address does not look valid."
        return email, None
    raw = (lead.phone or "").strip()
    if not raw:
        return None, "This lead has no phone number."
    phone = contact_policy_service.normalise_value(raw)
    if not phone or not phone.startswith("+"):
        return None, "The phone number needs a + and a country code."
    return phone, None


def policy_reasons(
    *,
    lead: Any,
    channel: str,
    suppressed: bool,
    attempts_last_24h: int,
    now: datetime,
    org_timezone: str = "UTC",
) -> list[str]:
    """Every reason the policy refuses this lead right now. Empty when the message may go."""
    extra = lead.extra or {}
    tz_name = extra.get("timezone")
    state = ContactState(
        consent=_CONSENT_STATES.get(str(extra.get("consent") or "").lower(), "unknown"),  # type: ignore[arg-type]
        suppressed=suppressed or bool(extra.get("suppressed")),
        opted_out=bool(extra.get("opted_out")),
        timezone=tz_name if isinstance(tz_name, str) and tz_name else None,
        last_inbound_at=None,
        attempts_last_24h=attempts_last_24h,
    )
    decision = check_outbound(
        contact=state,
        channel=channel,  # type: ignore[arg-type]
        now=now,
        org_timezone=org_timezone,
        is_reply=False,
    )
    return [_PLAIN_REASONS.get(reason, reason) for reason in decision.reasons]


async def attempts_last_24h(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    lead_ids: Sequence[uuid.UUID],
    now: datetime,
) -> dict[uuid.UUID, int]:
    """Messages already sent to each lead in the rolling 24 hours (all channels count toward the cap)."""
    if not lead_ids:
        return {}
    rows = (
        await session.execute(
            select(MarketingRecipient.lead_id, func.count(MarketingRecipient.id))
            .where(MarketingRecipient.organization_id == organization_id)
            .where(MarketingRecipient.lead_id.in_(list(lead_ids)))
            .where(MarketingRecipient.status == MarketingRecipientStatus.sent)
            .where(MarketingRecipient.sent_at >= now - timedelta(hours=24))
            .group_by(MarketingRecipient.lead_id)
        )
    ).all()
    return {lead_id: int(count) for lead_id, count in rows}


async def get_campaign(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> MarketingCampaign:
    campaign = await session.scalar(
        select(MarketingCampaign)
        .where(MarketingCampaign.id == campaign_id)
        .where(MarketingCampaign.organization_id == organization_id)
        .where(MarketingCampaign.project_id == project_id)
    )
    if campaign is None:
        raise CampaignNotFound("Campaign not found.")
    return campaign


async def create_campaign(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    created_by: Optional[uuid.UUID],
    name: str,
    channel: str,
    subject: Optional[str],
    body: str,
    lead_ids: Sequence[uuid.UUID],
    now: Optional[datetime] = None,
    org_timezone: str = "UTC",
) -> MarketingCampaign:
    """Create a draft campaign and plan one recipient per lead. Returns the campaign."""
    validate_campaign_input(
        name=name, channel=channel, subject=subject, body=body, lead_ids=lead_ids
    )
    current = now or _utcnow()
    unique_ids = list(dict.fromkeys(lead_ids))

    leads = list(
        (
            await session.scalars(
                select(Lead)
                .where(Lead.organization_id == organization_id)
                .where(Lead.project_id == project_id)
                .where(Lead.deleted_at.is_(None))
                .where(Lead.id.in_(unique_ids))
            )
        ).all()
    )
    if len(leads) != len(unique_ids):
        raise CampaignError(
            "Some of the chosen leads are not in this workspace any more. Refresh the list and try again."
        )

    suppressed = await contact_policy_service.suppressed_lead_ids(
        session, organization_id=organization_id, leads=leads, channel=channel
    )
    attempts = await attempts_last_24h(
        session, organization_id=organization_id, lead_ids=unique_ids, now=current
    )

    campaign = MarketingCampaign(
        id=uuid.uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        name=name.strip(),
        channel=channel,
        subject=(subject or "").strip() or None,
        body=body,
        status=MarketingCampaignStatus.draft,
        created_by=created_by,
        sent_count=0,
        skipped_count=0,
        failed_count=0,
    )
    session.add(campaign)

    skipped = 0
    by_id = {lead.id: lead for lead in leads}
    for lead_id in unique_ids:
        lead = by_id[lead_id]
        address, problem = address_for(channel, lead)
        reasons = (
            [problem]
            if problem
            else policy_reasons(
                lead=lead,
                channel=channel,
                suppressed=lead.id in suppressed,
                attempts_last_24h=attempts.get(lead.id, 0),
                now=current,
                org_timezone=org_timezone,
            )
        )
        recipient = MarketingRecipient(
            id=uuid.uuid4(),
            organization_id=organization_id,
            campaign_id=campaign.id,
            lead_id=lead.id,
            status=MarketingRecipientStatus.skipped
            if reasons
            else MarketingRecipientStatus.queued,
            skip_reason=" ".join(reasons) if reasons else None,
            failure_reason=None,
            sent_at=None,
        )
        session.add(recipient)
        if reasons:
            skipped += 1
    campaign.skipped_count = skipped
    await session.flush()
    return campaign


async def list_campaigns(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    limit: int = 100,
) -> list[MarketingCampaign]:
    rows = await session.scalars(
        select(MarketingCampaign)
        .where(MarketingCampaign.organization_id == organization_id)
        .where(MarketingCampaign.project_id == project_id)
        .order_by(MarketingCampaign.created_at.desc(), MarketingCampaign.id)
        .limit(limit)
    )
    return list(rows.all())


async def get_campaign_with_recipients(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> tuple[
    MarketingCampaign,
    list[tuple[MarketingRecipient, Optional[str], Optional[str], Optional[str]]],
]:
    """The campaign and its recipients with lead name, email and phone for the breakdown."""
    campaign = await get_campaign(
        session,
        organization_id=organization_id,
        project_id=project_id,
        campaign_id=campaign_id,
    )
    rows = (
        await session.execute(
            select(MarketingRecipient, Lead.name, Lead.email, Lead.phone)
            .join(Lead, Lead.id == MarketingRecipient.lead_id)
            .where(MarketingRecipient.organization_id == organization_id)
            .where(MarketingRecipient.campaign_id == campaign.id)
            .order_by(MarketingRecipient.id)
            .limit(MAX_RECIPIENTS)
        )
    ).all()
    return campaign, [tuple(row) for row in rows]  # type: ignore[misc]


async def begin_send(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> MarketingCampaign:
    """Claim the campaign for sending. Only one caller can move it from draft or scheduled to sending."""
    campaign = await get_campaign(
        session,
        organization_id=organization_id,
        project_id=project_id,
        campaign_id=campaign_id,
    )
    if campaign.status not in MarketingCampaignStatus.EDITABLE:
        raise CampaignConflict(_already_done_message(campaign.status))
    claimed = (
        await session.execute(
            update(MarketingCampaign)
            .where(MarketingCampaign.id == campaign.id)
            .where(MarketingCampaign.organization_id == organization_id)
            .where(MarketingCampaign.status.in_(MarketingCampaignStatus.EDITABLE))
            .values(status=MarketingCampaignStatus.sending)
            .returning(MarketingCampaign.id)
        )
    ).all()
    if not claimed:
        raise CampaignConflict(
            "This campaign has already been sent or is being sent. No message was sent again."
        )
    campaign.status = MarketingCampaignStatus.sending
    return campaign


def _already_done_message(status: str) -> str:
    if status == MarketingCampaignStatus.cancelled:
        return "This campaign was cancelled, so it cannot be sent."
    if status == MarketingCampaignStatus.completed:
        return "This campaign has already been sent. No message was sent again."
    return "This campaign has already been sent or is being sent. No message was sent again."


def _message_text(
    campaign: MarketingCampaign, recipient_id: uuid.UUID, base_url: str, now: datetime
) -> str:
    if campaign.channel == MarketingChannel.email:
        token = make_unsubscribe_token(
            organization_id=campaign.organization_id, recipient_id=recipient_id, now=now
        )
        link = f"{base_url}/api/marketing/unsubscribe?token={token}"
        return f"{campaign.body.strip()}\n\n---\nTo stop these emails, unsubscribe: {link}\n"
    if campaign.channel == MarketingChannel.sms:
        return f"{campaign.body.strip()} Reply STOP to opt out."
    return campaign.body.strip()


async def _load_recipient_pair(
    session: AsyncSession, recipient_id: uuid.UUID, lead_id: uuid.UUID
):
    """Fresh copies of a recipient and its lead, read after a commit."""
    recipient = await session.get(MarketingRecipient, recipient_id)
    lead = await session.get(Lead, lead_id)
    return recipient, lead


async def send_next_batch(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
    sender: Any,
    unsubscribe_base_url: str,
    batch_size: int = SEND_BATCH_SIZE,
    now: Optional[datetime] = None,
) -> int:
    """Process up to ``batch_size`` queued recipients. Returns how many were handled (0 means done).

    Three phases, so that no database lock is held during a provider call:

    1. Claim: apply the consent and policy checks, mark eligible recipients
       ``sending``, and commit (this releases the row locks).
    2. Send: call the provider for each claimed recipient, without a transaction open.
    3. Record: write each outcome and the campaign counters, then commit.

    A claim that is still ``sending`` long after it was taken means the worker stopped
    during phase 2. The provider may already have accepted that message, so the claim is
    marked failed for review and is never resent automatically.
    """
    current = now or _utcnow()
    campaign = await get_campaign(
        session,
        organization_id=organization_id,
        project_id=project_id,
        campaign_id=campaign_id,
    )

    # Stale claims from an interrupted worker: outcome unknown, so never auto-resend.
    stale = list(
        (
            await session.scalars(
                select(MarketingRecipient)
                .where(MarketingRecipient.organization_id == organization_id)
                .where(MarketingRecipient.campaign_id == campaign.id)
                .where(MarketingRecipient.status == MarketingRecipientStatus.sending)
                .where(MarketingRecipient.claimed_at < current - SENDING_CLAIM_TIMEOUT)
            )
        ).all()
    )
    for recipient in stale:
        recipient.status = MarketingRecipientStatus.failed
        recipient.failure_reason = (
            "The send outcome is unknown after a worker interruption. "
            "It was not resent automatically; check the provider before sending again."
        )
        campaign.failed_count += 1

    # Phase 1: claim.
    rows = (
        await session.execute(
            select(MarketingRecipient, Lead)
            .join(Lead, Lead.id == MarketingRecipient.lead_id)
            .where(MarketingRecipient.organization_id == organization_id)
            .where(MarketingRecipient.campaign_id == campaign.id)
            .where(MarketingRecipient.status == MarketingRecipientStatus.queued)
            .order_by(MarketingRecipient.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True, of=MarketingRecipient)
        )
    ).all()
    if not rows:
        await session.commit()
        return 0

    leads = [lead for _, lead in rows]
    suppressed = await contact_policy_service.suppressed_lead_ids(
        session, organization_id=organization_id, leads=leads, channel=campaign.channel
    )
    attempts = await attempts_last_24h(
        session,
        organization_id=organization_id,
        lead_ids=[lead.id for lead in leads],
        now=current,
    )

    to_send: list[tuple[uuid.UUID, uuid.UUID, str]] = []
    for recipient, lead in rows:
        reasons = policy_reasons(
            lead=lead,
            channel=campaign.channel,
            suppressed=lead.id in suppressed,
            attempts_last_24h=attempts.get(lead.id, 0),
            now=current,
        )
        address, problem = address_for(campaign.channel, lead)
        if lead.deleted_at is not None:
            reasons = [
                "This lead was deleted after the campaign was created.",
                *reasons,
            ]
        elif problem:
            reasons = [problem, *reasons]
        if reasons:
            recipient.status = MarketingRecipientStatus.skipped
            recipient.skip_reason = " ".join(reasons)
            campaign.skipped_count += 1
            continue
        recipient.status = MarketingRecipientStatus.sending
        recipient.claimed_at = current
        to_send.append((recipient.id, lead.id, address or ""))

    # Release the row locks before any network call.
    await session.commit()
    await session.refresh(campaign)

    # Phase 2: send.
    outcomes: dict[uuid.UUID, Optional[str]] = {}
    for recipient_id, lead_id, address in to_send:
        recipient, lead = await _load_recipient_pair(session, recipient_id, lead_id)
        outcomes[recipient_id] = await _deliver(
            campaign,
            recipient=recipient,
            lead=lead,
            address=address,
            sender=sender,
            unsubscribe_base_url=unsubscribe_base_url,
            now=current,
        )

    # Phase 3: record.
    for recipient_id, failure in outcomes.items():
        recipient = await session.get(MarketingRecipient, recipient_id)
        if failure is None:
            recipient.status = MarketingRecipientStatus.sent
            recipient.sent_at = current
            recipient.failure_reason = None
            campaign.sent_count += 1
        else:
            recipient.status = MarketingRecipientStatus.failed
            recipient.failure_reason = failure
            campaign.failed_count += 1
    await session.commit()
    return len(rows)


class MarketingDeliveryStatus:
    """Delivery states reported by a provider, in the order they can progress."""

    sent = "sent"
    delivered = "delivered"
    read = "read"
    bounced = "bounced"
    failed = "failed"

    RANK = {sent: 0, delivered: 1, read: 2, bounced: 3, failed: 3}


def _as_message_id(response) -> str | None:
    """The provider's message id, when the sender returns one (a string or a dict with an 'id')."""
    if isinstance(response, str) and response.strip():
        return response.strip()[:200]
    if isinstance(response, dict):
        value = response.get("id") or response.get("message_id")
        if isinstance(value, str) and value.strip():
            return value.strip()[:200]
    return None


def receipt_advances(current: str | None, incoming: str) -> bool:
    """True when a receipt moves a message forward. Receipts can arrive out of order,
    so a state that is not further along than the current one is ignored."""
    if incoming not in MarketingDeliveryStatus.RANK:
        return False
    if current is None:
        return True
    return (
        MarketingDeliveryStatus.RANK[incoming] > MarketingDeliveryStatus.RANK[current]
    )


async def apply_delivery_receipt(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    provider_message_id: str,
    status: str,
    occurred_at: datetime,
) -> str:
    """Apply a provider's delivery receipt to the matching recipient.

    Returns "applied", "stale" (an older or non-advancing receipt), "ignored" (unknown state)
    or "unknown" (no recipient of this organization has that provider id).
    """
    recipient = await session.scalar(
        select(MarketingRecipient)
        .where(MarketingRecipient.organization_id == organization_id)
        .where(MarketingRecipient.provider_message_id == provider_message_id)
        .limit(1)
    )
    if recipient is None:
        return "unknown"
    if status not in MarketingDeliveryStatus.RANK:
        return "ignored"
    if (
        recipient.delivery_updated_at is not None
        and occurred_at < recipient.delivery_updated_at
    ):
        return "stale"
    if not receipt_advances(recipient.delivery_status, status):
        return "stale"
    recipient.delivery_status = status
    recipient.delivery_updated_at = occurred_at
    await session.flush()
    return "applied"


async def _deliver(
    campaign: MarketingCampaign,
    *,
    recipient: MarketingRecipient,
    lead: Lead,
    address: str,
    sender: Any,
    unsubscribe_base_url: str,
    now: datetime,
) -> Optional[str]:
    """Send one message. Returns None only when the sender returned without raising."""
    if campaign.channel == MarketingChannel.email and not unsubscribe_base_url:
        return UNSUBSCRIBE_UNAVAILABLE_REASON
    text = _message_text(campaign, recipient.id, unsubscribe_base_url.rstrip("/"), now)
    try:
        provider_response = await sender.send(
            channel=campaign.channel,
            recipient=address,
            text=text,
            organization_id=campaign.organization_id,
            lead_id=lead.id,
        )
        # Keep the provider's id so that later delivery receipts can be matched to this recipient.
        recipient.provider_message_id = _as_message_id(provider_response)
        recipient.delivery_status = (
            MarketingDeliveryStatus.sent if recipient.provider_message_id else None
        )
        recipient.delivery_updated_at = now if recipient.provider_message_id else None
    except OutboundNotConfigured as exc:
        if campaign.channel == MarketingChannel.email:
            return EMAIL_NO_PROVIDER_REASON
        return str(exc)
    except Exception:  # noqa: BLE001 - provider detail stays in the log only
        log.warning(
            "marketing send failed on %s for campaign %s", campaign.channel, campaign.id
        )
        return PROVIDER_REFUSED_REASON
    return None


async def complete_campaign(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> MarketingCampaign:
    """Mark a sending campaign completed once no queued recipients remain."""
    campaign = await get_campaign(
        session,
        organization_id=organization_id,
        project_id=project_id,
        campaign_id=campaign_id,
    )
    if campaign.status == MarketingCampaignStatus.sending:
        await session.execute(
            update(MarketingCampaign)
            .where(MarketingCampaign.id == campaign.id)
            .where(MarketingCampaign.organization_id == organization_id)
            .values(status=MarketingCampaignStatus.completed)
        )
        campaign.status = MarketingCampaignStatus.completed
    return campaign


async def cancel_campaign(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    campaign_id: uuid.UUID,
) -> MarketingCampaign:
    campaign = await get_campaign(
        session,
        organization_id=organization_id,
        project_id=project_id,
        campaign_id=campaign_id,
    )
    if campaign.status not in MarketingCampaignStatus.EDITABLE:
        raise CampaignConflict("Only a draft or scheduled campaign can be cancelled.")
    claimed = (
        await session.execute(
            update(MarketingCampaign)
            .where(MarketingCampaign.id == campaign.id)
            .where(MarketingCampaign.organization_id == organization_id)
            .where(MarketingCampaign.status.in_(MarketingCampaignStatus.EDITABLE))
            .values(status=MarketingCampaignStatus.cancelled)
            .returning(MarketingCampaign.id)
        )
    ).all()
    if not claimed:
        raise CampaignConflict("Only a draft or scheduled campaign can be cancelled.")
    campaign.status = MarketingCampaignStatus.cancelled

    queued = (
        await session.scalars(
            select(MarketingRecipient)
            .where(MarketingRecipient.organization_id == organization_id)
            .where(MarketingRecipient.campaign_id == campaign.id)
            .where(MarketingRecipient.status == MarketingRecipientStatus.queued)
        )
    ).all()
    for recipient in queued:
        recipient.status = MarketingRecipientStatus.skipped
        recipient.skip_reason = (
            "The campaign was cancelled before this message was sent."
        )
    campaign.skipped_count += len(queued)
    await session.flush()
    return campaign
