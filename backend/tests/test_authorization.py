"""Unit tests for the unified AuthorizationService, quotas and metrics.

The full pipeline is exercised without a database by stubbing the two DB-backed
stages (``_subscription_state`` and the entitlement snapshot), so every policy
branch is covered deterministically and fast.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.services import authorization as azm
from app.services import cache as cachemod
from app.services import metrics as m
from app.services import quotas as q
from app.services.authorization import AuthzDecision, AuthzOutcome, authorize
from fastapi import HTTPException

#: Capture the real subscription resolver before any fixture stubs it.
_ORIG_SUB_STATE = azm._subscription_state


def _ctx(role: str = "owner"):
    return SimpleNamespace(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        cognito_sub="sub-123",
        membership_role=role,
    )


def _snapshot(**over):
    base = {
        "products": {"ai_platform": True, "voice_platform": True},
        "maintenance": {"ai_platform": False, "voice_platform": False},
        "statuses": {"ai_platform": "ga", "voice_platform": "ga"},
        "features": {"voice_agents": True, "analytics": True, "crm": False},
    }
    base.update(over)
    return base


@pytest.fixture(autouse=True)
def _stub_stages(monkeypatch):
    """Stub the two DB-backed stages with in-memory defaults; tests override."""
    async def _ok_sub(session, org_id):
        return {"status": "active", "plan_code": "business", "plan_limits": None,
                "blocked": False, "outcome": AuthzOutcome.ALLOW, "reason": None}

    async def _snap(session, org_id):
        return _snapshot()

    monkeypatch.setattr(azm, "_subscription_state", _ok_sub)
    monkeypatch.setattr(azm.ent, "get_cached_snapshot", _snap)
    m.reset()
    yield


# --------------------------------------------------------------------------- #
# Decision object                                                             #
# --------------------------------------------------------------------------- #
def test_outcome_status_mapping():
    assert azm.OUTCOME_STATUS[AuthzOutcome.ALLOW] == 200
    assert azm.OUTCOME_STATUS[AuthzOutcome.DENY] == 403
    assert azm.OUTCOME_STATUS[AuthzOutcome.MAINTENANCE] == 503
    assert azm.OUTCOME_STATUS[AuthzOutcome.COMING_SOON] == 403
    assert azm.OUTCOME_STATUS[AuthzOutcome.TRIAL_EXPIRED] == 402
    assert azm.OUTCOME_STATUS[AuthzOutcome.SUBSCRIPTION_EXPIRED] == 402
    assert azm.OUTCOME_STATUS[AuthzOutcome.USAGE_EXCEEDED] == 429
    assert azm.OUTCOME_STATUS[AuthzOutcome.UNAUTHENTICATED] == 401


def test_raise_for_denied_allow_is_noop():
    AuthzDecision(True, AuthzOutcome.ALLOW, 200).raise_for_denied()  # no raise


def test_raise_for_denied_raises_matching_status():
    d = AuthzDecision(False, AuthzOutcome.MAINTENANCE, 503, reason="down")
    with pytest.raises(HTTPException) as ei:
        d.raise_for_denied()
    assert ei.value.status_code == 503
    assert ei.value.detail == "down"


# --------------------------------------------------------------------------- #
# Pipeline                                                                    #
# --------------------------------------------------------------------------- #
async def test_unauthenticated_denied():
    d = await authorize(None, None, product="voice_platform")
    assert d.allowed is False
    assert d.outcome == AuthzOutcome.UNAUTHENTICATED
    assert d.http_status == 401


async def test_product_allowed():
    d = await authorize(None, _ctx(), product="voice_platform")
    assert d.allowed is True
    assert d.outcome == AuthzOutcome.ALLOW


async def test_product_denied_when_not_entitled(monkeypatch):
    async def _snap(session, org_id):
        return _snapshot(products={"ai_platform": True, "voice_platform": False})
    monkeypatch.setattr(azm.ent, "get_cached_snapshot", _snap)
    d = await authorize(None, _ctx(), product="voice_platform")
    assert d.allowed is False
    assert d.outcome == AuthzOutcome.DENY
    assert d.http_status == 403


async def test_product_maintenance(monkeypatch):
    async def _snap(session, org_id):
        return _snapshot(
            products={"voice_platform": False},
            maintenance={"voice_platform": True},
        )
    monkeypatch.setattr(azm.ent, "get_cached_snapshot", _snap)
    d = await authorize(None, _ctx(), product="voice_platform")
    assert d.outcome == AuthzOutcome.MAINTENANCE
    assert d.http_status == 503


async def test_product_coming_soon(monkeypatch):
    async def _snap(session, org_id):
        return _snapshot(
            products={"voice_platform": False},
            statuses={"voice_platform": "coming_soon"},
        )
    monkeypatch.setattr(azm.ent, "get_cached_snapshot", _snap)
    d = await authorize(None, _ctx(), product="voice_platform")
    assert d.outcome == AuthzOutcome.COMING_SOON
    assert d.http_status == 403


async def test_unknown_product_is_fail_closed():
    d = await authorize(None, _ctx(), product="nonexistent_product")
    assert d.allowed is False
    assert d.outcome == AuthzOutcome.DENY


async def test_feature_enabled_allowed():
    d = await authorize(None, _ctx(), feature="voice_agents")
    assert d.allowed is True


async def test_feature_disabled_denied():
    d = await authorize(None, _ctx(), feature="crm")
    assert d.allowed is False
    assert d.outcome == AuthzOutcome.DENY


async def test_permission_granted_for_owner():
    d = await authorize(None, _ctx("owner"), permission="agents.write")
    assert d.allowed is True


async def test_permission_denied_for_viewer():
    d = await authorize(None, _ctx("viewer"), permission="agents.write")
    assert d.allowed is False
    assert d.outcome == AuthzOutcome.DENY


# --------------------------------------------------------------------------- #
# Subscription stage (enforcement gated by env switch)                        #
# --------------------------------------------------------------------------- #
async def test_subscription_blocked_not_enforced_by_default(monkeypatch):
    async def _blocked_sub(session, org_id):
        return {"status": "canceled", "plan_code": "free", "plan_limits": None,
                "blocked": True, "outcome": AuthzOutcome.SUBSCRIPTION_EXPIRED,
                "reason": "inactive"}
    monkeypatch.setattr(azm, "_subscription_state", _blocked_sub)
    # Default: enforcement OFF -> still allowed.
    d = await authorize(None, _ctx(), product="voice_platform")
    assert d.allowed is True


async def test_subscription_blocked_denies_when_enforced(monkeypatch):
    async def _blocked_sub(session, org_id):
        return {"status": "canceled", "plan_code": "free", "plan_limits": None,
                "blocked": True, "outcome": AuthzOutcome.SUBSCRIPTION_EXPIRED,
                "reason": "inactive"}
    monkeypatch.setattr(azm, "_subscription_state", _blocked_sub)
    monkeypatch.setattr(azm, "ENFORCE_SUBSCRIPTION", True)
    d = await authorize(None, _ctx(), product="voice_platform")
    assert d.allowed is False
    assert d.outcome == AuthzOutcome.SUBSCRIPTION_EXPIRED
    assert d.http_status == 402


# --------------------------------------------------------------------------- #
# Quota stage (enforcement gated by env switch)                               #
# --------------------------------------------------------------------------- #
async def test_quota_exceeded_not_enforced_by_default(monkeypatch):
    async def _exceeded(session, org_id, key, **kw):
        return q.QuotaDecision(False, key, 10, 10, 0, "exceeded")
    monkeypatch.setattr(azm.quotas, "check_quota", _exceeded)
    d = await authorize(None, _ctx(), quota="ai_requests")
    assert d.allowed is True  # designed, not enforced


async def test_quota_exceeded_denies_when_enforced(monkeypatch):
    async def _exceeded(session, org_id, key, **kw):
        return q.QuotaDecision(False, key, 10, 10, 0, "exceeded")
    monkeypatch.setattr(azm.quotas, "check_quota", _exceeded)
    monkeypatch.setattr(azm, "ENFORCE_QUOTAS", True)
    d = await authorize(None, _ctx(), quota="ai_requests")
    assert d.allowed is False
    assert d.outcome == AuthzOutcome.USAGE_EXCEEDED
    assert d.http_status == 429


# --------------------------------------------------------------------------- #
# Metrics side effects                                                        #
# --------------------------------------------------------------------------- #
async def test_authorize_records_metrics():
    m.reset()
    await authorize(None, _ctx(), product="voice_platform")
    snap = m.snapshot()
    assert "authorization_total" in snap["counters"]
    assert "authorization_latency_ms" in snap["histograms"]
    assert snap["histograms"]["authorization_latency_ms"]["count"] == 1


async def test_denied_increments_denied_counter():
    m.reset()
    await authorize(None, None, product="voice_platform")  # unauthenticated
    snap = m.snapshot()
    assert "authorization_denied_total" in snap["counters"]


# --------------------------------------------------------------------------- #
# Quota module                                                                #
# --------------------------------------------------------------------------- #
def test_resolve_limit_uses_plan_default():
    assert q.resolve_limit(q.QuotaKey.USERS, plan_code="free") == 2
    assert q.resolve_limit(q.QuotaKey.AI_REQUESTS, plan_code="enterprise") == q.UNLIMITED


def test_resolve_limit_override_wins():
    assert q.resolve_limit(q.QuotaKey.USERS, plan_code="free", plan_limits={"users": 50}) == 50


async def test_check_quota_unlimited_allows():
    d = await q.check_quota(None, uuid.uuid4(), q.QuotaKey.USERS, plan_code="enterprise")
    assert d.allowed is True
    assert d.limit == q.UNLIMITED


async def test_check_quota_unmetered_allows():
    # No usage source wired up yet -> "unmetered" but allowed.
    d = await q.check_quota(None, uuid.uuid4(), q.QuotaKey.USERS, plan_code="free")
    assert d.allowed is True
    assert d.outcome == "unmetered"


# --------------------------------------------------------------------------- #
# Metrics registry                                                            #
# --------------------------------------------------------------------------- #
def test_metrics_counter_and_labels():
    m.reset()
    m.inc("things_total")
    m.inc("things_total")
    m.inc("things_total", outcome="deny")
    snap = m.snapshot()
    # Mixed labelled + unlabelled series -> list form.
    assert isinstance(snap["counters"]["things_total"], list)


def test_metrics_histogram_and_prometheus_text():
    m.reset()
    m.observe("lat_ms", 3)
    m.observe("lat_ms", 40)
    snap = m.snapshot()
    assert snap["histograms"]["lat_ms"]["count"] == 2
    assert snap["histograms"]["lat_ms"]["sum"] == 43
    text = m.prometheus_text()
    assert "lat_ms_bucket" in text
    assert "lat_ms_count 2" in text


# --------------------------------------------------------------------------- #
# Policy engine + DecisionTrace                                               #
# --------------------------------------------------------------------------- #
async def test_decision_carries_full_trace():
    d = await authorize(None, _ctx(), product="voice_platform", permission="agents.write")
    assert d.allowed is True
    names = [t["policy"] for t in d.trace]
    assert names[0] == "authentication"
    assert "subscription" in names
    assert "entitlement" in names
    assert "permission" in names


async def test_trace_stops_at_first_denial(monkeypatch):
    async def _snap(session, org_id):
        return _snapshot(products={"ai_platform": True, "voice_platform": False})
    monkeypatch.setattr(azm.ent, "get_cached_snapshot", _snap)
    d = await authorize(None, _ctx(), product="voice_platform", permission="agents.write")
    assert d.allowed is False
    last = d.trace[-1]
    assert last["policy"] == "entitlement"
    assert last["result"] == "deny"
    # Permission policy is never reached once entitlement denies.
    assert all(t["policy"] != "permission" for t in d.trace)


async def test_trace_records_skips_for_inapplicable_policies():
    d = await authorize(None, _ctx(), permission="agents.write")
    by_name = {t["policy"]: t for t in d.trace}
    assert by_name["maintenance"]["result"] == "skip"
    assert by_name["entitlement"]["result"] == "skip"
    assert by_name["permission"]["result"] == "allow"


async def test_custom_policy_chain_is_pluggable():
    # A single-policy chain that always allows -> allowed regardless of intent.
    class _AlwaysAllow(azm.Policy):
        name = "always_allow"

        async def evaluate(self, actx):
            return azm.PolicyEval(azm.PolicyResult.ALLOW)

    d = await authorize(None, None, product="voice_platform", policies=(_AlwaysAllow(),))
    assert d.allowed is True
    assert d.trace == [{"policy": "always_allow", "result": "allow"}]


# --------------------------------------------------------------------------- #
# AuthorizationContext                                                        #
# --------------------------------------------------------------------------- #
def test_authorization_context_identity():
    actx = azm.build_context(None, _ctx("admin"), product="voice_platform")
    assert actx.authenticated is True
    assert actx.role == "admin"
    assert actx.roles == ["admin"]
    assert "agents.write" in actx.permissions


def test_authorization_context_unauthenticated():
    actx = azm.build_context(None, None)
    assert actx.authenticated is False
    assert actx.organization_id is None
    assert actx.permissions == []


async def test_context_memoizes_snapshot(monkeypatch):
    calls = {"n": 0}

    async def _snap(session, org_id):
        calls["n"] += 1
        return _snapshot()

    monkeypatch.setattr(azm.ent, "get_cached_snapshot", _snap)
    actx = azm.build_context(None, _ctx(), product="voice_platform", feature="voice_agents")
    await actx.snapshot()
    await actx.snapshot()
    assert calls["n"] == 1  # resolved once, then memoised


# --------------------------------------------------------------------------- #
# Default Free plan resolution (no special-case bypass)                       #
# --------------------------------------------------------------------------- #
class _FakeSession:
    def __init__(self, sub=None):
        self._sub = sub

    async def scalar(self, *a, **k):
        return self._sub


async def test_no_subscription_resolves_default_free_plan(monkeypatch):
    # Restore the real implementation (the autouse fixture stubs it).
    monkeypatch.setattr(azm, "_subscription_state", _ORIG_SUB_STATE)
    state = await azm._subscription_state(_FakeSession(None), uuid.uuid4())
    assert state["plan_code"] == q._DEFAULT_PLAN == "free"
    assert state["blocked"] is False
    assert state["plan_source"] == "default_free"


async def test_subscription_lookup_error_falls_back_to_free(monkeypatch):
    monkeypatch.setattr(azm, "_subscription_state", _ORIG_SUB_STATE)

    class _BoomSession:
        async def scalar(self, *a, **k):
            raise RuntimeError("no table")

    state = await azm._subscription_state(_BoomSession(), uuid.uuid4())
    assert state["plan_code"] == "free"
    assert state["blocked"] is False


# --------------------------------------------------------------------------- #
# Metrics backend abstraction                                                 #
# --------------------------------------------------------------------------- #
def test_metrics_default_backend_is_inprocess():
    assert isinstance(m.get_backend(), m.InProcessBackend)


def test_metrics_use_backend_swaps_target():
    original = m.get_backend()
    try:
        b = m.InProcessBackend()
        m.use_backend(b)
        m.inc("swap_total")
        assert b.snapshot()["counters"]["swap_total"] == 1
    finally:
        m.use_backend(original)


def test_prometheus_backend_optional_dependency():
    try:
        import prometheus_client  # noqa: F401
        assert m.PrometheusBackend().name == "prometheus"
    except ImportError:
        with pytest.raises(RuntimeError):
            m.PrometheusBackend()


def test_otel_backend_optional_dependency():
    try:
        from opentelemetry import metrics as _otel  # noqa: F401
        assert m.OpenTelemetryBackend().name == "otel"
    except ImportError:
        with pytest.raises(RuntimeError):
            m.OpenTelemetryBackend()


# --------------------------------------------------------------------------- #
# Cache backend abstraction                                                   #
# --------------------------------------------------------------------------- #
def test_inprocess_cache_backend_roundtrip():
    b = cachemod.InProcessCacheBackend()
    assert b.native_ttl is False
    b.set("k", {"v": 1})
    assert b.get("k") == {"v": 1}
    b.delete("k")
    assert b.get("k") is None
    b.set("a", 1)
    b.set("b", 2)
    b.clear()
    assert b.get("a") is None and b.get("b") is None


def test_get_cache_backend_default_inprocess(monkeypatch):
    monkeypatch.delenv("ENTITLEMENTS_CACHE_BACKEND", raising=False)
    assert isinstance(cachemod.get_cache_backend(), cachemod.InProcessCacheBackend)


def test_get_cache_backend_redis_without_url_falls_back(monkeypatch):
    monkeypatch.setenv("ENTITLEMENTS_CACHE_BACKEND", "redis")
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert isinstance(cachemod.get_cache_backend(), cachemod.InProcessCacheBackend)
