"""API key lifecycle, authentication & rate limiting (Phase 12, Module 9).

Key format: ``sk_ora_<id8>_<secret>`` where ``sk_ora_<id8>`` is the public,
non-secret ``prefix`` (stored + displayable) and ``<secret>`` is a
high-entropy token. Only ``sha256(full_key)`` is persisted.

Rate limiting is a per-key fixed-window (1 minute) counter held in process
memory. The per-minute ceiling comes from the active plan's ``api_rpm``
limit (``-1`` = unlimited, ``0`` = API disabled on this plan). This is
sufficient for a single-worker deployment; a Redis-backed limiter would be
the multi-worker upgrade path.
"""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_scopes import normalize_scopes
from app.database.models.api_key import ApiKey
from app.services import billing_service, usage_service

_KEY_BYTES = 32
_ID_BYTES = 4  # -> 8 hex chars


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(full_key: str) -> str:
    return hashlib.sha256(full_key.encode("utf-8")).hexdigest()


def generate_key() -> tuple[str, str]:
    """Return ``(full_key, prefix)``. The full key is shown to the user once."""
    id_part = secrets.token_hex(_ID_BYTES)
    secret = secrets.token_urlsafe(_KEY_BYTES)
    prefix = f"sk_ora_{id_part}"
    full = f"{prefix}_{secret}"
    return full, prefix


def _prefix_of(full_key: str) -> Optional[str]:
    parts = full_key.split("_")
    if len(parts) < 4 or parts[0] != "sk" or parts[1] != "ora":
        return None
    return f"sk_ora_{parts[2]}"


# ── lifecycle ───────────────────────────────────────────────────────────
async def list_keys(
    session: AsyncSession,
    organization_id: uuid.UUID,
    project_id: Optional[uuid.UUID] = None,
) -> list[ApiKey]:
    stmt = (
        select(ApiKey)
        .where(ApiKey.organization_id == organization_id)
        .where(ApiKey.deleted_at.is_(None))
        .order_by(ApiKey.created_at.desc())
    )
    if project_id is not None:
        stmt = stmt.where(ApiKey.project_id == project_id)
    rows = await session.scalars(stmt)
    return list(rows)


async def create_key(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    name: str,
    scopes: list[str],
    created_by_user_id: Optional[uuid.UUID],
    expires_at: Optional[datetime] = None,
    project_id: Optional[uuid.UUID] = None,
) -> tuple[ApiKey, str]:
    """Create a key; returns ``(row, full_key)``. ``full_key`` is shown once."""
    clean_scopes = normalize_scopes(scopes)
    if not clean_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid scope is required.",
        )
    full, prefix = generate_key()
    row = ApiKey(
        organization_id=organization_id,
        project_id=project_id,
        name=name.strip() or "Untitled key",
        prefix=prefix,
        key_hash=_hash(full),
        scopes=clean_scopes,
        created_by_user_id=created_by_user_id,
        expires_at=expires_at,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row, full


async def revoke_key(
    session: AsyncSession, organization_id: uuid.UUID, key_id: uuid.UUID
) -> Optional[ApiKey]:
    row = await session.scalar(
        select(ApiKey)
        .where(ApiKey.id == key_id)
        .where(ApiKey.organization_id == organization_id)
        .where(ApiKey.deleted_at.is_(None))
    )
    if row is None:
        return None
    row.deleted_at = _now()
    await session.commit()
    await session.refresh(row)
    return row


# ── authentication ──────────────────────────────────────────────────────
async def authenticate(session: AsyncSession, full_key: str) -> ApiKey:
    """Resolve + verify a presented key. Raises 401 on any failure."""
    prefix = _prefix_of(full_key or "")
    if prefix is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed API key."
        )
    row = await session.scalar(
        select(ApiKey)
        .where(ApiKey.prefix == prefix)
        .where(ApiKey.deleted_at.is_(None))
    )
    if row is None or not secrets.compare_digest(row.key_hash, _hash(full_key)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key."
        )
    if row.expires_at is not None and row.expires_at < _now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key has expired."
        )
    return row


def require_scope(key: ApiKey, scope: str) -> None:
    if scope not in (key.scopes or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key is missing required scope '{scope}'.",
        )


async def touch_last_used(session: AsyncSession, key: ApiKey) -> None:
    key.last_used_at = _now()
    await session.commit()


# ── rate limiting (in-process fixed window) ──────────────────────────────
# key_id -> (window_minute_epoch, count)
_RATE_BUCKETS: dict[str, tuple[int, int]] = {}


async def enforce_rate_limit(session: AsyncSession, key: ApiKey) -> dict:
    """Enforce per-minute quota from the plan's ``api_rpm``; raises 429/403.

    Returns ``{"limit", "remaining"}`` for response headers.
    """
    sub = await billing_service.get_or_create_subscription(
        session, key.organization_id
    )
    rpm = int((sub.plan.limits or {}).get("api_rpm", 0))

    if rpm == 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="The API is not available on your current plan. Upgrade to enable it.",
        )

    # Record monthly api_calls usage regardless of limit shape.
    await usage_service.record_usage(session, key.organization_id, "api_calls", 1)

    if rpm < 0:  # unlimited
        return {"limit": -1, "remaining": -1}

    window = int(time.time() // 60)
    bucket_key = str(key.id)
    cur_window, count = _RATE_BUCKETS.get(bucket_key, (window, 0))
    if cur_window != window:
        cur_window, count = window, 0
    count += 1
    _RATE_BUCKETS[bucket_key] = (cur_window, count)

    if count > rpm:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({rpm} requests/minute). Try again shortly.",
        )
    return {"limit": rpm, "remaining": max(0, rpm - count)}
