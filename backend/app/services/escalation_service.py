"""Human handoff: persistent escalations for questions the assistant cannot answer.

Flow:
1. A chat or channel reply is a handoff (no supporting passage). The channel
   handler calls :func:`create_escalation`, which stores one row.
2. The reply the visitor sees depends on contact details. With a name, email
   or phone the team may follow up. Without any, the reply asks for a contact
   and never promises follow-up (:func:`handoff_reply`).
3. The worker calls :func:`deliver_due` on a fixed interval. It emails the
   organization's owners and admins. A failed send is retried with exponential
   backoff. After ``MAX_NOTIFY_ATTEMPTS`` the row moves to ``dead_letter``, and
   it stays visible in the dashboard.
4. When SMTP is not configured, rows stay ``pending`` without consuming an
   attempt, so nothing is lost and nothing is marked as sent.

Only scrubbed text is stored or sent. Addresses and tokens are removed from the
question before it is saved.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_redaction import redact_email, scrub_text
from app.database.models.escalation import Escalation, EscalationStatus, NotifyStatus
from app.database.models.organization_member import (
    MemberRole,
    MemberStatus,
    OrganizationMember,
)
from app.database.models.user import User
from app.services import email_service
from app.services.visitor_service import normalize_email, normalize_phone

log = logging.getLogger("app.escalations")

MAX_NOTIFY_ATTEMPTS = 5
NOTIFY_BACKOFF_SECONDS = 60
QUESTION_CHARS = 1000

HANDOFF_NO_CONTACT_TEXT = (
    "I don't have that information yet, so I won't guess. I've noted your question "
    "for the business team, but I don't have a way to reach you. If you share an "
    "email address or phone number, they can follow up."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def has_contact(email: Optional[str], phone: Optional[str]) -> bool:
    """True when the visitor gave a usable way to be reached."""
    return bool(normalize_email(email) or normalize_phone(phone))


def handoff_reply(answer: str, *, contact_known: bool) -> str:
    """The reply shown for a handoff. Promises follow-up only with a contact."""
    return answer if contact_known else HANDOFF_NO_CONTACT_TEXT


async def create_escalation(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: uuid.UUID,
    channel: str,
    question: str,
    conversation_id: Optional[uuid.UUID] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> Escalation:
    """Store one open handoff. The team is notified by the worker, not here.

    One conversation has at most one unresolved escalation. A repeat handoff, or
    a manual request from the same chat, refreshes that item instead of adding a
    second one, so the team sees one queue entry per conversation.
    """
    if conversation_id is not None:
        existing = await session.scalar(
            select(Escalation)
            .where(Escalation.conversation_id == conversation_id)
            .where(Escalation.status != EscalationStatus.resolved)
            .order_by(Escalation.created_at.desc())
            .limit(1)
        )
        if existing is not None:
            existing.question = scrub_text(question or "", limit=QUESTION_CHARS)
            existing.contact_name = (name or "").strip()[:160] or existing.contact_name
            existing.contact_email = normalize_email(email) or existing.contact_email
            existing.contact_phone = normalize_phone(phone) or existing.contact_phone
            existing.has_contact = existing.has_contact or has_contact(email, phone)
            await session.flush()
            return existing
    row = Escalation(
        organization_id=organization_id,
        project_id=project_id,
        conversation_id=conversation_id,
        channel=(channel or "chat")[:40],
        question=scrub_text(question or "", limit=QUESTION_CHARS),
        contact_name=(name or "").strip()[:160] or None,
        contact_email=normalize_email(email),
        contact_phone=normalize_phone(phone),
        has_contact=has_contact(email, phone),
        status=EscalationStatus.open,
        notify_status=NotifyStatus.pending,
        notify_attempts=0,
        next_attempt_at=_now(),
    )
    session.add(row)
    await session.flush()
    log.info("escalation_created id=%s channel=%s", row.id, row.channel)
    return row


async def _recipients(session: AsyncSession, organization_id: uuid.UUID) -> list[str]:
    rows = await session.execute(
        select(User.email)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == organization_id)
        .where(OrganizationMember.status == MemberStatus.active)
        .where(
            or_(
                OrganizationMember.role == MemberRole.owner,
                OrganizationMember.role == MemberRole.admin,
            )
        )
        .where(OrganizationMember.deleted_at.is_(None))
    )
    return sorted({email for (email,) in rows.all() if email})


def _alert_body(row: Escalation) -> dict:
    if row.has_contact:
        contact = " / ".join(
            part
            for part in (row.contact_name, row.contact_email, row.contact_phone)
            if part
        )
    else:
        contact = "No contact details given. The visitor was asked for one."
    return {
        "channel": row.channel,
        "question": row.question,
        "contact": contact,
    }


LEASE = timedelta(minutes=5)


def due_query(now: datetime, limit: int):
    """Escalations ready for a send attempt. Rows are locked so that concurrent
    workers each take a disjoint batch (SKIP LOCKED)."""
    return (
        select(Escalation)
        .where(
            Escalation.notify_status.in_([NotifyStatus.pending, NotifyStatus.failed])
        )
        .where(Escalation.next_attempt_at <= now)
        .where(Escalation.notify_attempts < MAX_NOTIFY_ATTEMPTS)
        .order_by(Escalation.next_attempt_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True, of=Escalation)
    )


async def deliver_due(
    session: AsyncSession, *, now: Optional[datetime] = None, limit: int = 50
) -> dict:
    """Send alerts for escalations that are due. Returns counts for logging."""
    counts = {
        "sent": 0,
        "failed": 0,
        "dead_letter": 0,
        "no_recipients": 0,
        "skipped": 0,
    }
    if not email_service.delivery_configured():
        # Leave rows pending and do not spend attempts while mail is unconfigured.
        counts["skipped"] = (
            await session.scalar(
                select(func.count(Escalation.id)).where(
                    Escalation.notify_status == NotifyStatus.pending
                )
            )
        ) or 0
        return counts

    now = now or _now()
    due = (await session.execute(due_query(now, limit))).scalars().all()

    for row in due:
        # Lease the row before any external call. The row lock held by this
        # transaction stops other workers claiming it, and the lease keeps it out
        # of the due set if this worker commits late.
        row.next_attempt_at = now + LEASE
        recipients = await _recipients(session, row.organization_id)
        if not recipients:
            row.notify_status = NotifyStatus.no_recipients
            row.last_error = "no_recipients"
            counts["no_recipients"] += 1
            continue

        # Send only to team members who have not received this alert yet, so a
        # retry never duplicates an earlier successful send.
        already = set(row.notified_addresses or [])
        remaining = [address for address in recipients if address not in already]
        body = _alert_body(row)
        for address in remaining:
            ok = email_service.send_email(
                to=address,
                subject="A visitor question needs your team",
                template="escalation_alert.html",
                preheader="The assistant could not answer a visitor question.",
                context=body,
            )
            if ok:
                already.add(address)
        row.notified_addresses = sorted(already)
        if set(recipients) <= already:
            row.notify_status = NotifyStatus.sent
            row.last_error = None
            counts["sent"] += 1
            continue

        row.notify_attempts += 1
        row.last_error = "delivery_failed"
        if row.notify_attempts >= MAX_NOTIFY_ATTEMPTS:
            row.notify_status = NotifyStatus.dead_letter
            counts["dead_letter"] += 1
            log.error("escalation_dead_letter id=%s", row.id)
        else:
            row.notify_status = NotifyStatus.failed
            delay = NOTIFY_BACKOFF_SECONDS * (2 ** (row.notify_attempts - 1))
            row.next_attempt_at = now + timedelta(seconds=delay)
            counts["failed"] += 1
            log.warning(
                "escalation_notify_failed id=%s attempts=%s recipients=%s",
                row.id,
                row.notify_attempts,
                ",".join(redact_email(a) for a in recipients),
            )
    await session.flush()
    return counts


async def assign(
    session: AsyncSession,
    row: Escalation,
    *,
    user_id: Optional[uuid.UUID],
) -> Escalation:
    """Give the item to a team member, or clear the owner with ``None``."""
    row.assigned_user_id = user_id
    row.status = EscalationStatus.assigned if user_id else EscalationStatus.open
    await session.flush()
    return row


async def resolve(session: AsyncSession, row: Escalation) -> Escalation:
    row.status = EscalationStatus.resolved
    row.resolved_at = _now()
    await session.flush()
    return row
