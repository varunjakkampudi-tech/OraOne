"""Cache backend abstraction with explicit production Redis requirements.

The entitlement snapshot cache is currently a per-process dict — correct and
fast for a single API node, but it means a mutation on node A isn't seen by
node B until each node's TTL lapses. Rather than bake that assumption in, the
storage sits behind :class:`CacheBackend` so a distributed backend (Redis +
pub/sub) can be dropped in without touching call sites.

    :class:`CacheBackend`          — the interface every backend implements.
    :class:`InProcessCacheBackend` — default; a plain dict (no cross-node sync).
    :class:`RedisCacheBackend`     — DESIGN STUB; native TTL + shared store.
    :func:`get_cache_backend`      — env-driven factory (defaults to in-process).

Selection is via ``ENTITLEMENTS_CACHE_BACKEND`` (``inprocess`` | ``redis``).
Local development may use the in-process backend. Production-like environments
must use a reachable Redis backend for shared auth, idempotency, rate-limit,
and entitlement state; silently falling back to process-local memory would
break those guarantees across workers.

``native_ttl`` tells the caller who owns expiry: in-process backends return
``False`` (the caller wraps values with its own clock), distributed backends
return ``True`` (the store expires keys itself).
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

log = logging.getLogger("app.cache")
_PRODUCTION_LIKE = {"production", "prod", "staging"}


def _is_production_like() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() in _PRODUCTION_LIKE


class CacheBackend(ABC):
    """A minimal key→value store used for per-org snapshot caching."""

    #: ``True`` if the backend expires keys itself (caller stores raw values);
    #: ``False`` if the caller must attach its own expiry metadata.
    native_ttl: bool = False

    #: Human-readable id for diagnostics / metrics.
    name: str = "cache"

    @abstractmethod
    def get(self, key: str) -> Optional[Any]: ...

    @abstractmethod
    def set(
        self, key: str, value: Any, ttl_seconds: Optional[float] = None
    ) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    def consume(self, key: str) -> Optional[Any]:
        """Return and remove a value; shared backends make this atomic."""
        value = self.get(key)
        if value is not None:
            self.delete(key)
        return value

    @abstractmethod
    def clear(self) -> None: ...

    def set_if_not_exists(
        self, key: str, value: Any, ttl_seconds: Optional[float] = None
    ) -> bool:
        """Atomically set ``key`` only if absent. Returns True if this call set it.

        Used for idempotency-key locking and refresh-token issuance. The base
        implementation is a best-effort (non-atomic) fallback; backends that
        can do better (Redis ``SET NX``) should override this.
        """
        if self.get(key) is not None:
            return False
        self.set(key, value, ttl_seconds=ttl_seconds)
        return True

    def increment(self, key: str, ttl_seconds: Optional[float] = None) -> int:
        """Increment a counter, using an atomic implementation when available."""
        value = int(self.get(key) or 0) + 1
        self.set(key, value, ttl_seconds=ttl_seconds)
        return value


class InProcessCacheBackend(CacheBackend):
    """A plain in-memory dict. Single-node only — no cross-process visibility.

    ``ttl_seconds`` is ignored here: the caller (entitlements) wraps values
    with an expiry timestamp and checks it on read, which keeps the clock
    monkeypatchable in tests and avoids a background sweeper.
    """

    native_ttl = False
    name = "inprocess"

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        self._store[key] = value

    def increment(self, key: str, ttl_seconds: Optional[float] = None) -> int:
        value = int(self._store.get(key) or 0) + 1
        self._store[key] = value
        return value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


class RedisCacheBackend(CacheBackend):
    """A shared, TTL-native cache for multi-node deployments.

    Not enabled by default. When selected it lazily imports ``redis`` and
    stores JSON-serialised snapshots under a namespaced key with a native
    ``EX`` TTL, so every API node reads the same value and expiry is handled
    by Redis. A companion pub/sub channel (see :meth:`publish_invalidation`)
    is the seam for cross-node cache invalidation — wire it to the entitlement
    mutation paths when this backend goes live.
    """

    native_ttl = True
    name = "redis"

    def __init__(self, url: str, *, prefix: str = "oraone:ent:") -> None:
        try:
            import redis  # type: ignore
        except Exception as e:  # pragma: no cover — optional dependency
            raise RuntimeError(
                "RedisCacheBackend requires the 'redis' package. "
                "Install it and set REDIS_URL to enable the distributed cache."
            ) from e
        self._redis = redis.Redis.from_url(url, decode_responses=True)
        # ``Redis.from_url`` is lazy. Verify reachability here so production
        # cannot boot with a cache object that will fail only on first use.
        self._redis.ping()
        self._prefix = prefix
        self._channel = f"{prefix}invalidate"

    def _k(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[Any]:  # pragma: no cover — needs redis
        raw = self._redis.get(self._k(key))
        return json.loads(raw) if raw is not None else None

    def set(
        self, key: str, value: Any, ttl_seconds: Optional[float] = None
    ) -> None:  # pragma: no cover
        payload = json.dumps(value, default=str)
        if ttl_seconds and ttl_seconds > 0:
            self._redis.set(self._k(key), payload, ex=int(ttl_seconds))
        else:
            self._redis.set(self._k(key), payload)

    def delete(self, key: str) -> None:  # pragma: no cover — needs redis
        self._redis.delete(self._k(key))

    def consume(self, key: str) -> Optional[Any]:  # pragma: no cover
        raw = self._redis.getdel(self._k(key))
        return json.loads(raw) if raw is not None else None

    def clear(self) -> None:  # pragma: no cover — needs redis
        for k in self._redis.scan_iter(f"{self._prefix}*"):
            self._redis.delete(k)

    def set_if_not_exists(
        self, key: str, value: Any, ttl_seconds: Optional[float] = None
    ) -> bool:  # pragma: no cover
        payload = json.dumps(value, default=str)
        return bool(
            self._redis.set(
                self._k(key),
                payload,
                nx=True,
                ex=int(ttl_seconds) if ttl_seconds else None,
            )
        )

    def increment(
        self, key: str, ttl_seconds: Optional[float] = None
    ) -> int:  # pragma: no cover
        value = int(self._redis.incr(self._k(key)))
        if value == 1 and ttl_seconds:
            self._redis.expire(self._k(key), int(ttl_seconds))
        return value

    def publish_invalidation(self, key: str) -> None:  # pragma: no cover — needs redis
        """Broadcast an invalidation so peer nodes drop their local copy."""
        self._redis.publish(self._channel, key)


def get_cache_backend() -> CacheBackend:
    """Build the configured cache backend (defaults to in-process locally).

    ``ENTITLEMENTS_CACHE_BACKEND=redis`` opts into :class:`RedisCacheBackend`
    using ``REDIS_URL``. Production-like environments fail closed when Redis is
    selected but missing or unreachable.
    """
    choice = os.getenv("ENTITLEMENTS_CACHE_BACKEND", "inprocess").strip().lower()
    if choice in {"redis", "distributed"}:
        url = os.getenv("REDIS_URL", "").strip()
        if not url:
            message = "ENTITLEMENTS_CACHE_BACKEND=redis requires REDIS_URL."
            if _is_production_like():
                raise RuntimeError(message)
            log.warning(
                "%s Falling back to in-process cache for local development.",
                message,
            )
            return InProcessCacheBackend()
        try:
            backend = RedisCacheBackend(url)
            log.info("entitlement cache backend: redis (%s)", url)
            return backend
        except Exception as e:  # pragma: no cover — optional dependency
            if _is_production_like():
                raise RuntimeError(
                    "Configured Redis entitlement cache is unavailable."
                ) from e
            log.warning(
                "Redis cache backend unavailable (%s); falling back to in-process "
                "for local development.",
                e,
            )
            return InProcessCacheBackend()
    return InProcessCacheBackend()


_namespaced_singletons: dict[str, CacheBackend] = {}


def get_shared_cache(namespace: str) -> CacheBackend:
    """A general-purpose namespaced cache for auth/idempotency/rate-limiting.

    Unlike :func:`get_cache_backend` (gated by
    ``ENTITLEMENTS_CACHE_BACKEND``), this always prefers Redis when
    ``REDIS_URL`` is set — refresh tokens, idempotency keys, and rate-limit
    counters all need to be shared across every worker process/node. Local
    development may fall back to process-local memory; production-like
    environments raise instead.

    One backend instance is cached per ``namespace`` for the process lifetime.
    """
    if namespace in _namespaced_singletons:
        return _namespaced_singletons[namespace]

    url = os.getenv("REDIS_URL", "").strip()
    backend: CacheBackend
    if url:
        try:
            backend = RedisCacheBackend(url, prefix=f"oraone:{namespace}:")
            log.info("shared cache [%s]: redis", namespace)
        except Exception as e:  # pragma: no cover — optional dependency
            if _is_production_like():
                raise RuntimeError(
                    f"Configured shared Redis cache is unavailable for namespace "
                    f"'{namespace}'."
                ) from e
            log.warning(
                "Redis unavailable for shared cache [%s] (%s); using in-process "
                "for local development.",
                namespace,
                e,
            )
            backend = InProcessCacheBackend()
    else:
        if _is_production_like():
            raise RuntimeError(
                f"Shared Redis cache is required in {_PRODUCTION_LIKE} environments "
                f"for namespace '{namespace}'. Set REDIS_URL."
            )
        backend = InProcessCacheBackend()
    _namespaced_singletons[namespace] = backend
    return backend
