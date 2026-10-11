"""Redis-backed idempotency middleware.

Mutating requests (POST/PUT/PATCH/DELETE) that carry an ``Idempotency-Key``
header are de-duplicated: the first execution's response is cached; any
retry with the same key (same org scope) replays the cached response
instead of re-running the operation. Protects against duplicate agent
creation, double document uploads, etc. on client retries / network blips.

Flow:
    request (+ Idempotency-Key)
        -> cache lookup
        -> hit?  replay cached (status, body, content-type)
        -> miss? acquire short lock -> run -> cache response -> return

Backed by app.services.cache.get_shared_cache("idempotency") (Redis when
REDIS_URL is set, in-process otherwise). Never blocks requests that don't
send the header — this is strictly opt-in per the API contract.
"""
from __future__ import annotations

import json
import logging

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.services.cache import get_shared_cache

log = logging.getLogger("app.idempotency")

_HEADER = "Idempotency-Key"
_RESPONSE_TTL_SECONDS = 24 * 3600
_LOCK_TTL_SECONDS = 30
_METHODS = {"POST", "PUT", "PATCH"}


def _cache():
    return get_shared_cache("idempotency")


def _scope_key(request: Request, idem_key: str) -> str:
    # Namespaced by path + caller so the same key from two different users
    # (or two different endpoints) can never collide.
    auth = request.headers.get("authorization", "")
    return f"{request.url.path}:{auth[-24:]}:{idem_key}"


async def idempotency_middleware(request: Request, call_next):
    if request.method not in _METHODS:
        return await call_next(request)

    idem_key = request.headers.get(_HEADER)
    if not idem_key:
        return await call_next(request)

    cache = _cache()
    scoped_key = _scope_key(request, idem_key)

    # Fail CLOSED, not open: a caller that explicitly asked for idempotency
    # protection on a mutation would rather get a clear, retryable 503 than
    # silently lose that protection and risk a duplicate charge/agent/
    # document during a Redis outage.
    try:
        cached = cache.get(f"resp:{scoped_key}")
    except Exception as e:  # noqa: BLE001
        log.error("idempotency_cache_unavailable path=%s err=%s", request.url.path, e)
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "IDEMPOTENCY_UNAVAILABLE",
                    "message": "Idempotency protection is temporarily unavailable. Please retry shortly.",
                },
            },
            headers={"Retry-After": "5"},
        )

    if cached is not None:
        return JSONResponse(
            status_code=cached["status_code"],
            content=cached["body"],
            headers={"Idempotency-Replayed": "true"},
        )

    try:
        acquired = cache.set_if_not_exists(f"lock:{scoped_key}", True, ttl_seconds=_LOCK_TTL_SECONDS)
    except Exception as e:  # noqa: BLE001
        log.error("idempotency_cache_unavailable path=%s err=%s", request.url.path, e)
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "IDEMPOTENCY_UNAVAILABLE",
                    "message": "Idempotency protection is temporarily unavailable. Please retry shortly.",
                },
            },
            headers={"Retry-After": "5"},
        )
    if not acquired:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "error": {
                    "code": "IDEMPOTENCY_IN_PROGRESS",
                    "message": "A request with this Idempotency-Key is already being processed.",
                },
            },
        )
    lock_key = f"lock:{scoped_key}"

    try:
        response = await call_next(request)
        body = b"".join([chunk async for chunk in response.body_iterator])

        # Only cache successful/deterministic outcomes — retry-able errors
        # (5xx) should be allowed to actually retry, not get stuck replaying
        # a transient failure.
        if response.status_code < 500:
            try:
                parsed = json.loads(body) if body else None
            except ValueError:
                parsed = None
            if parsed is not None:
                try:
                    cache.set(
                        f"resp:{scoped_key}",
                        {"status_code": response.status_code, "body": parsed},
                        ttl_seconds=_RESPONSE_TTL_SECONDS,
                    )
                except Exception as e:  # noqa: BLE001 — mutation already succeeded; don't fail the response over a cache write
                    log.warning("idempotency_cache_write_failed path=%s err=%s", request.url.path, e)

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
    finally:
        try:
            cache.delete(lock_key)
        except Exception as e:  # noqa: BLE001 — lock will still expire via its own TTL
            log.warning("idempotency_lock_release_failed path=%s err=%s", request.url.path, e)
