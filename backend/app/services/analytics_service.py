"""Organization analytics aggregation (Phase 12, Module 6).

Read-only, org-scoped roll-ups across the Postgres system-of-record:
totals, daily time-series and categorical breakdowns. Everything is
computed live (no materialised table) and scoped strictly by
``organization_id``.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Date, Float, case, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.analytics import AnswerFeedback
from app.database.models.conversation import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
)
from app.database.models.document import Document, DocumentStatus
from app.database.models.document_chunk import DocumentChunk
from app.database.models.integration import Integration, IntegrationStatus
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.message import Message, MessageSender
from app.database.models.organization_member import MemberStatus, OrganizationMember
from app.database.models.project import Project
from app.database.models.sync_job import SyncJob, SyncJobStatus
from app.database.models.website import Website
from app.database.models.widget import Widget
from app.database.models.widget_event import WidgetEvent
from app.database.models.widget_session import WidgetSession
from app.database.models.workflow import RunStatus, Workflow, WorkflowRun

MAX_DAYS = 90
DEFAULT_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp_days(days: int) -> int:
    if days < 1:
        return 1
    return min(days, MAX_DAYS)


async def _count(session: AsyncSession, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    for c in conditions:
        stmt = stmt.where(c)
    if hasattr(model, "deleted_at"):
        stmt = stmt.where(model.deleted_at.is_(None))
    return int(await session.scalar(stmt) or 0)


def _fill_series(rows: list[tuple[date, int]], start: date, end: date) -> list[dict]:
    """Turn sparse (day, count) rows into a dense, zero-filled series."""
    have = {r[0]: int(r[1]) for r in rows}
    out: list[dict] = []
    cursor = start
    while cursor <= end:
        out.append({"date": cursor.isoformat(), "count": have.get(cursor, 0)})
        cursor += timedelta(days=1)
    return out


async def _daily_counts(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    table,
    date_col,
    since: datetime,
    extra_join=None,
    org_col=None,
    extra_condition=None,
) -> list[tuple[date, int]]:
    day = cast(date_col, Date).label("day")
    stmt = select(day, func.count()).where(date_col >= since)
    if extra_join is not None:
        stmt = stmt.select_from(table).join(*extra_join)
    if org_col is not None:
        stmt = stmt.where(org_col == org_id)
    if extra_condition is not None:
        stmt = stmt.where(extra_condition)
    stmt = stmt.group_by(day).order_by(day)
    result = await session.execute(stmt)
    return [(r[0], r[1]) for r in result.all()]


async def _grouped(session: AsyncSession, col, *conditions) -> dict[str, int]:
    stmt = select(col, func.count()).group_by(col)
    for c in conditions:
        stmt = stmt.where(c)
    result = await session.execute(stmt)
    out: dict[str, int] = {}
    for value, count in result.all():
        key = value.value if hasattr(value, "value") else str(value)
        out[key] = int(count)
    return out


async def org_overview(
    session: AsyncSession,
    org_id: uuid.UUID,
    days: int = DEFAULT_DAYS,
    *,
    project_id: Optional[uuid.UUID] = None,
) -> dict:
    days = _clamp_days(days)
    now = _now()
    since = now - timedelta(days=days - 1)
    start_day = since.date()
    end_day = now.date()

    # ── project scoping (optional) ──
    # When ``project_id`` is given, restrict every project-scoped entity to
    # that project's namespace. WorkflowRun / Message have no project_id
    # column, so they're scoped via their parent (Workflow / Conversation).
    proj = project_id is not None
    agent_proj = [Agent.project_id == project_id] if proj else []
    conv_proj = [Conversation.project_id == project_id] if proj else []
    wf_proj = [Workflow.project_id == project_id] if proj else []
    kb_proj = [KnowledgeBase.project_id == project_id] if proj else []
    doc_proj = [Document.project_id == project_id] if proj else []
    wfrun_proj = (
        [
            WorkflowRun.workflow_id.in_(
                select(Workflow.id).where(Workflow.project_id == project_id)
            )
        ]
        if proj
        else []
    )
    conv_proj_cond = Conversation.project_id == project_id if proj else None
    wfrun_proj_cond = (
        WorkflowRun.workflow_id.in_(
            select(Workflow.id).where(Workflow.project_id == project_id)
        )
        if proj
        else None
    )

    # ── totals ──
    agents = await _count(session, Agent, Agent.organization_id == org_id, *agent_proj)
    conversations = await _count(
        session, Conversation, Conversation.organization_id == org_id, *conv_proj
    )
    workflows = await _count(
        session, Workflow, Workflow.organization_id == org_id, *wf_proj
    )
    workflow_runs = await _count(
        session, WorkflowRun, WorkflowRun.organization_id == org_id, *wfrun_proj
    )
    knowledge_bases = await _count(
        session, KnowledgeBase, KnowledgeBase.organization_id == org_id, *kb_proj
    )
    documents = await _count(
        session, Document, Document.organization_id == org_id, *doc_proj
    )
    members = await _count(
        session,
        OrganizationMember,
        OrganizationMember.organization_id == org_id,
        OrganizationMember.status == MemberStatus.active,
    )
    # messages are scoped via their conversation
    msg_stmt = (
        select(func.count())
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.organization_id == org_id)
    )
    if proj:
        msg_stmt = msg_stmt.where(Conversation.project_id == project_id)
    messages = int(await session.scalar(msg_stmt) or 0)

    qualified = await _count(
        session,
        Conversation,
        Conversation.organization_id == org_id,
        Conversation.status == ConversationStatus.qualified,
        *conv_proj,
    )
    conversion_rate = round((qualified / conversations) * 100, 1) if conversations else 0.0

    # ── time series (zero-filled) ──
    conv_rows = await _daily_counts(
        session, org_id, table=Conversation, date_col=Conversation.created_at,
        since=since, org_col=Conversation.organization_id,
        extra_condition=conv_proj_cond,
    )
    run_rows = await _daily_counts(
        session, org_id, table=WorkflowRun, date_col=WorkflowRun.created_at,
        since=since, org_col=WorkflowRun.organization_id,
        extra_condition=wfrun_proj_cond,
    )
    msg_rows = await _daily_counts(
        session, org_id, table=Message, date_col=Message.created_at, since=since,
        extra_join=(Conversation, Message.conversation_id == Conversation.id),
        org_col=Conversation.organization_id,
        extra_condition=conv_proj_cond,
    )

    # ── daily qualified conversations (drives the Resolution Rate trend) ──
    qual_day = cast(Conversation.created_at, Date).label("day")
    qual_stmt = (
        select(qual_day, func.count())
        .where(Conversation.organization_id == org_id)
        .where(Conversation.created_at >= since)
        .where(Conversation.status == ConversationStatus.qualified)
        .group_by(qual_day)
        .order_by(qual_day)
    )
    if proj:
        qual_stmt = qual_stmt.where(Conversation.project_id == project_id)
    qual_rows = [(r[0], int(r[1])) for r in (await session.execute(qual_stmt)).all()]

    # ── daily distinct agents with activity (Active Agents trend) ──
    aa_day = cast(Conversation.created_at, Date).label("day")
    aa_stmt = (
        select(aa_day, func.count(func.distinct(Conversation.agent_id)))
        .where(Conversation.organization_id == org_id)
        .where(Conversation.created_at >= since)
        .where(Conversation.agent_id.is_not(None))
        .group_by(aa_day)
        .order_by(aa_day)
    )
    if proj:
        aa_stmt = aa_stmt.where(Conversation.project_id == project_id)
    active_agent_rows = [(r[0], int(r[1])) for r in (await session.execute(aa_stmt)).all()]

    # dense daily resolution-rate series (qualified / total, per day)
    conv_have = {r[0]: int(r[1]) for r in conv_rows}
    qual_have = {r[0]: int(r[1]) for r in qual_rows}
    resolution_series: list[dict] = []
    _cursor = start_day
    while _cursor <= end_day:
        _tot = conv_have.get(_cursor, 0)
        _q = qual_have.get(_cursor, 0)
        resolution_series.append(
            {"date": _cursor.isoformat(), "count": round((_q / _tot) * 100, 1) if _tot else 0.0}
        )
        _cursor += timedelta(days=1)

    # ── breakdowns ──
    by_channel = await _grouped(
        session, Conversation.channel,
        Conversation.organization_id == org_id,
        Conversation.deleted_at.is_(None),
        *conv_proj,
    )
    by_status = await _grouped(
        session, Conversation.status,
        Conversation.organization_id == org_id,
        Conversation.deleted_at.is_(None),
        *conv_proj,
    )
    runs_by_status = await _grouped(
        session, WorkflowRun.status,
        WorkflowRun.organization_id == org_id,
        *wfrun_proj,
    )

    # ensure every channel/run-status key is present (zero default)
    channels = {c.value: by_channel.get(c.value, 0) for c in ConversationChannel}
    run_statuses = {s.value: runs_by_status.get(s.value, 0) for s in RunStatus}

    # ── top agents by conversation volume ──
    top_stmt = (
        select(Agent.id, Agent.name, func.count(Conversation.id).label("convos"))
        .join(Conversation, Conversation.agent_id == Agent.id)
        .where(Agent.organization_id == org_id)
        .where(Conversation.deleted_at.is_(None))
        .group_by(Agent.id, Agent.name)
        .order_by(func.count(Conversation.id).desc())
        .limit(5)
    )
    if proj:
        top_stmt = top_stmt.where(Agent.project_id == project_id)
    top_rows = (await session.execute(top_stmt)).all()
    top_agents = [
        {"agent_id": str(r[0]), "name": r[1], "conversations": int(r[2])}
        for r in top_rows
    ]

    return {
        "range_days": days,
        "generated_at": now,
        "totals": {
            "agents": agents,
            "conversations": conversations,
            "messages": messages,
            "workflows": workflows,
            "workflow_runs": workflow_runs,
            "knowledge_bases": knowledge_bases,
            "documents": documents,
            "members": members,
            "qualified_conversations": qualified,
            "conversion_rate": conversion_rate,
        },
        "series": {
            "conversations": _fill_series(conv_rows, start_day, end_day),
            "messages": _fill_series(msg_rows, start_day, end_day),
            "workflow_runs": _fill_series(run_rows, start_day, end_day),
            "resolution_rate": resolution_series,
            "active_agents": _fill_series(active_agent_rows, start_day, end_day),
        },
        "breakdowns": {
            "conversations_by_channel": channels,
            "conversations_by_status": by_status,
            "workflow_runs_by_status": run_statuses,
        },
        "top_agents": top_agents,
    }


# ─────────────────────────────────────────────────────────────────────────────
# R8 — Analytics & Observability modules
# ─────────────────────────────────────────────────────────────────────────────

# Blended price per 1K tokens (USD). Tunable; used for cost estimation only.
MODEL_PRICING: dict[str, float] = {
    "openai.gpt-oss-120b-1:0": 0.0009,
    "anthropic.claude-3-5-sonnet": 0.006,
    "anthropic.claude-3-5-sonnet-20240620-v1:0": 0.006,
    "anthropic.claude-3-haiku": 0.0008,
    "anthropic.claude-3-haiku-20240307-v1:0": 0.0008,
    "amazon.titan-embed-text-v2:0": 0.00002,
    "default": 0.0015,
}
# Estimated fully-loaded cost of a human-handled conversation (for ROI/savings).
HUMAN_COST_PER_CONVERSATION = 4.0


def _price_for(model: str | None) -> float:
    if not model:
        return MODEL_PRICING["default"]
    return MODEL_PRICING.get(model, MODEL_PRICING["default"])


def _window(days: int) -> tuple[datetime, date, date]:
    now = _now()
    since = now - timedelta(days=days - 1)
    return since, since.date(), now.date()


async def _token_sum(session: AsyncSession, org_id: uuid.UUID, *, since: datetime | None = None) -> int:
    stmt = (
        select(func.coalesce(func.sum(Message.token_count), 0))
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.organization_id == org_id)
    )
    if since is not None:
        stmt = stmt.where(Message.created_at >= since)
    return int(await session.scalar(stmt) or 0)


async def _daily_token_sum(session: AsyncSession, org_id: uuid.UUID, since: datetime) -> list[tuple[date, int]]:
    day = cast(Message.created_at, Date).label("day")
    stmt = (
        select(day, func.coalesce(func.sum(Message.token_count), 0))
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.organization_id == org_id, Message.created_at >= since)
        .group_by(day)
        .order_by(day)
    )
    return [(r[0], int(r[1])) for r in (await session.execute(stmt)).all()]


async def _feedback_counts(session: AsyncSession, org_id: uuid.UUID) -> dict[str, int]:
    up = await _count(session, AnswerFeedback, AnswerFeedback.organization_id == org_id, AnswerFeedback.rating > 0)
    down = await _count(session, AnswerFeedback, AnswerFeedback.organization_id == org_id, AnswerFeedback.rating < 0)
    total = up + down
    return {
        "positive": up,
        "negative": down,
        "total": total,
        "satisfaction_rate": round((up / total) * 100, 1) if total else 0.0,
    }


async def chat_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    since, start_day, end_day = _window(days)

    conversations = await _count(session, Conversation, Conversation.organization_id == org_id)
    messages = int(
        await session.scalar(
            select(func.count())
            .select_from(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.organization_id == org_id)
        )
        or 0
    )
    by_channel = await _grouped(
        session, Conversation.channel,
        Conversation.organization_id == org_id, Conversation.deleted_at.is_(None),
    )
    by_status = await _grouped(
        session, Conversation.status,
        Conversation.organization_id == org_id, Conversation.deleted_at.is_(None),
    )
    conv_rows = await _daily_counts(
        session, org_id, table=Conversation, date_col=Conversation.created_at,
        since=since, org_col=Conversation.organization_id,
    )
    msg_rows = await _daily_counts(
        session, org_id, table=Message, date_col=Message.created_at, since=since,
        extra_join=(Conversation, Message.conversation_id == Conversation.id),
        org_col=Conversation.organization_id,
    )
    feedback = await _feedback_counts(session, org_id)
    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {
            "conversations": conversations,
            "messages": messages,
            "avg_messages_per_conversation": round(messages / conversations, 1) if conversations else 0.0,
        },
        "series": {
            "conversations": _fill_series(conv_rows, start_day, end_day),
            "messages": _fill_series(msg_rows, start_day, end_day),
        },
        "breakdowns": {
            "by_channel": {c.value: by_channel.get(c.value, 0) for c in ConversationChannel},
            "by_status": by_status,
        },
        "feedback": feedback,
    }


async def agent_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    total_agents = await _count(session, Agent, Agent.organization_id == org_id)
    by_status = await _grouped(
        session, Agent.status, Agent.organization_id == org_id, Agent.deleted_at.is_(None)
    )
    stmt = (
        select(
            Agent.id,
            Agent.name,
            Agent.status,
            func.count(Conversation.id).label("convos"),
            func.coalesce(
                func.sum(case((Conversation.status == ConversationStatus.qualified, 1), else_=0)), 0
            ).label("qualified"),
        )
        .outerjoin(Conversation, (Conversation.agent_id == Agent.id) & (Conversation.deleted_at.is_(None)))
        .where(Agent.organization_id == org_id, Agent.deleted_at.is_(None))
        .group_by(Agent.id, Agent.name, Agent.status)
        .order_by(func.count(Conversation.id).desc())
        .limit(25)
    )
    rows = (await session.execute(stmt)).all()
    agents = [
        {
            "agent_id": str(r[0]),
            "name": r[1],
            "status": r[2].value if hasattr(r[2], "value") else str(r[2]),
            "conversations": int(r[3]),
            "qualified": int(r[4]),
            "conversion_rate": round((int(r[4]) / int(r[3])) * 100, 1) if int(r[3]) else 0.0,
        }
        for r in rows
    ]
    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {"agents": total_agents},
        "breakdowns": {"by_status": by_status},
        "agents": agents,
    }


async def knowledge_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    knowledge_bases = await _count(session, KnowledgeBase, KnowledgeBase.organization_id == org_id)
    documents = await _count(session, Document, Document.organization_id == org_id)
    docs_by_status = await _grouped(
        session, Document.status, Document.organization_id == org_id, Document.deleted_at.is_(None)
    )
    chunks = await _count(session, DocumentChunk, DocumentChunk.organization_id == org_id)
    websites = await _count(session, Website, Website.organization_id == org_id)
    pages = int(
        await session.scalar(
            select(func.coalesce(func.sum(Website.pages_count), 0)).where(
                Website.organization_id == org_id, Website.deleted_at.is_(None)
            )
        )
        or 0
    )
    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {
            "knowledge_bases": knowledge_bases,
            "documents": documents,
            "chunks": chunks,
            "websites": websites,
            "crawled_pages": pages,
        },
        "breakdowns": {"documents_by_status": docs_by_status},
    }


async def rag_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    base = (
        select(func.count())
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.organization_id == org_id, Message.sender == MessageSender.agent)
    )
    answers = int(await session.scalar(base) or 0)
    grounded = int(
        await session.scalar(base.where(Message.metadata_["grounded"].astext == "true")) or 0
    )
    feedback = await _feedback_counts(session, org_id)
    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {
            "answers": answers,
            "grounded_answers": grounded,
            "ungrounded_answers": max(answers - grounded, 0),
            "grounded_rate": round((grounded / answers) * 100, 1) if answers else 0.0,
        },
        "feedback": feedback,
    }


async def widget_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    since, start_day, end_day = _window(days)
    widgets = await _count(session, Widget, Widget.organization_id == org_id)
    sessions = await _count(session, WidgetSession, WidgetSession.organization_id == org_id)
    escalations = await _count(
        session, WidgetSession, WidgetSession.organization_id == org_id, WidgetSession.escalated.is_(True)
    )
    messages = int(
        await session.scalar(
            select(func.coalesce(func.sum(WidgetSession.message_count), 0)).where(
                WidgetSession.organization_id == org_id
            )
        )
        or 0
    )
    by_event = await _grouped(session, WidgetEvent.event, WidgetEvent.organization_id == org_id)
    sess_rows = await _daily_counts(
        session, org_id, table=WidgetSession, date_col=WidgetSession.created_at,
        since=since, org_col=WidgetSession.organization_id,
    )
    leads = int(by_event.get("lead", 0))
    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {
            "widgets": widgets,
            "sessions": sessions,
            "messages": messages,
            "escalations": escalations,
            "leads": leads,
            "escalation_rate": round((escalations / sessions) * 100, 1) if sessions else 0.0,
        },
        "series": {"sessions": _fill_series(sess_rows, start_day, end_day)},
        "breakdowns": {"by_event": by_event},
    }


async def workflow_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    since, start_day, end_day = _window(days)
    workflows = await _count(session, Workflow, Workflow.organization_id == org_id)
    runs = await _count(session, WorkflowRun, WorkflowRun.organization_id == org_id)
    succeeded = await _count(
        session, WorkflowRun, WorkflowRun.organization_id == org_id, WorkflowRun.status == RunStatus.completed
    )
    by_status = await _grouped(session, WorkflowRun.status, WorkflowRun.organization_id == org_id)
    run_rows = await _daily_counts(
        session, org_id, table=WorkflowRun, date_col=WorkflowRun.created_at,
        since=since, org_col=WorkflowRun.organization_id,
    )
    top_stmt = (
        select(Workflow.id, Workflow.name, Workflow.run_count, Workflow.success_count)
        .where(Workflow.organization_id == org_id, Workflow.deleted_at.is_(None))
        .order_by(Workflow.run_count.desc())
        .limit(10)
    )
    top = [
        {
            "workflow_id": str(r[0]),
            "name": r[1],
            "runs": int(r[2] or 0),
            "successes": int(r[3] or 0),
        }
        for r in (await session.execute(top_stmt)).all()
    ]
    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {
            "workflows": workflows,
            "runs": runs,
            "succeeded": succeeded,
            "success_rate": round((succeeded / runs) * 100, 1) if runs else 0.0,
        },
        "series": {"runs": _fill_series(run_rows, start_day, end_day)},
        "breakdowns": {"runs_by_status": {s.value: by_status.get(s.value, 0) for s in RunStatus}},
        "top_workflows": top,
    }


async def integration_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    integrations = await _count(session, Integration, Integration.organization_id == org_id)
    by_status = await _grouped(
        session, Integration.status, Integration.organization_id == org_id, Integration.deleted_at.is_(None)
    )
    sync_jobs = await _count(session, SyncJob, SyncJob.organization_id == org_id)
    jobs_by_status = await _grouped(session, SyncJob.status, SyncJob.organization_id == org_id)
    docs_synced = int(
        await session.scalar(
            select(func.coalesce(func.sum(SyncJob.documents_synced), 0)).where(
                SyncJob.organization_id == org_id
            )
        )
        or 0
    )
    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {
            "integrations": integrations,
            "sync_jobs": sync_jobs,
            "documents_synced": docs_synced,
        },
        "breakdowns": {
            "integrations_by_status": by_status,
            "sync_jobs_by_status": jobs_by_status,
        },
    }


async def cost_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    since, start_day, end_day = _window(days)

    total_tokens = await _token_sum(session, org_id)
    window_tokens = await _token_sum(session, org_id, since=since)

    # Stored per-message cost (USD) lives in agent message metadata as
    # ``cost_usd``; we sum it when present and fall back to a token-based
    # estimate for legacy rows that predate cost accounting.
    cost_stored = cast(Message.metadata_["cost_usd"].astext, Float)

    # ── Tokens & cost grouped by model ───────────────────────────────
    model_stmt = (
        select(
            Message.metadata_["model"].astext.label("model"),
            func.coalesce(func.sum(Message.token_count), 0),
            func.coalesce(func.sum(cost_stored), 0.0),
        )
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.organization_id == org_id, Message.sender == MessageSender.agent)
        .group_by(text("1"))
    )
    by_model: list[dict] = []
    total_cost = 0.0
    for model, tokens, stored in (await session.execute(model_stmt)).all():
        tokens = int(tokens or 0)
        stored = float(stored or 0.0)
        cost = round(stored if stored > 0 else (tokens / 1000.0) * _price_for(model), 4)
        total_cost += cost
        by_model.append({"model": model or "unknown", "tokens": tokens, "cost": cost})
    by_model.sort(key=lambda r: r["cost"], reverse=True)

    # ── Cost grouped by agent ────────────────────────────────────────
    agent_stmt = (
        select(
            Agent.name,
            func.coalesce(func.sum(Message.token_count), 0),
            func.coalesce(func.sum(cost_stored), 0.0),
            func.count(func.distinct(Conversation.id)),
        )
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Agent, Conversation.agent_id == Agent.id)
        .where(Conversation.organization_id == org_id, Message.sender == MessageSender.agent)
        .group_by(Agent.id, Agent.name)
    )
    by_agent: list[dict] = []
    for name, tokens, stored, convos in (await session.execute(agent_stmt)).all():
        tokens = int(tokens or 0)
        stored = float(stored or 0.0)
        cost = round(stored if stored > 0 else (tokens / 1000.0) * MODEL_PRICING["default"], 4)
        by_agent.append(
            {"agent": name or "Unnamed agent", "tokens": tokens, "cost": cost, "conversations": int(convos or 0)}
        )
    by_agent.sort(key=lambda r: r["cost"], reverse=True)

    # ── Cost grouped by project ──────────────────────────────────────
    project_stmt = (
        select(
            func.coalesce(Project.name, "Unassigned"),
            func.coalesce(func.sum(Message.token_count), 0),
            func.coalesce(func.sum(cost_stored), 0.0),
            func.count(func.distinct(Conversation.id)),
        )
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .outerjoin(Project, Conversation.project_id == Project.id)
        .where(Conversation.organization_id == org_id, Message.sender == MessageSender.agent)
        .group_by(text("1"))
    )
    by_project: list[dict] = []
    for name, tokens, stored, convos in (await session.execute(project_stmt)).all():
        tokens = int(tokens or 0)
        stored = float(stored or 0.0)
        cost = round(stored if stored > 0 else (tokens / 1000.0) * MODEL_PRICING["default"], 4)
        by_project.append(
            {"project": name, "tokens": tokens, "cost": cost, "conversations": int(convos or 0)}
        )
    by_project.sort(key=lambda r: r["cost"], reverse=True)

    # Daily cost series — prefer stored daily cost, else estimate from tokens.
    day = cast(Message.created_at, Date).label("day")
    daily_stmt = (
        select(
            day,
            func.coalesce(func.sum(Message.token_count), 0),
            func.coalesce(func.sum(cost_stored), 0.0),
        )
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.organization_id == org_id, Message.created_at >= since)
        .group_by(day)
    )
    blended = MODEL_PRICING["default"]
    daily = {
        d: (int(t or 0), float(c or 0.0)) for d, t, c in (await session.execute(daily_stmt)).all()
    }
    cost_series: list[dict] = []
    cursor = start_day
    while cursor <= end_day:
        toks, stored = daily.get(cursor, (0, 0.0))
        cost = round(stored if stored > 0 else (toks / 1000.0) * blended, 4)
        cost_series.append({"date": cursor.isoformat(), "tokens": toks, "cost": cost})
        cursor += timedelta(days=1)

    conversations = await _count(session, Conversation, Conversation.organization_id == org_id)
    cost_per_conversation = round(total_cost / conversations, 4) if conversations else 0.0
    window_cost = round(sum(p["cost"] for p in cost_series), 4)
    projected_monthly = round(window_cost / max(days, 1) * 30, 2)

    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {
            "total_tokens": total_tokens,
            "window_tokens": window_tokens,
            "total_cost": round(total_cost, 2),
            "cost_per_conversation": cost_per_conversation,
            "projected_monthly_cost": projected_monthly,
        },
        "series": {"cost": cost_series},
        "breakdowns": {
            "by_model": by_model,
            "by_agent": by_agent,
            "by_project": by_project,
        },
    }


async def insights_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    """Question-level insights: top questions, unanswered rate and the
    knowledge gaps (questions asked in conversations the AI could not
    confidently ground in the knowledge base)."""
    days = _clamp_days(days)
    since, _start, _end = _window(days)

    norm = func.nullif(func.trim(Message.message), "")
    grounded_txt = Message.metadata_["grounded"].astext
    confidence = cast(Message.metadata_["confidence"].astext, Float)

    # ── Top customer questions in the window ─────────────────────────
    q_stmt = (
        select(norm.label("q"), func.count().label("n"))
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.organization_id == org_id,
            Message.sender == MessageSender.customer,
            Message.created_at >= since,
            norm.isnot(None),
        )
        .group_by(norm)
        .order_by(func.count().desc(), norm)
        .limit(15)
    )
    top_questions = [
        {"question": q, "count": int(n)} for q, n in (await session.execute(q_stmt)).all()
    ]

    # ── Answer health (agent messages in the window) ─────────────────
    base = (
        select(func.count())
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.organization_id == org_id,
            Message.sender == MessageSender.agent,
            Message.created_at >= since,
        )
    )
    answers = int(await session.scalar(base) or 0)
    grounded = int(await session.scalar(base.where(grounded_txt == "true")) or 0)
    low_conf = int(await session.scalar(base.where(confidence < 0.4)) or 0)
    ungrounded = max(answers - grounded, 0)

    # ── Knowledge gaps: questions asked in conversations that produced
    # at least one ungrounded answer ─────────────────────────────────
    gap_convs = (
        select(Message.conversation_id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.organization_id == org_id,
            Message.sender == MessageSender.agent,
            Message.created_at >= since,
            grounded_txt != "true",
        )
        .group_by(Message.conversation_id)
        .subquery()
    )
    gaps_stmt = (
        select(norm.label("q"), func.count().label("n"))
        .select_from(Message)
        .where(
            Message.sender == MessageSender.customer,
            Message.conversation_id.in_(select(gap_convs.c.conversation_id)),
            norm.isnot(None),
        )
        .group_by(norm)
        .order_by(func.count().desc(), norm)
        .limit(10)
    )
    knowledge_gaps = [
        {"question": q, "count": int(n)} for q, n in (await session.execute(gaps_stmt)).all()
    ]

    feedback = await _feedback_counts(session, org_id)
    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {
            "answers": answers,
            "grounded_answers": grounded,
            "unanswered": ungrounded,
            "low_confidence": low_conf,
            "grounded_rate": round((grounded / answers) * 100, 1) if answers else 0.0,
            "unanswered_rate": round((ungrounded / answers) * 100, 1) if answers else 0.0,
        },
        "top_questions": top_questions,
        "knowledge_gaps": knowledge_gaps,
        "feedback": feedback,
    }


async def user_team_analytics(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    members = await _count(
        session, OrganizationMember,
        OrganizationMember.organization_id == org_id,
        OrganizationMember.status == MemberStatus.active,
    )
    by_role = await _grouped(
        session, OrganizationMember.role,
        OrganizationMember.organization_id == org_id,
        OrganizationMember.status == MemberStatus.active,
    )
    active_users = int(
        await session.scalar(
            select(func.count(func.distinct(Conversation.user_id))).where(
                Conversation.organization_id == org_id, Conversation.user_id.isnot(None)
            )
        )
        or 0
    )
    return {
        "range_days": days,
        "generated_at": _now(),
        "totals": {"members": members, "active_users": active_users},
        "breakdowns": {"by_role": by_role},
    }


async def executive_summary(session: AsyncSession, org_id: uuid.UUID, days: int = DEFAULT_DAYS) -> dict:
    days = _clamp_days(days)
    overview = await org_overview(session, org_id, days)
    cost = await cost_analytics(session, org_id, days)
    feedback = await _feedback_counts(session, org_id)

    conversations = overview["totals"]["conversations"]
    workflow_runs = overview["totals"]["workflow_runs"]
    automated_interactions = conversations + workflow_runs
    ai_cost = cost["totals"]["total_cost"]
    human_equiv_cost = round(conversations * HUMAN_COST_PER_CONVERSATION, 2)
    estimated_savings = round(max(human_equiv_cost - ai_cost, 0.0), 2)
    roi = round((estimated_savings / ai_cost), 1) if ai_cost else None

    return {
        "range_days": days,
        "generated_at": _now(),
        "kpis": {
            "conversations": conversations,
            "messages": overview["totals"]["messages"],
            "members": overview["totals"]["members"],
            "automated_interactions": automated_interactions,
            "conversion_rate": overview["totals"]["conversion_rate"],
            "satisfaction_rate": feedback["satisfaction_rate"],
            "ai_cost": ai_cost,
            "human_equivalent_cost": human_equiv_cost,
            "estimated_savings": estimated_savings,
            "roi_multiple": roi,
        },
        "series": {
            "conversations": overview["series"]["conversations"],
            "cost": cost["series"]["cost"],
        },
        "breakdowns": {
            "conversations_by_channel": overview["breakdowns"]["conversations_by_channel"],
            "cost_by_model": cost["breakdowns"]["by_model"],
        },
        "top_agents": overview["top_agents"],
    }


# Module dispatch table consumed by the API layer (/api/analytics/{module},
# /api/v1/analytics/{module}).
MODULE_FUNCTIONS = {
    "chat": chat_analytics,
    "conversations": chat_analytics,
    "agents": agent_analytics,
    "knowledge": knowledge_analytics,
    "rag": rag_analytics,
    "widget": widget_analytics,
    "widgets": widget_analytics,
    "workflows": workflow_analytics,
    "integrations": integration_analytics,
    "cost": cost_analytics,
    "insights": insights_analytics,
    "questions": insights_analytics,
    "users": user_team_analytics,
    "team": user_team_analytics,
    "executive": executive_summary,
}
