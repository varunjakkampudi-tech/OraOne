"""Platform-level analytics for the admin console (aggregate counts only).

Privacy rules for this module:

* Every value is a COUNT, a GROUP BY count, or a rate built from counts.
* No query selects a text, name, email, phone, or payload column. Results are
  plain integers, percentages, dates, and channel names.
* Per-organisation figures are used only inside the org summary, scoped to one
  organisation and returned only to that organisation's owner.

Helpers ``_count``, ``_grouped`` and ``_fill_series`` are shared with the org
analytics module so the counting rules stay in one place.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.api_log import ApiRequestLog
from app.database.models.call_campaign import AttemptStatus, CallAttempt
from app.database.models.conversation import Conversation
from app.database.models.lead import Lead
from app.database.models.message import Message
from app.database.models.organization import Organization
from app.database.models.organization_member import MemberStatus, OrganizationMember
from app.database.models.user import User
from app.database.models.workflow import WorkflowRun
from app.services.analytics_service import _count, _fill_series, _grouped

WINDOW_DAYS = 30
_PLACED_CALL_STATUSES = AttemptStatus.COUNTED


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _window(now: datetime) -> tuple[datetime, date, date]:
    """Return (since, first_day, last_day) for a 30-calendar-day window ending today."""
    last_day = now.date()
    first_day = last_day - timedelta(days=WINDOW_DAYS - 1)
    since = datetime.combine(first_day, time.min, tzinfo=timezone.utc)
    return since, first_day, last_day


async def _daily(
    session: AsyncSession,
    *,
    date_col,
    since: datetime,
    first_day: date,
    last_day: date,
    select_from,
    conditions: tuple = (),
) -> list[dict]:
    """Zero-filled per-day COUNT series for the window."""
    day = cast(date_col, Date).label("day")
    stmt = select(day, func.count()).select_from(select_from).where(date_col >= since)
    for condition in conditions:
        stmt = stmt.where(condition)
    stmt = stmt.group_by(day).order_by(day)
    rows = [(r[0], int(r[1])) for r in (await session.execute(stmt)).all()]
    return _fill_series(rows, first_day, last_day)


def _rate(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


async def platform_overview(
    session: AsyncSession, *, now: Optional[datetime] = None
) -> dict:
    """Platform counts, channel mix, error rate and 30-day daily series."""
    now = now or _now()
    since, first_day, last_day = _window(now)

    organizations = await _count(session, Organization)
    active_users = await _count(session, User, User.last_login_at >= since)
    conversations = await _count(
        session, Conversation, Conversation.created_at >= since
    )
    messages = await _count(session, Message, Message.created_at >= since)
    leads = await _count(session, Lead, Lead.created_at >= since)
    calls_placed = await _count(
        session,
        CallAttempt,
        CallAttempt.created_at >= since,
        CallAttempt.status.in_(_PLACED_CALL_STATUSES),
    )
    workflows_run = await _count(session, WorkflowRun, WorkflowRun.created_at >= since)

    requests = await _count(session, ApiRequestLog, ApiRequestLog.created_at >= since)
    server_errors = await _count(
        session,
        ApiRequestLog,
        ApiRequestLog.created_at >= since,
        ApiRequestLog.status_code >= 500,
    )

    channel_mix = await _grouped(
        session,
        Conversation.channel,
        Conversation.created_at >= since,
        Conversation.deleted_at.is_(None),
    )

    daily_conversations = await _daily(
        session,
        date_col=Conversation.created_at,
        since=since,
        first_day=first_day,
        last_day=last_day,
        select_from=Conversation,
        conditions=(Conversation.deleted_at.is_(None),),
    )
    daily_messages = await _daily(
        session,
        date_col=Message.created_at,
        since=since,
        first_day=first_day,
        last_day=last_day,
        select_from=Message,
    )
    daily_errors = await _daily(
        session,
        date_col=ApiRequestLog.created_at,
        since=since,
        first_day=first_day,
        last_day=last_day,
        select_from=ApiRequestLog,
        conditions=(ApiRequestLog.status_code >= 500,),
    )

    return {
        "window_days": WINDOW_DAYS,
        "generated_at": now.isoformat(),
        "totals": {
            "organizations": organizations,
            "active_users_30d": active_users,
            "conversations_30d": conversations,
            "messages_30d": messages,
            "leads_30d": leads,
            "calls_placed_30d": calls_placed,
            "workflows_run_30d": workflows_run,
        },
        "channel_mix": channel_mix,
        "errors": {
            "requests_30d": requests,
            "server_errors_30d": server_errors,
            "error_rate_pct": _rate(server_errors, requests),
            "source": "api_request_logs",
        },
        "daily": {
            "conversations": daily_conversations,
            "messages": daily_messages,
            "server_errors": daily_errors,
        },
    }


async def org_summary(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    now: Optional[datetime] = None,
) -> dict:
    """One organisation's 30-day summary. Every query is scoped to ``organization_id``."""
    now = now or _now()
    since, first_day, last_day = _window(now)
    org = organization_id

    conversations = await _count(
        session,
        Conversation,
        Conversation.organization_id == org,
        Conversation.created_at >= since,
    )
    messages_stmt = (
        select(func.count())
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.organization_id == org,
            Message.created_at >= since,
        )
    )
    messages = int(await session.scalar(messages_stmt) or 0)
    leads = await _count(
        session, Lead, Lead.organization_id == org, Lead.created_at >= since
    )
    calls_placed = await _count(
        session,
        CallAttempt,
        CallAttempt.organization_id == org,
        CallAttempt.created_at >= since,
        CallAttempt.status.in_(_PLACED_CALL_STATUSES),
    )
    workflows_run = await _count(
        session,
        WorkflowRun,
        WorkflowRun.organization_id == org,
        WorkflowRun.created_at >= since,
    )
    active_members = int(
        await session.scalar(
            select(func.count(func.distinct(OrganizationMember.user_id)))
            .select_from(OrganizationMember)
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                OrganizationMember.organization_id == org,
                OrganizationMember.status == MemberStatus.active,
                OrganizationMember.deleted_at.is_(None),
                User.last_login_at >= since,
            )
        )
        or 0
    )
    requests = await _count(
        session,
        ApiRequestLog,
        ApiRequestLog.organization_id == org,
        ApiRequestLog.created_at >= since,
    )
    server_errors = await _count(
        session,
        ApiRequestLog,
        ApiRequestLog.organization_id == org,
        ApiRequestLog.created_at >= since,
        ApiRequestLog.status_code >= 500,
    )
    channel_mix = await _grouped(
        session,
        Conversation.channel,
        Conversation.organization_id == org,
        Conversation.created_at >= since,
        Conversation.deleted_at.is_(None),
    )
    daily_conversations = await _daily(
        session,
        date_col=Conversation.created_at,
        since=since,
        first_day=first_day,
        last_day=last_day,
        select_from=Conversation,
        conditions=(
            Conversation.organization_id == org,
            Conversation.deleted_at.is_(None),
        ),
    )

    return {
        "organization_id": str(org),
        "window_days": WINDOW_DAYS,
        "generated_at": now.isoformat(),
        "totals": {
            "conversations_30d": conversations,
            "messages_30d": messages,
            "leads_30d": leads,
            "calls_placed_30d": calls_placed,
            "workflows_run_30d": workflows_run,
            "active_members_30d": active_members,
        },
        "channel_mix": channel_mix,
        "errors": {
            "requests_30d": requests,
            "server_errors_30d": server_errors,
            "error_rate_pct": _rate(server_errors, requests),
            "source": "api_request_logs",
        },
        "daily": {"conversations": daily_conversations},
    }
