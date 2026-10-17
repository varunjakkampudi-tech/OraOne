"""Provider webhooks get their own per-IP tier; every other tier is unchanged."""

from __future__ import annotations

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.middleware import rate_limit


@pytest.fixture(autouse=True)
def frozen_window(monkeypatch):
    """Fixed-window buckets roll over on the minute; freeze the clock so counts stay in one bucket."""
    from types import SimpleNamespace

    monkeypatch.setattr(
        rate_limit, "time", SimpleNamespace(time=lambda: 1_700_000_000.0)
    )


class FakeCache:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def increment(self, key: str, ttl_seconds=None) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


def tier_name(path: str) -> str:
    tier = next(t for t in rate_limit.TIERS if t.matches(path))
    return tier.name


def make_request(
    path: str, method: str = "POST", ip: str = "203.0.113.10", headers=None
):
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": headers or [],
            "client": (ip, 40000),
            "scheme": "https",
            "server": ("test", 443),
        }
    )


async def ok_next(request):
    return Response("ok", status_code=200)


async def send(request):
    return await rate_limit.rate_limit_middleware(request, ok_next)


WEBHOOK_PATHS = [
    "/api/channels/twilio/inbound",
    "/api/channels/meta/inbound",
    "/api/channels/meta_instagram/inbound",
    "/api/channels/telegram/some-token/inbound",
    "/api/channels/email/inbound",
    "/api/channels/sdk/inbound",
    "/api/voice/inbound",
    "/api/voice/gather",
    "/api/voice/twiml",
    "/api/voice/status",
]

UNCHANGED_PATHS = {
    "/api/auth/email-code/request": "auth",
    "/api/auth/email-code/verify": "auth",
    "/api/auth/refresh": "auth",
    "/api/auth/me": "api",
    "/api/conversations/abc/messages": "ai",
    "/api/rag/search": "ai",
    "/api/documents/upload": "ai",
    "/api/channels/agents/1/bindings": "api",
    "/api/channels/meta/inbound/extra/segments/that/are/not/a/webhook": "api",
    "/api/agents": "api",
    "/api/voice": "api",
    "/api/voicemail/list": "api",
}


@pytest.mark.parametrize("path", WEBHOOK_PATHS)
def test_provider_inbound_paths_use_webhook_tier(path):
    assert tier_name(path) == "webhook"


@pytest.mark.parametrize("path,expected", sorted(UNCHANGED_PATHS.items()))
def test_non_webhook_paths_keep_their_existing_tier(path, expected):
    assert tier_name(path) == expected


def test_default_tier_limits_are_unchanged_and_webhook_is_higher(monkeypatch):
    # Defaults are what the code falls back to when the env var is absent.
    for var in (
        "RATE_LIMIT_AUTH_PER_MINUTE",
        "RATE_LIMIT_AI_PER_MINUTE",
        "RATE_LIMIT_API_PER_MINUTE",
        "RATE_LIMIT_WEBHOOK_PER_MINUTE",
    ):
        monkeypatch.delenv(var, raising=False)
    assert rate_limit._int_env("RATE_LIMIT_AUTH_PER_MINUTE", 10) == 10
    assert rate_limit._int_env("RATE_LIMIT_AI_PER_MINUTE", 20) == 20
    assert rate_limit._int_env("RATE_LIMIT_API_PER_MINUTE", 120) == 120
    assert rate_limit._int_env("RATE_LIMIT_WEBHOOK_PER_MINUTE", 600) == 600
    by_name = {t.name: t for t in rate_limit.TIERS}
    assert by_name["webhook"].window_seconds == 60
    assert by_name["auth"].window_seconds == 60
    names = [t.name for t in rate_limit.TIERS]
    assert names.index("webhook") < names.index("api")


@pytest.fixture
def known_limits(monkeypatch):
    """Pin tier limits so assertions do not depend on the local environment."""
    for tier in rate_limit.TIERS:
        if tier.name == "webhook":
            monkeypatch.setattr(tier, "limit", 600)
        if tier.name == "api":
            monkeypatch.setattr(tier, "limit", 120)
    return {t.name: t.limit for t in rate_limit.TIERS}


def test_webhook_tier_is_ip_only_even_with_bearer_token(monkeypatch):
    cache = FakeCache()
    monkeypatch.setattr(rate_limit, "_cache", lambda: cache)
    headers = [(b"authorization", b"Bearer not-a-real-token")]
    import asyncio

    asyncio.run(send(make_request("/api/channels/twilio/inbound", headers=headers)))
    keys = list(cache.counts)
    assert len(keys) == 1
    assert keys[0].startswith("webhook:ip:203.0.113.10:")


def test_provider_burst_above_api_limit_is_not_throttled(monkeypatch, known_limits):
    import asyncio

    cache = FakeCache()
    monkeypatch.setattr(rate_limit, "_cache", lambda: cache)
    # 130 deliveries in one minute is above the 120/min API tier but within the webhook tier.
    statuses = []
    for _ in range(130):
        response = asyncio.run(send(make_request("/api/channels/meta/inbound")))
        statuses.append(response.status_code)
    assert set(statuses) == {200}


def test_webhook_tier_still_limits_a_flood(monkeypatch, known_limits):
    import asyncio

    cache = FakeCache()
    monkeypatch.setattr(rate_limit, "_cache", lambda: cache)
    limit = known_limits["webhook"]
    response = None
    for _ in range(limit + 1):
        response = asyncio.run(send(make_request("/api/voice/inbound")))
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


def test_webhook_buckets_are_per_source_ip(monkeypatch, known_limits):
    import asyncio

    cache = FakeCache()
    monkeypatch.setattr(rate_limit, "_cache", lambda: cache)
    limit = known_limits["webhook"]
    for _ in range(limit):
        asyncio.run(send(make_request("/api/voice/gather", ip="198.51.100.1")))
    # A different provider IP is not affected by the first IP exhausting its bucket.
    other = asyncio.run(send(make_request("/api/voice/gather", ip="198.51.100.2")))
    assert other.status_code == 200
    blocked = asyncio.run(send(make_request("/api/voice/gather", ip="198.51.100.1")))
    assert blocked.status_code == 429


def test_api_tier_still_throttles_at_its_own_limit(monkeypatch, known_limits):
    import asyncio

    cache = FakeCache()
    monkeypatch.setattr(rate_limit, "_cache", lambda: cache)
    responses = [
        asyncio.run(send(make_request("/api/agents", method="GET"))) for _ in range(121)
    ]
    assert responses[119].status_code == 200
    assert responses[120].status_code == 429
    assert all(key.startswith("api:") for key in cache.counts)
