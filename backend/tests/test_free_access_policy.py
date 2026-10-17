"""Regression tests for OraOne's free-access and real-usage policy."""

import importlib

import pytest

from app.services import billing_service, usage_service


@pytest.fixture
def default_free_access_billing(monkeypatch):
    # FREE_ACCESS_ONLY is read once at import time, so set the variable this
    # test depends on and reload the module. A developer's .env or exported
    # value must not change the result.
    monkeypatch.setenv("ORAONE_FREE_ACCESS_ONLY", "true")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    importlib.reload(billing_service)
    try:
        yield billing_service
    finally:
        monkeypatch.undo()
        importlib.reload(billing_service)


def test_paid_billing_is_disabled_by_default(default_free_access_billing):
    billing = default_free_access_billing
    assert billing.FREE_ACCESS_ONLY is True
    assert billing.stripe_enabled() is False


def test_free_plan_has_real_token_meter():
    free = next(
        plan for plan in billing_service.PLAN_CATALOGUE if plan["code"].value == "free"
    )
    assert free["price_cents"] == 0
    assert free["price_cents_yearly"] == 0
    assert free["limits"]["ai_tokens_per_month"] == 250000
    assert usage_service.METERED_METRICS["ai_tokens"]["granularity"] == "month"
