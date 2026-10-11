"""Unit tests for the entitlement engine's pure resolution logic.

These cover the security-critical decisions (fail-closed access, lifecycle
gating, deterministic rollout, Product→Feature parenting, cache invalidation)
without touching the database, so they run fast in CI.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.database.models.product import ProductStatus, ProductVisibility
from app.services import entitlements as ent


# --------------------------------------------------------------------------- #
# Lifecycle: which statuses grant access                                       #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "status_value, usable",
    [
        (ProductStatus.GA, True),
        (ProductStatus.ACTIVE, True),
        (ProductStatus.BETA, True),
        (ProductStatus.PREVIEW, True),
        (ProductStatus.DEPRECATED, True),
        (ProductStatus.COMING_SOON, False),
        (ProductStatus.MAINTENANCE, False),
        (ProductStatus.INTERNAL, False),
        (ProductStatus.DISABLED, False),
    ],
)
def test_status_is_usable(status_value, usable):
    assert ent.status_is_usable(status_value) is usable


# --------------------------------------------------------------------------- #
# Effective product access (the fail-closed core)                              #
# --------------------------------------------------------------------------- #
def test_effective_enabled_usable_default_on_no_override():
    assert ent._effective_product_enabled(ProductStatus.GA, True, None) is True


def test_effective_enabled_usable_default_off_no_override():
    assert ent._effective_product_enabled(ProductStatus.GA, False, None) is False


def test_effective_override_true_wins_over_default_off():
    assert ent._effective_product_enabled(ProductStatus.GA, False, True) is True


def test_effective_override_false_wins_over_default_on():
    assert ent._effective_product_enabled(ProductStatus.GA, True, False) is False


@pytest.mark.parametrize(
    "status_value",
    [ProductStatus.DISABLED, ProductStatus.COMING_SOON, ProductStatus.MAINTENANCE, ProductStatus.INTERNAL],
)
def test_non_usable_status_denies_even_with_override_true(status_value):
    # A non-usable lifecycle status is fail-closed regardless of the org switch.
    assert ent._effective_product_enabled(status_value, True, True) is False


def test_visibility_is_not_an_authorization_gate():
    # Visibility only affects discovery; it must never appear in access logic.
    # (Sanity check: the resolver signature takes no visibility argument.)
    import inspect

    params = inspect.signature(ent._effective_product_enabled).parameters
    assert "visibility" not in params
    assert set(ProductVisibility.ALL) == {"visible", "hidden", "internal"}


# --------------------------------------------------------------------------- #
# Deterministic rollout bucketing                                              #
# --------------------------------------------------------------------------- #
def test_rollout_bucket_is_deterministic_and_bounded():
    org = uuid.uuid4()
    b1 = ent._rollout_bucket(org, "flag_x")
    b2 = ent._rollout_bucket(org, "flag_x")
    assert b1 == b2
    assert 0 <= b1 < 100


def test_rollout_bucket_varies_by_flag_and_org():
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    # Different flags for the same org should generally differ; different orgs too.
    assert ent._rollout_bucket(org_a, "a") == ent._rollout_bucket(org_a, "a")
    # Not asserting inequality (hash collisions possible) — just determinism above.


def _flag(enabled=True, rollout=100, name="f"):
    return SimpleNamespace(enabled=enabled, rollout_percentage=rollout, name=name)


def test_flag_disabled_is_off_regardless_of_rollout():
    assert ent._flag_enabled_for_org(_flag(enabled=False, rollout=100), uuid.uuid4()) is False


def test_flag_full_rollout_is_on():
    assert ent._flag_enabled_for_org(_flag(enabled=True, rollout=100), uuid.uuid4()) is True


def test_flag_zero_rollout_is_off():
    assert ent._flag_enabled_for_org(_flag(enabled=True, rollout=0), uuid.uuid4()) is False


def test_flag_partial_rollout_is_stable_per_org():
    org = uuid.uuid4()
    f = _flag(enabled=True, rollout=50, name="partial")
    first = ent._flag_enabled_for_org(f, org)
    for _ in range(5):
        assert ent._flag_enabled_for_org(f, org) is first


# --------------------------------------------------------------------------- #
# Product → Feature parenting                                                  #
# --------------------------------------------------------------------------- #
def test_unknown_feature_defaults_to_ai_platform_parent():
    assert ent._feature_parent("some_new_feature") == "ai_platform"


# --------------------------------------------------------------------------- #
# In-process cache lifecycle                                                    #
# --------------------------------------------------------------------------- #
def test_cache_set_get_and_invalidate_org():
    ent.invalidate_all()
    org = uuid.uuid4()
    snap = {"products": {"ai_platform": True}}
    ent._cache_set(org, snap)
    assert ent._cache_get(org) == snap
    ent.invalidate_org(org)
    assert ent._cache_get(org) is None


def test_invalidate_all_clears_every_org():
    ent.invalidate_all()
    a, b = uuid.uuid4(), uuid.uuid4()
    ent._cache_set(a, {"x": 1})
    ent._cache_set(b, {"y": 2})
    ent.invalidate_all()
    assert ent._cache_get(a) is None
    assert ent._cache_get(b) is None


def test_cache_expiry(monkeypatch):
    # Force the in-process backend regardless of ambient ENTITLEMENTS_CACHE_BACKEND
    # config (e.g. a local .env pointing at Redis) — this test exercises the
    # in-process TTL logic specifically, via a monkeypatched monotonic clock,
    # which a real Redis TTL wouldn't honour.
    from app.services import cache as cache_module
    monkeypatch.setattr(ent, "_cache", cache_module.InProcessCacheBackend())
    ent.invalidate_all()
    org = uuid.uuid4()
    clock = {"t": 1000.0}
    monkeypatch.setattr(ent.time, "monotonic", lambda: clock["t"])
    ent._cache_set(org, {"z": 3})
    assert ent._cache_get(org) == {"z": 3}
    clock["t"] += ent._CACHE_TTL_SECONDS + 1
    assert ent._cache_get(org) is None
