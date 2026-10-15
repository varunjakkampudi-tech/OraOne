"""API-key quotas must be shared across workers and fail closed."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import api_key_service


class _CounterCache:
    def __init__(self):
        self.counts = {}
        self.keys = []

    def increment(self, key, ttl_seconds=None):
        self.keys.append((key, ttl_seconds))
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


@pytest.fixture
def quota(monkeypatch):
    recorded = []
    settings = {"rpm": 2}
    cache = _CounterCache()

    async def fake_subscription(_session, _org_id):
        return SimpleNamespace(
            plan=SimpleNamespace(limits={"api_rpm": settings["rpm"]})
        )

    async def fake_record(_session, org_id, item, quantity):
        recorded.append((org_id, item, quantity))

    monkeypatch.setattr(
        api_key_service.billing_service,
        "get_or_create_subscription",
        fake_subscription,
    )
    monkeypatch.setattr(api_key_service.usage_service, "record_usage", fake_record)
    monkeypatch.setattr(api_key_service, "_quota_cache", lambda: cache)
    return SimpleNamespace(
        key=SimpleNamespace(id=uuid4(), organization_id=uuid4()),
        settings=settings,
        cache=cache,
        recorded=recorded,
    )


@pytest.mark.asyncio
async def test_quota_shared_counter_and_denied_requests_not_charged(quota):
    first = await api_key_service.enforce_rate_limit(None, quota.key)
    second = await api_key_service.enforce_rate_limit(None, quota.key)
    assert first == {"limit": 2, "remaining": 1}
    assert second == {"limit": 2, "remaining": 0}

    with pytest.raises(HTTPException) as exc:
        await api_key_service.enforce_rate_limit(None, quota.key)
    assert exc.value.status_code == 429
    assert len(quota.recorded) == 2
    assert len({key for key, ttl in quota.cache.keys}) == 1
    assert all(ttl == 120 for key, ttl in quota.cache.keys)


@pytest.mark.asyncio
async def test_cache_failure_rejects_unmetered_api_request(quota, monkeypatch):
    class _BrokenCache:
        def increment(self, key, ttl_seconds=None):
            raise ConnectionError("redis is unavailable")

    monkeypatch.setattr(api_key_service, "_quota_cache", lambda: _BrokenCache())
    with pytest.raises(HTTPException) as exc:
        await api_key_service.enforce_rate_limit(None, quota.key)
    assert exc.value.status_code == 503
    assert len(quota.recorded) == 0


@pytest.mark.asyncio
async def test_free_plan_denies_api_before_usage_recording(quota):
    quota.settings["rpm"] = 0
    with pytest.raises(HTTPException) as exc:
        await api_key_service.enforce_rate_limit(None, quota.key)
    assert exc.value.status_code == 402
    assert len(quota.recorded) == 0
    assert len(quota.cache.keys) == 0


@pytest.mark.asyncio
async def test_unlimited_plan_still_records_accepted_usage(quota):
    quota.settings["rpm"] = -1
    result = await api_key_service.enforce_rate_limit(None, quota.key)
    assert result == {"limit": -1, "remaining": -1}
    assert len(quota.recorded) == 1
    assert len(quota.cache.keys) == 0
