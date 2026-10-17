"""Quota model — measured where a usage source exists, fail-closed otherwise.

Entitlements answer *"may this org use product X?"* (a boolean). Quotas answer
the next question: *"how much of X may they use?"*.

    * :class:`QuotaKey`      — the canonical quota identifiers.
    * :data:`QUOTA_SPECS`    — metadata (label / unit / period) per quota.
    * :data:`DEFAULT_LIMITS` — per-plan default limits (``-1`` == unlimited).
    * :func:`resolve_limit`  — the effective limit for an org/plan+key.
    * :func:`check_quota`    — returns a :class:`QuotaDecision`.

Usage is measured from data the product already records (no new billing
metrics):

    * ``users``      — active organization members.
    * ``projects``   — live (not soft-deleted) projects.
    * ``kb_size_mb`` — summed ``documents.file_size`` of live documents.
    * ``ai_requests``— ``ai_messages`` counter, summed over the current month.
    * ``api_calls``  — ``api_calls`` counter for the current month.

``storage_mb`` has no complete source (recordings and exports are not
metered), so it is unmeasured.

Unmeasured quotas: in production ``check_quota`` returns ``allowed=False`` with
outcome ``"unmeasured"`` and a plain reason, so the request fails closed. In
development the quota is allowed so local work is not blocked. Unlimited plan
limits never need a measurement and are always allowed.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.models.document import Document
from app.database.models.organization_member import MemberStatus, OrganizationMember
from app.database.models.project import Project
from app.database.models.usage import UsageCounter

UNLIMITED = -1
UNMEASURED_REASON = "We cannot check this limit yet."
_BYTES_PER_MB = 1024 * 1024


class QuotaKey:
    """Canonical quota identifiers (stable strings, safe for storage)."""

    AI_REQUESTS = "ai_requests"
    KB_SIZE_MB = "kb_size_mb"
    STORAGE_MB = "storage_mb"
    PROJECTS = "projects"
    USERS = "users"
    API_CALLS = "api_calls"

    ALL = (
        AI_REQUESTS,
        KB_SIZE_MB,
        STORAGE_MB,
        PROJECTS,
        USERS,
        API_CALLS,
    )


@dataclass(frozen=True)
class QuotaSpec:
    key: str
    label: str
    unit: str
    period: str  # "month" | "total"
    description: str


QUOTA_SPECS: dict[str, QuotaSpec] = {
    QuotaKey.AI_REQUESTS: QuotaSpec(
        QuotaKey.AI_REQUESTS,
        "AI Requests",
        "requests",
        "month",
        "LLM completions / agent turns per billing period.",
    ),
    QuotaKey.KB_SIZE_MB: QuotaSpec(
        QuotaKey.KB_SIZE_MB,
        "Knowledge Base Size",
        "MB",
        "total",
        "Total stored, indexed knowledge-base content.",
    ),
    QuotaKey.STORAGE_MB: QuotaSpec(
        QuotaKey.STORAGE_MB,
        "Storage",
        "MB",
        "total",
        "Total object storage (uploads, recordings, exports).",
    ),
    QuotaKey.PROJECTS: QuotaSpec(
        QuotaKey.PROJECTS,
        "Projects",
        "projects",
        "total",
        "Concurrent workspaces / projects in the organization.",
    ),
    QuotaKey.USERS: QuotaSpec(
        QuotaKey.USERS,
        "Users",
        "seats",
        "total",
        "Active member seats in the organization.",
    ),
    QuotaKey.API_CALLS: QuotaSpec(
        QuotaKey.API_CALLS,
        "API Calls",
        "calls",
        "month",
        "Public API requests per billing period.",
    ),
}


# Per-plan default limits (-1 == unlimited). A subscription's ``plan.limits``
# JSONB overrides these where present, so ops can tune a single account without
# a code change.
DEFAULT_LIMITS: dict[str, dict[str, int]] = {
    "free": {
        QuotaKey.AI_REQUESTS: 1_000,
        QuotaKey.KB_SIZE_MB: 100,
        QuotaKey.STORAGE_MB: 512,
        QuotaKey.PROJECTS: 1,
        QuotaKey.USERS: 2,
        QuotaKey.API_CALLS: 5_000,
    },
    "starter": {
        QuotaKey.AI_REQUESTS: 25_000,
        QuotaKey.KB_SIZE_MB: 2_048,
        QuotaKey.STORAGE_MB: 10_240,
        QuotaKey.PROJECTS: 3,
        QuotaKey.USERS: 10,
        QuotaKey.API_CALLS: 100_000,
    },
    "business": {
        QuotaKey.AI_REQUESTS: 250_000,
        QuotaKey.KB_SIZE_MB: 20_480,
        QuotaKey.STORAGE_MB: 102_400,
        QuotaKey.PROJECTS: 25,
        QuotaKey.USERS: 100,
        QuotaKey.API_CALLS: 1_000_000,
    },
    "enterprise": {
        QuotaKey.AI_REQUESTS: UNLIMITED,
        QuotaKey.KB_SIZE_MB: UNLIMITED,
        QuotaKey.STORAGE_MB: UNLIMITED,
        QuotaKey.PROJECTS: UNLIMITED,
        QuotaKey.USERS: UNLIMITED,
        QuotaKey.API_CALLS: UNLIMITED,
    },
}

# Fallback plan when an org has no subscription row yet.
_DEFAULT_PLAN = "free"


@dataclass
class QuotaDecision:
    allowed: bool
    key: str
    limit: int  # -1 == unlimited
    used: int
    remaining: int  # -1 == unlimited
    outcome: str  # "allow" | "exceeded" | "unmeasured"
    meta: dict[str, Any] = field(default_factory=dict)


def resolve_limit(
    key: str,
    *,
    plan_code: Optional[str] = None,
    plan_limits: Optional[dict[str, Any]] = None,
) -> int:
    """Effective limit for a quota key: subscription override → plan default."""
    if plan_limits and key in plan_limits:
        try:
            return int(plan_limits[key])
        except (TypeError, ValueError):
            pass
    table = DEFAULT_LIMITS.get(
        (plan_code or _DEFAULT_PLAN), DEFAULT_LIMITS[_DEFAULT_PLAN]
    )
    return int(table.get(key, UNLIMITED))


def _current_month_prefix(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m")


async def _counter_month_total(
    session: AsyncSession, organization_id: uuid.UUID, metric: str
) -> int:
    """Sum a metered counter over the current calendar month (any granularity)."""
    prefix = _current_month_prefix()
    total = await session.scalar(
        select(func.coalesce(func.sum(UsageCounter.value), 0)).where(
            UsageCounter.organization_id == organization_id,
            UsageCounter.metric == metric,
            UsageCounter.period.startswith(prefix),
        )
    )
    return int(total or 0)


async def _current_usage(
    session: AsyncSession, organization_id: uuid.UUID, key: str
) -> Optional[int]:
    """Return the org's current usage for ``key``, or ``None`` if unmeasured.

    Units match :data:`QUOTA_SPECS`. ``None`` means there is no complete
    measurement source, and :func:`check_quota` decides fail-closed vs allow.
    """
    if key == QuotaKey.AI_REQUESTS:
        return await _counter_month_total(session, organization_id, "ai_messages")

    if key == QuotaKey.API_CALLS:
        return await _counter_month_total(session, organization_id, "api_calls")

    if key == QuotaKey.USERS:
        val = await session.scalar(
            select(func.count())
            .select_from(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.status == MemberStatus.active,
                OrganizationMember.deleted_at.is_(None),
            )
        )
        return int(val or 0)

    if key == QuotaKey.PROJECTS:
        val = await session.scalar(
            select(func.count())
            .select_from(Project)
            .where(
                Project.organization_id == organization_id,
                Project.deleted_at.is_(None),
            )
        )
        return int(val or 0)

    if key == QuotaKey.KB_SIZE_MB:
        total_bytes = await session.scalar(
            select(func.coalesce(func.sum(Document.file_size), 0)).where(
                Document.organization_id == organization_id,
                Document.deleted_at.is_(None),
            )
        )
        # Round up so any partial megabyte counts against the limit.
        return -(-int(total_bytes or 0) // _BYTES_PER_MB)

    # STORAGE_MB and any unknown key: no complete measurement source.
    return None


async def check_quota(
    session: AsyncSession,
    organization_id: uuid.UUID,
    key: str,
    *,
    amount: int = 1,
    plan_code: Optional[str] = None,
    plan_limits: Optional[dict[str, Any]] = None,
) -> QuotaDecision:
    """Evaluate a quota. Never *enforces* on its own — the caller decides.

    Returns ``outcome="allow"`` when usage+amount fits the limit,
    ``"exceeded"`` when it does not, and ``"unmeasured"`` when no usage source
    exists (denied in production, allowed in development).
    """
    limit = resolve_limit(key, plan_code=plan_code, plan_limits=plan_limits)
    if limit == UNLIMITED:
        return QuotaDecision(True, key, UNLIMITED, 0, UNLIMITED, "allow")

    used = await _current_usage(session, organization_id, key)
    if used is None:
        # No measurable source. Production fails closed; development allows
        # so local work is not blocked. Both carry the plain reason.
        allowed = not settings.is_production
        return QuotaDecision(
            allowed,
            key,
            limit,
            0,
            limit if allowed else 0,
            "unmeasured",
            meta={"reason": UNMEASURED_REASON},
        )

    remaining = max(limit - used, 0)
    allowed = (used + amount) <= limit
    return QuotaDecision(
        allowed,
        key,
        limit,
        used,
        remaining,
        "allow" if allowed else "exceeded",
    )
