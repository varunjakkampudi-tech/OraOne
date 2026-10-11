"""Tiered, Redis-backed rate limiting middleware.

Replaces the single fixed auth-only limiter that used to live inline in
server.py with a small set of named tiers, checked in order (most specific
first). Each tier is a fixed-window counter keyed by (client, path window)
via app.services.cache.get_shared_cache("ratelimit") — Redis when
REDIS_URL is set, so limits are correctly shared across every worker
process, not just per-worker.

Tiers (override any of them via env vars — see the *_PER_MINUTE constants):

    auth          — login/signup/etc.                    10 / min
    password      — forgot/reset-password                 5 / 15 min
    ai            — chat/document/crawl endpoints         20 / min
    api           — everything else under /api            120 / min

Unauthenticated callers are keyed by client IP; authenticated callers are
keyed by their JWT subject so one noisy IP (NAT, office network) can't
throttle everyone behind it.
"""
from __future__ import annotations

import logging
import os
import time

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services.cache import get_shared_cache

log = logging.getLogger("app.rate_limit")


def _cache():
    return get_shared_cache("ratelimit")


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _caller_id(request: Request) -> str:
    """Prefer the JWT subject (stable per-user) over raw IP when present."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            from jose import jwt as jose_jwt

            claims = jose_jwt.get_unverified_claims(auth[7:].strip())
            sub = claims.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:  # noqa: BLE001 — malformed token; fall through to IP
            pass
    return f"ip:{_client_ip(request)}"


class RateLimitTier:
    __slots__ = ("name", "prefixes", "limit", "window_seconds")

    def __init__(self, name: str, prefixes: tuple[str, ...], limit: int, window_seconds: int):
        self.name = name
        self.prefixes = prefixes
        self.limit = limit
        self.window_seconds = window_seconds

    def matches(self, path: str) -> bool:
        return path.startswith(self.prefixes)


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


# Order matters — first match wins, so put the most specific prefixes first.
TIERS: list[RateLimitTier] = [
    RateLimitTier(
        "password",
        ("/api/auth/forgot-password", "/api/auth/reset-password"),
        _int_env("RATE_LIMIT_PASSWORD_PER_15MIN", 5),
        15 * 60,
    ),
    RateLimitTier(
        "auth",
        (
            "/api/auth/login", "/api/auth/signup", "/api/auth/refresh",
            "/api/auth/resend", "/api/auth/verify",
        ),
        _int_env("RATE_LIMIT_AUTH_PER_MINUTE", 10),
        60,
    ),
    RateLimitTier(
        "ai",
        (
            "/api/conversations", "/api/documents/upload", "/api/websites",
            "/api/rag/",
        ),
        _int_env("RATE_LIMIT_AI_PER_MINUTE", 20),
        60,
    ),
    RateLimitTier(
        "api",
        ("/api/",),
        _int_env("RATE_LIMIT_API_PER_MINUTE", 120),
        60,
    ),
]


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    tier = next((t for t in TIERS if t.matches(path)), None)
    if tier is None:
        return await call_next(request)

    try:
        cache = _cache()
        window_bucket = int(time.time() // tier.window_seconds)
        key = f"{tier.name}:{_caller_id(request)}:{window_bucket}"
        count = int(cache.get(key) or 0)
        if count >= tier.limit:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": f"Too many requests ({tier.name} tier). Please slow down.",
                    },
                    "requestId": getattr(request.state, "request_id", None),
                },
                headers={"Retry-After": str(tier.window_seconds)},
            )
        cache.set(key, count + 1, ttl_seconds=tier.window_seconds * 1.5)
    except Exception:  # noqa: BLE001 — never block a request on a cache hiccup
        log.warning("rate_limit_check_failed", exc_info=True)

    return await call_next(request)
