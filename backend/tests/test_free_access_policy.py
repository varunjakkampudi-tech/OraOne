"""Regression tests for OraOne's free-access and real-usage policy."""

from app.services import billing_service, usage_service


def test_paid_billing_is_disabled_by_default():
    assert billing_service.FREE_ACCESS_ONLY is True
    assert billing_service.stripe_enabled() is False


def test_free_plan_has_real_token_meter():
    free = next(
        plan for plan in billing_service.PLAN_CATALOGUE if plan["code"].value == "free"
    )
    assert free["price_cents"] == 0
    assert free["price_cents_yearly"] == 0
    assert free["limits"]["ai_tokens_per_month"] == 250000
    assert usage_service.METERED_METRICS["ai_tokens"]["granularity"] == "month"
