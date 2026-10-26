"""Sign-in limits, single use and fail-closed behaviour across two backend instances.

Each test uses two separate Redis clients with the same key prefix. They stand in for two
backend processes behind one load balancer. Requests alternate between the two clients, so
any limit that is only enforced per process fails the test.

These tests need a real Redis. They are skipped unless ``REDIS_URL`` is set, for example
``REDIS_URL=redis://127.0.0.1:6379/15`` on a disposable test instance. Each test uses its
own key prefix and removes it afterwards.
"""

from __future__ import annotations

import asyncio
import itertools
import os
import threading
import uuid
from types import SimpleNamespace

import pytest
from starlette.requests import Request

REDIS_URL = os.environ.get("REDIS_URL", "").strip()
pytestmark = pytest.mark.skipif(
    not REDIS_URL,
    reason="REDIS_URL not set; cross-instance limits are verified against a real Redis only.",
)


def _instance(prefix: str):
    from app.services.cache import RedisCacheBackend

    return RedisCacheBackend(REDIS_URL, prefix=prefix)


@pytest.fixture
def two_instances():
    prefix = f"oraone:test-{uuid.uuid4().hex}:"
    first = _instance(prefix)
    second = _instance(prefix)
    yield first, second
    first.clear()


@pytest.fixture
def alternate_instances(monkeypatch, two_instances):
    """Make every shared-cache lookup in the auth service alternate between instances."""
    from app.services import auth_service

    first, second = two_instances
    turn = itertools.cycle([first, second])
    monkeypatch.setattr(auth_service, "get_shared_cache", lambda namespace: next(turn))
    return first, second


class _NoRows:
    async def get_by_email(self, _email):
        return None


class _ActiveUser:
    auth_subject = "sub-multi"
    email = "multi@example.com"
    full_name = "Multi Instance"
    password_hash = "unused"
    is_email_verified = False
    last_login_at = None

    class status:  # noqa: N801 - mimics the enum's .value access
        value = "active"


class _Session:
    async def commit(self):
        return None


def test_counters_are_shared_between_instances(two_instances):
    first, second = two_instances
    assert first.increment("counter", ttl_seconds=60) == 1
    assert second.increment("counter", ttl_seconds=60) == 2
    assert first.increment("counter") == 3


def test_cooldown_can_be_taken_by_only_one_instance(two_instances):
    first, second = two_instances
    assert first.set_if_not_exists("cooldown", 1, ttl_seconds=60) is True
    assert second.set_if_not_exists("cooldown", 1, ttl_seconds=60) is False


def test_send_limit_holds_across_instances(alternate_instances, monkeypatch):
    from app.schemas.auth import EmailCodeRequest
    from app.services import auth_service, email_service

    sent: list[str] = []
    monkeypatch.setattr(
        email_service,
        "send_login_otp",
        lambda to, *, code, expires_in="5 minutes": sent.append(to) or True,
    )
    monkeypatch.setattr(auth_service, "UserRepository", lambda session: _NoRows())
    email = f"limit-{uuid.uuid4().hex[:8]}@example.com"

    for _ in range(auth_service.MAX_CODE_SENDS + 2):
        # Clear the cooldown so only the send limit is being tested.
        first, second = alternate_instances
        first.delete(auth_service._cooldown_key(email))
        second.delete(auth_service._cooldown_key(email))
        assert (
            asyncio.run(
                auth_service.request_email_code(
                    _Session(), EmailCodeRequest(email=email)
                )
            )
            is None
        )

    assert len(sent) == auth_service.MAX_CODE_SENDS


def test_wrong_code_attempts_are_counted_across_instances(
    alternate_instances, monkeypatch
):
    from fastapi import HTTPException

    from app.core.config import settings
    from app.schemas.auth import VerifyLoginOtpRequest
    from app.services import auth_service

    monkeypatch.setattr(settings, "jwt_secret_key", "s" * 64)
    email = f"attempts-{uuid.uuid4().hex[:8]}@example.com"
    first, _second = alternate_instances
    first.set(
        auth_service._code_key(email),
        {"digest": auth_service._digest(email, "111111")},
        ttl_seconds=300,
    )
    statuses = []
    for _ in range(auth_service.MAX_CODE_ATTEMPTS + 1):
        try:
            asyncio.run(
                auth_service.verify_email_code(
                    _Session(), VerifyLoginOtpRequest(email=email, code="000000")
                )
            )
        except HTTPException as exc:
            statuses.append(exc.status_code)
    assert (
        statuses[: auth_service.MAX_CODE_ATTEMPTS]
        == [400] * auth_service.MAX_CODE_ATTEMPTS
    )
    assert statuses[-1] == 429


def _race(alternate_instances, monkeypatch, *, parties: int):
    from fastapi import HTTPException

    from app.core.config import settings
    from app.schemas.auth import VerifyLoginOtpRequest
    from app.services import auth_service

    monkeypatch.setattr(settings, "jwt_secret_key", "s" * 64)
    email = f"race-{uuid.uuid4().hex[:8]}@example.com"
    first, _second = alternate_instances
    code = "482913"
    first.set(
        auth_service._code_key(email),
        {"digest": auth_service._digest(email, code)},
        ttl_seconds=300,
    )
    users = type("Users", (), {"get_by_email": lambda self, e: _async(_ActiveUser())})
    monkeypatch.setattr(auth_service, "UserRepository", lambda session: users())

    barrier = threading.Barrier(parties)
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt():
        barrier.wait()
        try:
            asyncio.run(
                auth_service.verify_email_code(
                    _Session(), VerifyLoginOtpRequest(email=email, code=code)
                )
            )
            result = "ok"
        except HTTPException as exc:
            result = str(exc.status_code)
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt) for _ in range(parties)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return outcomes


def test_exactly_one_verification_succeeds_under_concurrency(
    alternate_instances, monkeypatch
):
    from app.services import auth_service

    # Three simultaneous submissions (a double click plus one retry) fit the attempt budget.
    outcomes = _race(alternate_instances, monkeypatch, parties=3)
    assert outcomes.count("ok") == 1, outcomes
    assert outcomes.count("400") == 2, outcomes
    assert auth_service.MAX_CODE_ATTEMPTS >= 3


def test_a_burst_beyond_the_attempt_budget_never_yields_two_sessions(
    alternate_instances, monkeypatch
):
    from app.services import auth_service

    # Twelve simultaneous submissions exceed the budget. Some are refused by the limit,
    # and the code may be lost to the lockout. What must never happen is two sessions.
    outcomes = _race(alternate_instances, monkeypatch, parties=12)
    assert outcomes.count("ok") <= 1, outcomes
    assert auth_service.MAX_CODE_ATTEMPTS == 5


def test_consume_has_exactly_one_winner_across_instances(two_instances):
    first, second = two_instances
    first.set("single-use", {"digest": "x"}, ttl_seconds=60)
    barrier = threading.Barrier(24)
    winners: list[object] = []
    lock = threading.Lock()

    def take(instance):
        barrier.wait()
        value = instance.consume("single-use")
        if value is not None:
            with lock:
                winners.append(value)

    threads = [
        threading.Thread(target=take, args=(first if i % 2 == 0 else second,))
        for i in range(24)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    assert len(winners) == 1


@pytest.mark.asyncio
async def test_redis_outage_fails_closed_in_production(two_instances, monkeypatch):
    from app.core.config import settings
    from app.middleware import rate_limit

    first, _second = two_instances

    class _Down:
        def __getattr__(self, name):
            def _raise(*_a, **_k):
                import redis

                raise redis.ConnectionError("redis unreachable")

            return _raise

    healthy = first._redis
    first._redis = _Down()  # the outage starts after the client was created
    monkeypatch.setattr(rate_limit, "_cache", lambda: first)
    monkeypatch.setattr(settings, "environment", "production")

    async def _ok(request):
        return SimpleNamespace(status_code=200)

    def _req(path):
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": path,
                "headers": [],
                "query_string": b"",
                "client": ("203.0.113.44", 0),
            }
        )

    try:
        for path in ("/api/auth/refresh", "/api/rag/query", "/api/agents"):
            response = await rate_limit.rate_limit_middleware(_req(path), _ok)
            assert response.status_code == 503, path
    finally:
        first._redis = healthy  # let the fixture clean up its keys


async def _async(value):
    return value
