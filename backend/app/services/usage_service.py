"""Usage metering & quota enforcement (Phase 12, Module 2).

Two kinds of metrics:

* **Resource** metrics (``users``, ``agents``, ``knowledge_bases``,
  ``workflows``, ``integrations``) — counted live from their own tables.
  A quota is the maximum number that may exist at once.

* **Metered** metrics (``ai_messages``, ``workflow_runs``, ``api_calls``,
  ``documents_processed``) — cumulative event counters stored in
  ``usage_counters`` and bucketed by period (daily or monthly). The quota
  is the maximum events allowed within the current window.

Plan limits live on ``Plan.limits`` (a JSON dict; ``-1`` / missing means
unlimited). The active plan is resolved via the org's subscription.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.integration import Integration
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.organization_member import MemberStatus, OrganizationMember
from app.database.models.usage import UsageCounter
from app.database.models.workflow import Workflow
from app.services import billing_service

UNLIMITED = -1

# ── metric registry ─────────────────────────────────────────────────────
# Resource metrics: live counts. ``limit_key`` maps onto Plan.limits.
RESOURCE_METRICS: dict[str, dict] = {
    "users": {"label": "Team Members", "limit_key": "users", "model": OrganizationMember},
    "agents": {"label": "Agents", "limit_key": "agents", "model": Agent},
    "knowledge_bases": {"label": "Knowledge Bases", "limit_key": "knowledge_bases", "model": KnowledgeBase},
    "workflows": {"label": "Workflows", "limit_key": "workflows", "model": Workflow},
    "integrations": {"label": "Integrations", "limit_key": "integrations", "model": Integration},
}

# Metered metrics: accumulating counters. ``granularity`` decides the bucket.
METERED_METRICS: dict[str, dict] = {
    "ai_messages": {"label": "AI Messages / day", "limit_key": "ai_messages_per_day", "granularity": "day"},
    "workflow_runs": {"label": "Workflow Runs / mo", "limit_key": None, "granularity": "month"},
    "api_calls": {"label": "API Calls / mo", "limit_key": None, "granularity": "month"},
    "documents_processed": {"label": "Documents Processed / mo", "limit_key": None, "granularity": "month"},
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def period_key(granularity: str, *, at: Optional[datetime] = None) -> str:
    """Return the bucket key for a metered metric."""
    moment = at or _now()
    if granularity == "month":
        return moment.strftime("%Y-%m")
    return moment.strftime("%Y-%m-%d")  # default: daily


def _limit_for(limits: dict, key: Optional[str]) -> int:
    """Resolve a plan limit. Missing key or -1 => unlimited."""
    if not key:
        return UNLIMITED
    val = limits.get(key, UNLIMITED)
    try:
        return int(val)
    except (TypeError, ValueError):
        return UNLIMITED


# ── plan limits ──────────────────────────────────────────────────────────
async def _plan_for(session: AsyncSession, organization_id: uuid.UUID):
    sub = await billing_service.get_or_create_subscription(session, organization_id)
    return sub.plan


# ── recording metered events ──────────────────────────────────────────────
async def record_usage(
    session: AsyncSession,
    organization_id: uuid.UUID,
    metric: str,
    amount: int = 1,
) -> int:
    """Atomically increment a metered counter; returns the new period total.

    Unknown metrics are ignored (returns 0) so callers can fire-and-forget
    without coupling to the registry. Uses an upsert so concurrent writers
    don't lose increments.
    """
    spec = METERED_METRICS.get(metric)
    if spec is None or amount == 0:
        return 0

    period = period_key(spec["granularity"])
    stmt = (
        pg_insert(UsageCounter)
        .values(
            id=uuid.uuid4(),
            organization_id=organization_id,
            metric=metric,
            period=period,
            value=amount,
        )
        .on_conflict_do_update(
            constraint="uq_usage_counters_org_metric_period",
            set_={"value": UsageCounter.value + amount, "updated_at": _now()},
        )
        .returning(UsageCounter.value)
    )
    result = await session.execute(stmt)
    await session.commit()
    return int(result.scalar_one())


async def _metered_value(
    session: AsyncSession, organization_id: uuid.UUID, metric: str
) -> int:
    spec = METERED_METRICS[metric]
    period = period_key(spec["granularity"])
    val = await session.scalar(
        select(UsageCounter.value).where(
            UsageCounter.organization_id == organization_id,
            UsageCounter.metric == metric,
            UsageCounter.period == period,
        )
    )
    return int(val or 0)


async def _resource_count(
    session: AsyncSession, organization_id: uuid.UUID, metric: str
) -> int:
    spec = RESOURCE_METRICS[metric]
    model = spec["model"]
    stmt = select(func.count()).select_from(model).where(
        model.organization_id == organization_id
    )
    # Exclude soft-deleted rows where the column exists.
    if hasattr(model, "deleted_at"):
        stmt = stmt.where(model.deleted_at.is_(None))
    # For members, only count active seats.
    if model is OrganizationMember:
        stmt = stmt.where(OrganizationMember.status == MemberStatus.active)
    val = await session.scalar(stmt)
    return int(val or 0)


# ── snapshot ──────────────────────────────────────────────────────────────
def _entry(metric: str, label: str, category: str, used: int, limit: int, period: Optional[str]) -> dict:
    unlimited = limit == UNLIMITED
    percent = 0
    if not unlimited and limit > 0:
        percent = min(100, round((used / limit) * 100))
    return {
        "metric": metric,
        "label": label,
        "category": category,
        "used": used,
        "limit": limit,
        "unlimited": unlimited,
        "percent": percent,
        "period": period,
    }


async def usage_snapshot(
    session: AsyncSession, organization_id: uuid.UUID
) -> dict:
    """Build the full usage-vs-limits view for an organization."""
    plan = await _plan_for(session, organization_id)
    limits = plan.limits or {}

    metrics: list[dict] = []
    for key, spec in RESOURCE_METRICS.items():
        used = await _resource_count(session, organization_id, key)
        limit = _limit_for(limits, spec["limit_key"])
        metrics.append(_entry(key, spec["label"], "resource", used, limit, None))

    for key, spec in METERED_METRICS.items():
        used = await _metered_value(session, organization_id, key)
        limit = _limit_for(limits, spec["limit_key"])
        period = period_key(spec["granularity"])
        metrics.append(_entry(key, spec["label"], "metered", used, limit, period))

    return {
        "plan_code": plan.code.value,
        "plan_name": plan.name,
        "metrics": metrics,
        "generated_at": _now(),
    }


# ── quota checks / enforcement ────────────────────────────────────────────
async def check_quota(
    session: AsyncSession,
    organization_id: uuid.UUID,
    metric: str,
    amount: int = 1,
) -> dict:
    """Return whether ``amount`` more of ``metric`` is within the plan quota.

    Unknown metrics are treated as unlimited (allowed) so callers stay
    decoupled. ``remaining`` is ``None`` for unlimited metrics.
    """
    plan = await _plan_for(session, organization_id)
    limits = plan.limits or {}

    if metric in RESOURCE_METRICS:
        limit = _limit_for(limits, RESOURCE_METRICS[metric]["limit_key"])
        used = await _resource_count(session, organization_id, metric)
    elif metric in METERED_METRICS:
        limit = _limit_for(limits, METERED_METRICS[metric]["limit_key"])
        used = await _metered_value(session, organization_id, metric)
    else:
        return {"metric": metric, "allowed": True, "used": 0, "limit": UNLIMITED,
                "remaining": None, "unlimited": True}

    if limit == UNLIMITED:
        return {"metric": metric, "allowed": True, "used": used, "limit": UNLIMITED,
                "remaining": None, "unlimited": True}

    remaining = max(0, limit - used)
    return {
        "metric": metric,
        "allowed": used + amount <= limit,
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "unlimited": False,
    }


async def enforce_quota(
    session: AsyncSession,
    organization_id: uuid.UUID,
    metric: str,
    amount: int = 1,
) -> None:
    """Raise HTTP 402 if granting ``amount`` more of ``metric`` exceeds quota."""
    check = await check_quota(session, organization_id, metric, amount)
    if not check["allowed"]:
        label = (
            RESOURCE_METRICS.get(metric) or METERED_METRICS.get(metric) or {}
        ).get("label", metric)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Plan limit reached for '{label}' "
                f"({check['used']}/{check['limit']}). Upgrade your plan to continue."
            ),
        )
