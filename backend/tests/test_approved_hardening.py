"""Approved hardening rules for rate limits, webhooks and the mail provider.

* Health probes are never rate-limited, so they keep answering during a Redis outage.
* Webhook deliveries are fail-open for rate limiting only. Other API calls fail closed in production.
* The Stripe sink acknowledges only after its work is committed; a failed commit is a server error.
* Automated tests cannot reach the live mail provider without an explicit, allowlisted opt-in.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from starlette.requests import Request


class _BrokenStore:
    def increment(self, key, ttl_seconds=None):
        raise ConnectionError("redis unreachable")


def _request(path: str, method: str = "POST") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "client": ("203.0.113.61", 0),
        }
    )


async def _ok(request):
    return SimpleNamespace(status_code=200)


@pytest.mark.asyncio
async def test_health_probes_are_not_limited_during_a_redis_outage(monkeypatch):
    from app.core.config import settings
    from app.middleware import rate_limit

    monkeypatch.setattr(rate_limit, "_cache", lambda: _BrokenStore())
    monkeypatch.setattr(settings, "environment", "production")
    for path in ("/api/health", "/api/health/ready", "/health"):
        response = await rate_limit.rate_limit_middleware(_request(path, "GET"), _ok)
        assert response.status_code == 200, path


@pytest.mark.asyncio
async def test_general_api_fails_closed_in_production_during_an_outage(monkeypatch):
    from app.core.config import settings
    from app.middleware import rate_limit

    monkeypatch.setattr(rate_limit, "_cache", lambda: _BrokenStore())
    monkeypatch.setattr(settings, "environment", "production")
    response = await rate_limit.rate_limit_middleware(
        _request("/api/agents", "GET"), _ok
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_webhooks_stay_open_for_rate_limiting_only(monkeypatch):
    from app.core.config import settings
    from app.middleware import rate_limit

    monkeypatch.setattr(rate_limit, "_cache", lambda: _BrokenStore())
    monkeypatch.setattr(settings, "environment", "production")
    for path in (
        "/api/billing/webhook",
        "/api/voice/inbound",
        "/api/channels/meta/inbound",
    ):
        response = await rate_limit.rate_limit_middleware(_request(path), _ok)
        assert response.status_code == 200, path


def test_stripe_sink_commits_before_it_acknowledges(monkeypatch):
    import asyncio

    from app.api.billing import routes as billing_routes
    from app.services import billing_service

    events: list[str] = []

    class _Session:
        async def commit(self):
            events.append("commit")

    async def _handle(session, event):
        events.append("handled")
        return "applied"

    class _Webhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            return {"id": "evt_1", "type": "invoice.paid", "data": {"object": {}}}

    import sys
    import types

    fake_stripe = types.ModuleType("stripe")
    fake_stripe.Webhook = _Webhook
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe)
    monkeypatch.setattr(billing_service, "stripe_enabled", lambda: True)
    monkeypatch.setattr(billing_service, "handle_webhook_event", _handle)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_not_a_real_secret")

    async def _body_request():
        async def receive():
            return {"type": "http.request", "body": b"{}", "more_body": False}

        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/billing/webhook",
                "headers": [(b"stripe-signature", b"t=1,v1=x")],
                "query_string": b"",
            },
            receive,
        )

    result = asyncio.run(
        billing_routes.stripe_webhook(asyncio.run(_body_request()), _Session())
    )
    assert result == {"received": True, "outcome": "applied"}
    assert events == ["handled", "commit"]


def test_stripe_commit_failure_is_not_acknowledged(monkeypatch):
    import asyncio
    import sys
    import types

    from app.api.billing import routes as billing_routes
    from app.services import billing_service

    class _Session:
        async def commit(self):
            raise RuntimeError("database unavailable")

    async def _handle(session, event):
        return "applied"

    class _Webhook:
        @staticmethod
        def construct_event(payload, sig, secret):
            return {"id": "evt_2", "type": "invoice.paid", "data": {"object": {}}}

    fake_stripe = types.ModuleType("stripe")
    fake_stripe.Webhook = _Webhook
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe)
    monkeypatch.setattr(billing_service, "stripe_enabled", lambda: True)
    monkeypatch.setattr(billing_service, "handle_webhook_event", _handle)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_not_a_real_secret")

    async def _body_request():
        async def receive():
            return {"type": "http.request", "body": b"{}", "more_body": False}

        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/billing/webhook",
                "headers": [(b"stripe-signature", b"t=1,v1=x")],
                "query_string": b"",
            },
            receive,
        )

    with pytest.raises(RuntimeError):
        asyncio.run(
            billing_routes.stripe_webhook(asyncio.run(_body_request()), _Session())
        )


def test_tests_cannot_reach_the_live_mail_provider(monkeypatch):
    import httpx

    from app.services import resend_client

    def _no_network(*args, **kwargs):
        raise AssertionError("a test opened a connection to the mail provider")

    monkeypatch.setattr(httpx, "Client", _no_network)
    monkeypatch.delenv("ORAONE_LIVE_EMAIL_TEST", raising=False)
    monkeypatch.delenv("ORAONE_LIVE_EMAIL_RECIPIENTS", raising=False)
    with pytest.raises(resend_client.LiveEmailBlockedError):
        resend_client.send(
            api_key="re_test_key_value",
            from_address="OraOne <auth@oraone.in>",
            to="person@example.com",
            subject="s",
            html="<p>x</p>",
            text="x",
            idempotency_key="k" * 64,
        )


def test_live_send_needs_opt_in_and_an_allowlisted_recipient(monkeypatch):
    from app.services import resend_client

    monkeypatch.setenv("ORAONE_LIVE_EMAIL_TEST", "1")
    monkeypatch.setenv("ORAONE_LIVE_EMAIL_RECIPIENTS", "approved@example.com")
    # Approved recipient with opt-in: allowed.
    resend_client._check_live_send_allowed("approved@example.com", None)
    # Any other recipient: refused, even with opt-in.
    with pytest.raises(resend_client.LiveEmailBlockedError):
        resend_client._check_live_send_allowed("someone@example.com", None)
    # Opt-in missing: refused, even for the approved recipient.
    monkeypatch.setenv("ORAONE_LIVE_EMAIL_TEST", "0")
    with pytest.raises(resend_client.LiveEmailBlockedError):
        resend_client._check_live_send_allowed("approved@example.com", None)
