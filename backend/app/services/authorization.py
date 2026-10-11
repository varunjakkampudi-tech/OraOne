"""AuthorizationService — the single authorization pipeline for OraOne.

Every authorization question in the platform flows through one function,
:func:`authorize`, which evaluates an ordered chain of **policies**:

    Authentication → Subscription → Maintenance → Entitlement
        → Feature Flag → Permission (RBAC) → Quota

Each policy inspects one shared :class:`AuthorizationContext` and returns
``allow`` / ``deny`` / ``skip``. The engine stops at the first ``deny`` and
records a :class:`DecisionTrace` of every step, so a denied request explains
*exactly* which policy blocked it (invaluable in production).

Callers never hand-roll ``if feature_enabled`` checks. Routes attach a dependency
(:func:`require_product` / :func:`require_feature` / :func:`require_permission`
/ :func:`require_authorization`); WebSockets and background jobs call
:func:`authorize` directly and inspect the returned :class:`AuthzDecision` (no
HTTP exception is raised for them).

The decision carries a rich *outcome* — not just allow/deny:

    allow · deny · maintenance · coming_soon · trial_expired
    · subscription_expired · usage_exceeded · unauthenticated

Enforcement policy:
    * Authentication / entitlement / maintenance / feature / RBAC are
      **enforced** (they already were).
    * Subscription and quota policies are **evaluated and observable** but only
      *deny* when their env switch is on (``AUTHZ_ENFORCE_SUBSCRIPTION`` /
      ``AUTHZ_ENFORCE_QUOTAS``). This lets us design + monitor them now and turn
      enforcement on deliberately, without bricking existing tenants.

Plan resolution: an org with no subscription row is **not** special-cased — it
resolves to the default Free plan and is evaluated like every other plan, so
authorization and (later) billing stay consistent.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import has_permission, permissions_for
from app.database.models.billing import Subscription
from app.database.models.product import ProductStatus
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.services import entitlements as ent
from app.services import metrics
from app.services import quotas

log = logging.getLogger("app.authorization")


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").strip().lower() in {"1", "true", "yes", "on"}


# Enforcement switches (design-now, enforce-later).
ENFORCE_SUBSCRIPTION = _flag("AUTHZ_ENFORCE_SUBSCRIPTION", False)
ENFORCE_QUOTAS = _flag("AUTHZ_ENFORCE_QUOTAS", False)


class AuthzOutcome:
    ALLOW = "allow"
    DENY = "deny"
    MAINTENANCE = "maintenance"
    COMING_SOON = "coming_soon"
    TRIAL_EXPIRED = "trial_expired"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    USAGE_EXCEEDED = "usage_exceeded"
    UNAUTHENTICATED = "unauthenticated"


#: Outcome → HTTP status for the dependency guards.
OUTCOME_STATUS: dict[str, int] = {
    AuthzOutcome.ALLOW: 200,
    AuthzOutcome.DENY: 403,
    AuthzOutcome.MAINTENANCE: 503,
    AuthzOutcome.COMING_SOON: 403,
    AuthzOutcome.TRIAL_EXPIRED: 402,
    AuthzOutcome.SUBSCRIPTION_EXPIRED: 402,
    AuthzOutcome.USAGE_EXCEEDED: 429,
    AuthzOutcome.UNAUTHENTICATED: 401,
}

_DENIED_OUTCOMES = frozenset(OUTCOME_STATUS) - {AuthzOutcome.ALLOW}


class PolicyResult:
    """The verdict a single policy returns."""

    ALLOW = "allow"   # this policy is satisfied; keep evaluating
    DENY = "deny"     # stop; the request is denied
    SKIP = "skip"     # not applicable (or evaluated-but-not-enforced)


@dataclass
class PolicyEval:
    """What one policy reports for the current context."""

    result: str                                  # PolicyResult.*
    outcome: str = AuthzOutcome.ALLOW            # meaningful when result == DENY
    reason: Optional[str] = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthzDecision:
    """The result of one authorization evaluation."""

    allowed: bool
    outcome: str
    http_status: int
    reason: Optional[str] = None
    product: Optional[str] = None
    feature: Optional[str] = None
    permission: Optional[str] = None
    quota: Optional[str] = None
    meta: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)

    def raise_for_denied(self) -> None:
        """Raise an ``HTTPException`` mirroring the decision if denied."""
        if not self.allowed:
            raise HTTPException(
                status_code=self.http_status,
                detail=self.reason or "You are not authorized to perform this action.",
            )


def _allow(**kw: Any) -> AuthzDecision:
    return AuthzDecision(True, AuthzOutcome.ALLOW, 200, **kw)


def _deny(outcome: str, reason: str, **kw: Any) -> AuthzDecision:
    return AuthzDecision(False, outcome, OUTCOME_STATUS[outcome], reason=reason, **kw)


# --------------------------------------------------------------------------- #
# Subscription stage                                                          #
# --------------------------------------------------------------------------- #
async def _subscription_state(session: AsyncSession, organization_id: uuid.UUID) -> dict[str, Any]:
    """Resolve an org's subscription posture (never raises).

    An org with no subscription row is **not** special-cased: it resolves to
    the default Free plan (``quotas._DEFAULT_PLAN``) and is evaluated like any
    other plan. Only explicitly terminal states (canceled / incomplete, or an
    expired trial) are marked ``blocked``.
    """
    try:
        sub = await session.scalar(
            select(Subscription).where(Subscription.organization_id == organization_id)
        )
    except Exception as e:  # pragma: no cover — resilience if table absent
        log.warning("subscription lookup failed for %s: %s", organization_id, e)
        return {"status": "unknown", "plan_code": quotas._DEFAULT_PLAN, "plan_limits": None,
                "blocked": False, "outcome": AuthzOutcome.ALLOW, "reason": None,
                "plan_source": "default_free"}

    if sub is None:
        # No subscription → resolve the default Free plan (consistent evaluation).
        return {"status": "none", "plan_code": quotas._DEFAULT_PLAN, "plan_limits": None,
                "blocked": False, "outcome": AuthzOutcome.ALLOW, "reason": None,
                "plan_source": "default_free"}

    status_value = getattr(sub.status, "value", str(sub.status))
    plan = getattr(sub, "plan", None)
    plan_code = getattr(getattr(plan, "code", None), "value", None) if plan else None
    plan_limits = getattr(plan, "limits", None) if plan else None
    now = datetime.now(timezone.utc)

    blocked, outcome, reason = False, AuthzOutcome.ALLOW, None
    if status_value in {"canceled", "incomplete"}:
        blocked, outcome = True, AuthzOutcome.SUBSCRIPTION_EXPIRED
        reason = "Your subscription is inactive. Please renew to continue."
    elif status_value == "trialing" and sub.current_period_end and sub.current_period_end < now:
        blocked, outcome = True, AuthzOutcome.TRIAL_EXPIRED
        reason = "Your free trial has ended. Upgrade to keep access."

    return {"status": status_value, "plan_code": plan_code or quotas._DEFAULT_PLAN,
            "plan_limits": plan_limits, "blocked": blocked, "outcome": outcome,
            "reason": reason, "plan_source": "subscription"}


# --------------------------------------------------------------------------- #
# Authorization context — one object every policy reads                        #
# --------------------------------------------------------------------------- #
@dataclass
class AuthorizationContext:
    """Everything a policy needs, resolved once and shared across the chain.

    The DB-backed pieces (subscription, entitlement snapshot) are resolved
    lazily and memoised so a chain never hits the DB twice for the same thing.
    """

    session: Optional[AsyncSession]
    org: Optional[OrgContext]
    product: Optional[str] = None
    feature: Optional[str] = None
    permission: Optional[str] = None
    quota: Optional[str] = None
    quota_amount: int = 1
    request: Any = None
    workspace_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    meta: dict[str, Any] = field(default_factory=dict)
    _subscription: Optional[dict[str, Any]] = field(default=None, repr=False)
    _snapshot: Optional[dict[str, Any]] = field(default=None, repr=False)

    # -- identity ----------------------------------------------------------- #
    @property
    def authenticated(self) -> bool:
        return self.org is not None and getattr(self.org, "organization_id", None) is not None

    @property
    def organization_id(self) -> Optional[uuid.UUID]:
        return getattr(self.org, "organization_id", None)

    @property
    def user_id(self) -> Optional[uuid.UUID]:
        return getattr(self.org, "user_id", None)

    @property
    def role(self) -> str:
        return getattr(self.org, "membership_role", "") or ""

    @property
    def roles(self) -> list[str]:
        return [self.role] if self.role else []

    @property
    def permissions(self) -> list[str]:
        return sorted(permissions_for(self.role)) if self.role else []

    # -- lazily-resolved state --------------------------------------------- #
    async def subscription(self) -> dict[str, Any]:
        if self._subscription is None:
            self._subscription = await _subscription_state(self.session, self.organization_id)
        return self._subscription

    async def snapshot(self) -> dict[str, Any]:
        if self._snapshot is None:
            self._snapshot = await ent.get_cached_snapshot(self.session, self.organization_id)
        return self._snapshot

    @property
    def products(self) -> dict[str, bool]:
        return (self._snapshot or {}).get("products", {})

    @property
    def features(self) -> dict[str, bool]:
        return (self._snapshot or {}).get("features", {})


# --------------------------------------------------------------------------- #
# Policies                                                                     #
# --------------------------------------------------------------------------- #
class Policy:
    """A single, composable authorization rule."""

    name = "policy"

    async def evaluate(self, actx: AuthorizationContext) -> PolicyEval:  # pragma: no cover
        raise NotImplementedError


class AuthenticationPolicy(Policy):
    name = "authentication"

    async def evaluate(self, actx: AuthorizationContext) -> PolicyEval:
        if not actx.authenticated:
            return PolicyEval(PolicyResult.DENY, AuthzOutcome.UNAUTHENTICATED,
                              "Authentication required.")
        return PolicyEval(PolicyResult.ALLOW)


class SubscriptionPolicy(Policy):
    """Blocks on inactive subscription / expired trial. Handles both the
    ``subscription_expired`` and ``trial_expired`` outcomes."""

    name = "subscription"

    async def evaluate(self, actx: AuthorizationContext) -> PolicyEval:
        sub = await actx.subscription()
        actx.meta["subscription"] = sub["status"]
        actx.meta["plan"] = sub.get("plan_code")
        if not sub["blocked"]:
            return PolicyEval(PolicyResult.ALLOW,
                              detail={"status": sub["status"], "plan": sub.get("plan_code")})
        metrics.inc("authorization_subscription_blocked_total", outcome=sub["outcome"])
        if ENFORCE_SUBSCRIPTION:
            return PolicyEval(PolicyResult.DENY, sub["outcome"], sub["reason"])
        # Evaluated but enforcement is off — record and continue.
        return PolicyEval(PolicyResult.SKIP, sub["outcome"], sub["reason"],
                          detail={"would_deny": True, "enforced": False})


class MaintenancePolicy(Policy):
    name = "maintenance"

    async def evaluate(self, actx: AuthorizationContext) -> PolicyEval:
        if not actx.product:
            return PolicyEval(PolicyResult.SKIP)
        snap = await actx.snapshot()
        if snap.get("maintenance", {}).get(actx.product, False):
            metrics.inc("maintenance_denied_total", product=actx.product)
            return PolicyEval(PolicyResult.DENY, AuthzOutcome.MAINTENANCE,
                              f"The '{actx.product}' product is temporarily under maintenance.")
        return PolicyEval(PolicyResult.ALLOW)


class EntitlementPolicy(Policy):
    name = "entitlement"

    async def evaluate(self, actx: AuthorizationContext) -> PolicyEval:
        if not actx.product:
            return PolicyEval(PolicyResult.SKIP)
        snap = await actx.snapshot()
        if snap.get("products", {}).get(actx.product, False):
            return PolicyEval(PolicyResult.ALLOW)
        status_value = snap.get("statuses", {}).get(actx.product)
        if status_value == ProductStatus.COMING_SOON:
            return PolicyEval(PolicyResult.DENY, AuthzOutcome.COMING_SOON,
                              f"The '{actx.product}' product is coming soon and isn't available yet.")
        return PolicyEval(PolicyResult.DENY, AuthzOutcome.DENY,
                          f"Your workspace does not have access to the '{actx.product}' "
                          "product. Contact your administrator.")


class FeaturePolicy(Policy):
    name = "feature_flag"

    async def evaluate(self, actx: AuthorizationContext) -> PolicyEval:
        if not actx.feature:
            return PolicyEval(PolicyResult.SKIP)
        snap = await actx.snapshot()
        metrics.inc("feature_flag_evaluations_total", feature=actx.feature)
        if snap.get("features", {}).get(actx.feature, False):
            return PolicyEval(PolicyResult.ALLOW)
        return PolicyEval(PolicyResult.DENY, AuthzOutcome.DENY,
                          f"The '{actx.feature}' feature is not enabled for your workspace.")


class PermissionPolicy(Policy):
    name = "permission"

    async def evaluate(self, actx: AuthorizationContext) -> PolicyEval:
        if not actx.permission:
            return PolicyEval(PolicyResult.SKIP)
        if has_permission(actx.role, actx.permission):
            return PolicyEval(PolicyResult.ALLOW)
        return PolicyEval(PolicyResult.DENY, AuthzOutcome.DENY,
                          f"Your role does not permit '{actx.permission}'.")


class QuotaPolicy(Policy):
    name = "quota"

    async def evaluate(self, actx: AuthorizationContext) -> PolicyEval:
        if not actx.quota:
            return PolicyEval(PolicyResult.SKIP)
        sub = await actx.subscription()
        qd = await quotas.check_quota(
            actx.session, actx.organization_id, actx.quota,
            amount=actx.quota_amount, plan_code=sub["plan_code"],
            plan_limits=sub["plan_limits"],
        )
        actx.meta["quota"] = {"key": qd.key, "limit": qd.limit, "used": qd.used,
                              "remaining": qd.remaining, "outcome": qd.outcome}
        if qd.allowed:
            return PolicyEval(PolicyResult.ALLOW, detail=actx.meta["quota"])
        metrics.inc("quota_exceeded_total", quota=actx.quota)
        if ENFORCE_QUOTAS:
            return PolicyEval(PolicyResult.DENY, AuthzOutcome.USAGE_EXCEEDED,
                              f"You have reached your '{actx.quota}' limit for this billing period.")
        return PolicyEval(PolicyResult.SKIP, AuthzOutcome.USAGE_EXCEEDED,
                          detail={"would_deny": True, "enforced": False, **actx.meta["quota"]})


#: The ordered policy chain. Prepend/append to extend authorization without
#: touching :func:`authorize` — adding a future rule is a one-line change.
DEFAULT_POLICIES: tuple[Policy, ...] = (
    AuthenticationPolicy(),
    SubscriptionPolicy(),
    MaintenancePolicy(),
    EntitlementPolicy(),
    FeaturePolicy(),
    PermissionPolicy(),
    QuotaPolicy(),
)


# --------------------------------------------------------------------------- #
# Policy engine                                                               #
# --------------------------------------------------------------------------- #
async def _run_policies(
    actx: AuthorizationContext,
    policies: tuple[Policy, ...] = DEFAULT_POLICIES,
) -> AuthzDecision:
    """Evaluate the chain, stopping at the first deny. Builds a full trace."""
    trace: list[dict[str, Any]] = []
    for policy in policies:
        ev = await policy.evaluate(actx)
        entry: dict[str, Any] = {"policy": policy.name, "result": ev.result}
        if ev.result == PolicyResult.DENY:
            entry["outcome"] = ev.outcome
        if ev.reason:
            entry["reason"] = ev.reason
        if ev.detail:
            entry["detail"] = ev.detail
        trace.append(entry)
        if ev.result == PolicyResult.DENY:
            return _deny(ev.outcome, ev.reason or "Denied.",
                         product=actx.product, feature=actx.feature,
                         permission=actx.permission, quota=actx.quota,
                         meta=actx.meta, trace=trace)
    return _allow(product=actx.product, feature=actx.feature,
                  permission=actx.permission, quota=actx.quota,
                  meta=actx.meta, trace=trace)


def build_context(
    session: Optional[AsyncSession],
    ctx: Optional[OrgContext],
    *,
    product: Optional[str] = None,
    feature: Optional[str] = None,
    permission: Optional[str] = None,
    quota: Optional[str] = None,
    quota_amount: int = 1,
    request: Any = None,
) -> AuthorizationContext:
    """Assemble the :class:`AuthorizationContext` for a request/intent."""
    return AuthorizationContext(
        session=session, org=ctx, product=product, feature=feature,
        permission=permission, quota=quota, quota_amount=quota_amount,
        request=request,
    )


async def authorize(
    session: Optional[AsyncSession],
    ctx: Optional[OrgContext],
    *,
    product: Optional[str] = None,
    feature: Optional[str] = None,
    permission: Optional[str] = None,
    quota: Optional[str] = None,
    quota_amount: int = 1,
    request: Any = None,
    policies: tuple[Policy, ...] = DEFAULT_POLICIES,
) -> AuthzDecision:
    """Run the full authorization pipeline and return a :class:`AuthzDecision`.

    Safe for HTTP routes, WebSockets and background jobs alike — it never raises
    for a denial (use :meth:`AuthzDecision.raise_for_denied` when you want HTTP
    semantics). The returned decision carries a ``trace`` of every policy that
    ran. Records latency + outcome metrics for every call.
    """
    actx = build_context(
        session, ctx, product=product, feature=feature, permission=permission,
        quota=quota, quota_amount=quota_amount, request=request,
    )
    start = time.perf_counter()
    decision: Optional[AuthzDecision] = None
    try:
        decision = await _run_policies(actx, policies)
        return decision
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        metrics.observe("authorization_latency_ms", elapsed_ms)
        outcome = decision.outcome if decision else "error"
        metrics.inc("authorization_total", outcome=outcome)
        if decision is None or not decision.allowed:
            metrics.inc("authorization_denied_total", outcome=outcome)


# --------------------------------------------------------------------------- #
# FastAPI dependency guards (all route through :func:`authorize`)             #
# --------------------------------------------------------------------------- #
def require_product(product_key: str):
    """Block a route unless the caller's org may use ``product_key``."""

    async def _checker(
        ctx: OrgContext = Depends(get_current_organization),
        session: AsyncSession = Depends(get_db),
    ) -> OrgContext:
        decision = await authorize(session, ctx, product=product_key)
        decision.raise_for_denied()
        return ctx

    return _checker


def require_feature(feature_name: str):
    """Block a route unless ``feature_name`` (and its parent product) is on."""

    async def _checker(
        ctx: OrgContext = Depends(get_current_organization),
        session: AsyncSession = Depends(get_db),
    ) -> OrgContext:
        decision = await authorize(session, ctx, feature=feature_name)
        decision.raise_for_denied()
        return ctx

    return _checker


def require_permission(permission: str):
    """Block a route unless the caller's role grants ``permission``."""

    async def _checker(
        ctx: OrgContext = Depends(get_current_organization),
        session: AsyncSession = Depends(get_db),
    ) -> OrgContext:
        decision = await authorize(session, ctx, permission=permission)
        decision.raise_for_denied()
        return ctx

    return _checker


def require_authorization(
    *,
    product: Optional[str] = None,
    feature: Optional[str] = None,
    permission: Optional[str] = None,
    quota: Optional[str] = None,
):
    """Compose several checks into one dependency (all must pass)."""

    async def _checker(
        ctx: OrgContext = Depends(get_current_organization),
        session: AsyncSession = Depends(get_db),
    ) -> OrgContext:
        decision = await authorize(
            session, ctx, product=product, feature=feature,
            permission=permission, quota=quota,
        )
        decision.raise_for_denied()
        return ctx

    return _checker
