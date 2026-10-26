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
    webhook       — provider inbound deliveries (per IP)  600 / min
    api           — everything else under /api            120 / min

Unauthenticated callers are keyed by client IP; authenticated callers are
keyed by their JWT subject so one noisy IP (NAT, office network) can't
throttle everyone behind it. Webhook callers are always keyed by IP.

Failure policy when the shared store is unreachable: the ``auth`` and ``ai``
tiers FAIL CLOSED (503, retryable). The ``webhook`` and ``api`` tiers FAIL
OPEN as a documented best-effort choice, so a cache outage does not drop
provider deliveries or block ordinary dashboard traffic.
"""

from __future__ import annotations

import logging
import ipaddress
import os
import time

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services.cache import get_shared_cache

log = logging.getLogger("app.rate_limit")


def _cache():
    return get_shared_cache("ratelimit")


def _trusted_proxy_networks() -> tuple[
    ipaddress.IPv4Network | ipaddress.IPv6Network, ...
]:
    networks = []
    for raw in os.environ.get("TRUSTED_PROXY_IPS", "").split(","):
        value = raw.strip()
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            log.warning("Ignoring invalid TRUSTED_PROXY_IPS entry: %s", value)
    return tuple(networks)


def _is_trusted_proxy(peer: str) -> bool:
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(address in network for network in _trusted_proxy_networks())


def _client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    fwd = request.headers.get("x-forwarded-for")
    if fwd and _is_trusted_proxy(peer):
        return fwd.split(",")[0].strip()
    return peer


def _caller_id(request: Request) -> str:
    """Only verified local access tokens may select a per-user bucket.

    Other credentials remain IP-scoped at this pre-authentication boundary.
    Unverified subjects would let an attacker rotate fabricated identities.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            from app.core.security import decode_access_token

            claims = decode_access_token(auth[7:].strip())
            sub = claims.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:  # noqa: BLE001 — malformed token; fall through to IP
            pass
    return f"ip:{_client_ip(request)}"


#: Tiers that must not run unthrottled when the shared store is down, in every environment.
FAIL_CLOSED_TIERS = frozenset({"auth", "ai"})
#: In production the general API tier also fails closed, so a Redis outage cannot
#: remove the request limits. Webhooks stay fail-open: provider deliveries are
#: signed and retried by the provider, and a limit outage must not drop them.
PRODUCTION_FAIL_CLOSED_TIERS = FAIL_CLOSED_TIERS | {"api"}


def _fails_closed(tier_name: str) -> bool:
    from app.core.config import settings

    tiers = (
        PRODUCTION_FAIL_CLOSED_TIERS if settings.is_production else FAIL_CLOSED_TIERS
    )
    return tier_name in tiers


#: Health probes must answer during a Redis outage, so they are never limited.
_UNLIMITED_PATHS = ("/api/health", "/health")


def _is_unlimited(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in _UNLIMITED_PATHS)


def _is_provider_webhook(path: str) -> bool:
    """Inbound provider deliveries: Stripe, Twilio voice, and channel webhooks.

    Channel webhooks are ``/api/channels/{provider}/inbound`` (Telegram, Meta,
    Instagram, email, SDK, Twilio SMS/WhatsApp). Voice callbacks live under
    ``/api/voice/``. The Stripe sink is ``/api/billing/webhook``.

    Webhooks are fail-open for rate limiting only. Their signatures, timestamps,
    replay checks and durable acceptance are enforced by the handlers themselves.
    """
    if path == "/api/billing/webhook":
        return True
    if path.startswith("/api/voice/"):
        return True
    return path.startswith("/api/channels/") and path.rstrip("/").endswith("/inbound")


_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class RateLimitTier:
    __slots__ = (
        "name",
        "prefixes",
        "write_prefixes",
        "limit",
        "window_seconds",
        "predicate",
        "per_ip_only",
    )

    def __init__(
        self,
        name: str,
        prefixes: tuple[str, ...],
        limit: int,
        window_seconds: int,
        *,
        predicate=None,
        per_ip_only: bool = False,
        write_prefixes: tuple[str, ...] = (),
    ):
        self.name = name
        self.prefixes = prefixes
        # Prefixes that only count for state-changing methods (e.g. model-calling
        # POST/PUT/PATCH routes under a prefix that also serves cheap GET reads).
        self.write_prefixes = write_prefixes
        self.limit = limit
        self.window_seconds = window_seconds
        self.predicate = predicate
        # Provider webhooks never send a bearer token; always bucket by source IP.
        self.per_ip_only = per_ip_only

    def matches(self, path: str, method: str = "GET") -> bool:
        if self.predicate is not None:
            return self.predicate(path)
        if path.startswith(self.prefixes):
            return True
        return bool(self.write_prefixes) and (
            method.upper() in _WRITE_METHODS and path.startswith(self.write_prefixes)
        )


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


# Order matters — first match wins, so put the most specific prefixes first.
TIERS: list[RateLimitTier] = [
    RateLimitTier(
        "auth",
        (
            "/api/auth/email-code/request",
            "/api/auth/email-code/verify",
            "/api/auth/dev-login",
            "/api/auth/refresh",
        ),
        _int_env("RATE_LIMIT_AUTH_PER_MINUTE", 10),
        60,
    ),
    RateLimitTier(
        "ai",
        (
            "/api/conversations",
            "/api/documents/upload",
            "/api/websites",
            "/api/rag/",
        ),
        _int_env("RATE_LIMIT_AI_PER_MINUTE", 20),
        60,
        # Write methods on these prefixes call models (LLM, embeddings, crawl,
        # simulations) or run agents/workflows, so they share the AI budget.
        write_prefixes=(
            "/api/ai/",
            "/api/assistants/",
            "/api/knowledge/sources",
            "/api/knowledge/search",
            "/api/v1/chat",
            "/api/v1/search",
            "/api/v1/workflows/",
            "/api/v2/",
            "/api/workspace/simulator",
            "/api/rag/",
        ),
    ),
    # Provider webhooks come in bursts from a few provider IPs. They get their own
    # per-source-IP tier so a burst is not answered with 429 (which drops deliveries).
    RateLimitTier(
        "webhook",
        (),
        _int_env("RATE_LIMIT_WEBHOOK_PER_MINUTE", 600),
        60,
        predicate=_is_provider_webhook,
        per_ip_only=True,
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
    if _is_unlimited(path):
        return await call_next(request)
    tier = next((t for t in TIERS if t.matches(path, request.method)), None)
    if tier is None:
        return await call_next(request)

    try:
        cache = _cache()
        window_bucket = int(time.time() // tier.window_seconds)
        caller = (
            f"ip:{_client_ip(request)}" if tier.per_ip_only else _caller_id(request)
        )
        key = f"{tier.name}:{caller}:{window_bucket}"
        count = cache.increment(key, ttl_seconds=tier.window_seconds * 1.5)
        if count > tier.limit:
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
    except Exception:  # noqa: BLE001 — the store itself failed
        log.warning("rate_limit_check_failed tier=%s", tier.name, exc_info=True)
        if _fails_closed(tier.name):
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_UNAVAILABLE",
                        "message": "Request limits are temporarily unavailable. Please retry shortly.",
                    },
                    "requestId": getattr(request.state, "request_id", None),
                },
                headers={"Retry-After": "5"},
            )

    return await call_next(request)
