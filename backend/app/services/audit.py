"""Audit logging (Phase 6, persisted in Phase 12 Module 5).

Emits structured JSON log records via Python's stdlib ``logging`` to a
dedicated logger (``app.audit``) AND buffers them in-process so they can be
flushed to the ``audit_logs`` table after each request. The logger sink
(stdout → CloudWatch / Loki / Datadog) is kept for streaming; the DB table
gives an org-scoped, queryable history for compliance review.

``audit()`` stays synchronous and call-site compatible — it just appends to
a bounded buffer. ``flush_pending(session)`` drains the buffer into the DB
and is invoked by middleware after each request.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("app.audit")

# Bounded buffer of records awaiting DB persistence. Bounded so a flush
# outage can never exhaust memory; oldest records are dropped first.
_MAX_PENDING = 5000
_PENDING: "deque[dict[str, Any]]" = deque(maxlen=_MAX_PENDING)


def audit(
    action: str,
    *,
    resource: str,
    organization_id: str,
    user_id: str,
    resource_id: Optional[str] = None,
    before: Optional[dict[str, Any]] = None,
    after: Optional[dict[str, Any]] = None,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Emit one structured audit record.

    Args:
        action: ``create`` / ``update`` / ``delete`` / ``read`` / etc.
        resource: Resource family (``agent`` / ``integration`` / …).
        resource_id: Stringified UUID of the affected row, if any.
        organization_id / user_id: Tenant + actor (stringified UUIDs).
        before / after: Field snapshots for diffing. Keep them small.
        meta: Arbitrary extras (search query, filter set, pagination, …).
    """
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "organization_id": organization_id,
        "user_id": user_id,
        "before": before,
        "after": after,
        "meta": meta,
    }
    # ``json.dumps(default=str)`` so UUIDs / datetimes / Enums don't blow up
    # the audit pipe if a caller forgets to stringify.
    log.info("AUDIT %s", json.dumps(record, default=str))
    _PENDING.append(record)


def _coerce_uuid(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


async def flush_pending(session) -> int:
    """Drain buffered audit records into the ``audit_logs`` table.

    Best-effort: never raises. Returns the number of rows persisted. On any
    failure the in-flight batch is re-queued so nothing is silently lost.
    """
    if not _PENDING:
        return 0
    # Local import avoids a circular import at module load time.
    from app.database.models.audit_log import AuditLog

    batch: list[dict[str, Any]] = []
    while _PENDING:
        batch.append(_PENDING.popleft())

    rows = []
    for rec in batch:
        created = _parse_ts(rec.get("ts"))
        kwargs: dict[str, Any] = {
            "organization_id": _coerce_uuid(rec.get("organization_id")),
            "user_id": _coerce_uuid(rec.get("user_id")),
            "action": str(rec.get("action") or "")[:40],
            "resource": str(rec.get("resource") or "")[:80],
            "resource_id": (str(rec["resource_id"])[:120] if rec.get("resource_id") else None),
            "before": rec.get("before"),
            "after": rec.get("after"),
            "meta": rec.get("meta"),
        }
        if created is not None:
            kwargs["created_at"] = created
        rows.append(AuditLog(**kwargs))

    try:
        session.add_all(rows)
        await session.commit()
        return len(rows)
    except Exception:  # noqa: BLE001 — audit must never break a request
        try:
            await session.rollback()
        except Exception:  # noqa: BLE001
            pass
        # Re-queue so the next flush retries; preserve original order.
        for rec in reversed(batch):
            _PENDING.appendleft(rec)
        log.exception("Failed to flush %d audit records", len(batch))
        return 0

