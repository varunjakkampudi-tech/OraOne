"""Health endpoints — liveness, readiness, and database probes."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.database.session import init_engine

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/db")
async def db_health() -> dict:
    """Postgres reachability probe.

    Returns 200 with `{status: 'healthy', database: 'connected'}` when the
    engine can run `SELECT 1` against RDS. Returns 503 with a clear error
    detail otherwise (e.g. when the preview pod can't see the private VPC).
    """
    try:
        engine = init_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        # Driver and network error text can name hosts, users or schema details.
        # Keep it in server logs only and return a fixed message to the client.
        log.warning("DB health probe failed: %s: %s", type(e).__name__, e)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": "database unavailable",
            },
        )


@router.get("/ready")
async def readiness() -> dict:
    """Readiness probe — "can this instance receive traffic?"

    Unlike `/api/health` (pure liveness — always 200 while the process is
    up), this checks every hard dependency the API needs to actually serve
    requests: Postgres and Redis in production-like environments. Local
    development may omit Redis and use the explicitly documented in-process
    fallback.
    Point your orchestrator's readiness probe here, not at `/api/health`.
    """
    checks: dict[str, str] = {}
    ready = True

    try:
        engine = init_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"unreachable: {type(e).__name__}"
        ready = False  # Postgres is a hard dependency — not ready without it.

    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    production_like = environment in {"production", "prod", "staging"}
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        checks["redis"] = "not_configured"
        if production_like:
            ready = False
    else:
        try:
            import redis as _redis

            _redis.Redis.from_url(redis_url, socket_connect_timeout=2).ping()
            checks["redis"] = "connected"
        except Exception as e:
            checks["redis"] = f"unreachable: {type(e).__name__}"
            if production_like:
                ready = False

    if not ready:
        raise HTTPException(
            status_code=503, detail={"status": "not_ready", "checks": checks}
        )
    return {"status": "ready", "checks": checks}
