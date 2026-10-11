"""Concurrent idempotency — two simultaneous requests with the same
``Idempotency-Key`` must not both execute the underlying mutation.

This is the one behavior `test_redis_failure.py` doesn't cover (that file
is about the cache being *unreachable*; this is about two callers racing
against a *healthy* cache at the same instant). Uses the real
``InProcessCacheBackend`` (deterministic, no Redis needed) — its
``set_if_not_exists`` has no internal ``await``, so two asyncio tasks
racing on it resolve deterministically to exactly one winner, same as
Redis's atomic ``SET NX`` would under a real race.
"""
from __future__ import annotations

import asyncio

import pytest

from app.middleware.idempotency import idempotency_middleware
from app.services.cache import InProcessCacheBackend


def _fake_request(*, idem_key="race-key-1"):
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/agents",
        "headers": [(b"authorization", b"Bearer faketoken"), (b"idempotency-key", idem_key.encode())],
        "query_string": b"",
        "client": ("127.0.0.1", 0),
    }
    return Request(scope)


class _StreamedResponse:
    """Mimics what Starlette's BaseHTTPMiddleware actually hands `call_next`
    callers — a response whose body is exposed via `body_iterator`, not a
    plain `JSONResponse.body` attribute."""

    def __init__(self, status_code: int, content: dict):
        import json as _json
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self.media_type = "application/json"
        self._body = _json.dumps(content).encode()

    @property
    async def body_iterator(self):
        yield self._body


@pytest.mark.asyncio
async def test_concurrent_requests_with_same_key_execute_once(monkeypatch):
    from app.middleware import idempotency as idem_module

    shared = InProcessCacheBackend()
    monkeypatch.setattr(idem_module, "_cache", lambda: shared)

    execution_count = 0

    async def _slow_call_next(request):
        # Wide enough window that both tasks are guaranteed to have started
        # (and the first to have acquired the lock) before either finishes —
        # simulates a real mutation that takes non-trivial time.
        nonlocal execution_count
        execution_count += 1
        await asyncio.sleep(0.05)
        return _StreamedResponse(201, {"id": "created-once"})

    # Two "simultaneous" callers, same Idempotency-Key.
    results = await asyncio.gather(
        idempotency_middleware(_fake_request(), _slow_call_next),
        idempotency_middleware(_fake_request(), _slow_call_next),
    )

    assert execution_count == 1, "the underlying mutation ran more than once for the same Idempotency-Key"

    statuses = sorted(r.status_code for r in results)
    # Winner gets 201 (executed for real); the loser gets a 409
    # (IDEMPOTENCY_IN_PROGRESS) since it arrives while the winner still holds
    # the lock — it must never silently execute a second time nor hang.
    assert statuses == [201, 409]

    loser = next(r for r in results if r.status_code == 409)
    import json
    body = json.loads(bytes(loser.body))
    assert body["error"]["code"] == "IDEMPOTENCY_IN_PROGRESS"


@pytest.mark.asyncio
async def test_sequential_requests_with_same_key_replay_cached_response(monkeypatch):
    """Once the first request finishes (lock released, response cached), a
    later retry with the same key must replay the cached response instead
    of re-running the mutation — the actual client-retry scenario this
    middleware exists for."""
    from app.middleware import idempotency as idem_module

    shared = InProcessCacheBackend()
    monkeypatch.setattr(idem_module, "_cache", lambda: shared)

    execution_count = 0

    async def _call_next(request):
        nonlocal execution_count
        execution_count += 1
        return _StreamedResponse(201, {"id": "created-once", "n": execution_count})

    first = await idempotency_middleware(_fake_request(idem_key="seq-key-1"), _call_next)
    second = await idempotency_middleware(_fake_request(idem_key="seq-key-1"), _call_next)

    assert execution_count == 1
    assert first.status_code == 201 and second.status_code == 201
    import json
    assert json.loads(bytes(first.body)) == json.loads(bytes(second.body))
    assert second.headers.get("Idempotency-Replayed") == "true"
