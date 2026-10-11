"""Quota model — DESIGN ONLY (not enforced yet).

Entitlements answer *"may this org use product X?"* (a boolean). Quotas answer
the next question: *"how much of X may they use?"* — AI requests,
knowledge-base size, storage, projects, seats, API calls.

This module lays the foundation so the rest of OraOne can be written against a
stable quota API today, while enforcement is switched on later:

    * :class:`QuotaKey`      — the canonical quota identifiers.
    * :data:`QUOTA_SPECS`    — metadata (label / unit / period) per quota.
    * :data:`DEFAULT_LIMITS` — per-plan default limits (``-1`` == unlimited).
    * :func:`resolve_limit`  — the effective limit for an org/plan+key.
    * :func:`check_quota`    — returns a :class:`QuotaDecision`.

**Enforcement is intentionally off.** ``check_quota`` always resolves to
``allowed=True`` because there is no usage meter wired up yet — the ``used``
field is a placeholder (0) and the caller (``AuthorizationService``) only ever
denies on quota when ``AUTHZ_ENFORCE_QUOTAS`` is set. When a real usage source
exists (a metering table / time-series counter), fill in ``_current_usage``.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

UNLIMITED = -1


class QuotaKey:
    """Canonical quota identifiers (stable strings, safe for storage)."""

    AI_REQUESTS = "ai_requests"
    KB_SIZE_MB = "kb_size_mb"
    STORAGE_MB = "storage_mb"
    PROJECTS = "projects"
    USERS = "users"
    API_CALLS = "api_calls"

    ALL = (
        AI_REQUESTS, KB_SIZE_MB, STORAGE_MB,
        PROJECTS, USERS, API_CALLS,
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
        QuotaKey.AI_REQUESTS, "AI Requests", "requests", "month",
        "LLM completions / agent turns per billing period.",
    ),
    QuotaKey.KB_SIZE_MB: QuotaSpec(
        QuotaKey.KB_SIZE_MB, "Knowledge Base Size", "MB", "total",
        "Total stored, indexed knowledge-base content.",
    ),
    QuotaKey.STORAGE_MB: QuotaSpec(
        QuotaKey.STORAGE_MB, "Storage", "MB", "total",
        "Total object storage (uploads, recordings, exports).",
    ),
    QuotaKey.PROJECTS: QuotaSpec(
        QuotaKey.PROJECTS, "Projects", "projects", "total",
        "Concurrent workspaces / projects in the organization.",
    ),
    QuotaKey.USERS: QuotaSpec(
        QuotaKey.USERS, "Users", "seats", "total",
        "Active member seats in the organization.",
    ),
    QuotaKey.API_CALLS: QuotaSpec(
        QuotaKey.API_CALLS, "API Calls", "calls", "month",
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
    limit: int          # -1 == unlimited
    used: int
    remaining: int      # -1 == unlimited
    outcome: str        # "allow" | "exceeded" | "unmetered"
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
    table = DEFAULT_LIMITS.get((plan_code or _DEFAULT_PLAN), DEFAULT_LIMITS[_DEFAULT_PLAN])
    return int(table.get(key, UNLIMITED))


async def _current_usage(session: AsyncSession, organization_id: uuid.UUID, key: str) -> Optional[int]:
    """Return the org's current usage for ``key``, or ``None`` if unmetered.

    DESIGN STUB: no metering source is wired up yet, so this always returns
    ``None`` (unmetered). When a usage table / counter exists, resolve it here
    and quota enforcement lights up automatically.
    """
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

    Returns ``outcome="unmetered"`` (allowed) while there's no usage source,
    ``"allow"`` when usage+amount fits the limit, or ``"exceeded"`` otherwise.
    """
    limit = resolve_limit(key, plan_code=plan_code, plan_limits=plan_limits)
    if limit == UNLIMITED:
        return QuotaDecision(True, key, UNLIMITED, 0, UNLIMITED, "allow")

    used = await _current_usage(session, organization_id, key)
    if used is None:
        # No meter yet — surface the limit but don't block.
        return QuotaDecision(True, key, limit, 0, limit, "unmetered")

    remaining = max(limit - used, 0)
    allowed = (used + amount) <= limit
    return QuotaDecision(
        allowed, key, limit, used, remaining,
        "allow" if allowed else "exceeded",
    )
