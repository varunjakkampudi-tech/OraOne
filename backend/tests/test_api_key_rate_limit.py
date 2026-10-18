"""API key rate limits must hold across worker processes and fail closed.

Two backend instances over one shared store stand in for two Gunicorn workers.
The plan lookup and usage recording are replaced, so no database is needed.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import api_key_service, billing_service, usage_service
from app.services.cache import InProcessCacheBackend


class _BrokenStore(InProcessCacheBackend):
    def increment(self, key, ttl_seconds=None):
        raise ConnectionError("shared store unreachable")


def _key(org, key_id=None):
    return SimpleNamespace(id=key_id or uuid.uuid4(), organization_id=org)


@pytest.fixture
def plan_limit(monkeypatch):
    limit = {"rpm": 3}

    async def _subscription(_session, _org):
        return SimpleNamespace(plan=SimpleNamespace(limits={"api_rpm": limit["rpm"]}))

    async def _record(*_args, **_kwargs):
        return None

    monkeypatch.setattr(billing_service, "get_or_create_subscription", _subscription)
    monkeypatch.setattr(usage_service, "record_usage", _record)
    return limit


@pytest.fixture
def shared_store(monkeypatch):
    store = InProcessCacheBackend()
    monkeypatch.setattr(api_key_service, "_rate_cache", lambda: store)
    return store


@pytest.mark.asyncio
async def test_limit_is_enforced_per_key(plan_limit, shared_store):
    org = uuid.uuid4()
    key = _key(org)
    for _ in range(3):
        await api_key_service.enforce_rate_limit(None, key)
    with pytest.raises(HTTPException) as exc:
        await api_key_service.enforce_rate_limit(None, key)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_two_workers_share_one_ceiling(plan_limit, monkeypatch):
    org = uuid.uuid4()
    key_id = uuid.uuid4()
    # Each "worker" holds its own cache handle onto the same shared counters.
    shared = InProcessCacheBackend()
    worker_a = shared
    worker_b = shared
    monkeypatch.setattr(api_key_service, "_rate_cache", lambda: worker_a)
    for _ in range(2):
        await api_key_service.enforce_rate_limit(None, _key(org, key_id))
    monkeypatch.setattr(api_key_service, "_rate_cache", lambda: worker_b)
    await api_key_service.enforce_rate_limit(None, _key(org, key_id))
    with pytest.raises(HTTPException) as exc:
        await api_key_service.enforce_rate_limit(None, _key(org, key_id))
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_unavailable_store_fails_closed_with_503(plan_limit, monkeypatch):
    monkeypatch.setattr(api_key_service, "_rate_cache", lambda: _BrokenStore())
    with pytest.raises(HTTPException) as exc:
        await api_key_service.enforce_rate_limit(None, _key(uuid.uuid4()))
    assert exc.value.status_code == 503
    assert exc.value.headers == {"Retry-After": "5"}


@pytest.mark.asyncio
async def test_unlimited_plan_skips_the_counter(plan_limit, monkeypatch):
    plan_limit["rpm"] = -1

    def _never(*_args, **_kwargs):
        raise AssertionError("unlimited plans must not touch the counter")

    monkeypatch.setattr(api_key_service, "_rate_cache", _never)
    assert await api_key_service.enforce_rate_limit(None, _key(uuid.uuid4())) == {
        "limit": -1,
        "remaining": -1,
    }
