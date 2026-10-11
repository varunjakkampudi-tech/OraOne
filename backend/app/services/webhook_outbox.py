"""Transactional outbox drain worker for webhooks.

Pattern:
    business transaction
        -> INSERT business rows
        -> INSERT webhook_outbox row(s)   (same session, same commit)
        -> COMMIT once
                |
                v
        this worker polls `webhook_outbox` for `pending` rows and hands
        them to the existing delivery machinery in app.services.webhook_service

This closes the gap a naive `asyncio.create_task(deliver(...))` has: if the
process crashes between committing business data and firing the webhook,
a fire-and-forget task is lost forever with no record it ever should have
happened. An outbox row, by contrast, only exists if the surrounding
transaction actually committed — so it WILL be delivered (eventually, by
this poller), even across a restart.

Single-process, best-effort poller — matches the same trade-off already
accepted by app/services/workflow_scheduler.py for this self-hosted scale.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.webhook import OutboxStatus, WebhookOutbox
from app.database.session import AsyncSessionLocal, init_engine

log = logging.getLogger("app.webhooks.outbox")

_POLL_SECONDS = 5
_BATCH_SIZE = 20
_MAX_ATTEMPTS = 5
_STALE_PROCESSING_SECONDS = 120  # reclaim rows stuck in PROCESSING (worker crashed mid-delivery)

_task: Optional[asyncio.Task] = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def enqueue(session: AsyncSession, *, organization_id: uuid.UUID, event: str, data: dict[str, Any]) -> WebhookOutbox:
    """Add a pending outbox row to ``session`` — caller commits alongside
    their own business-data changes so both succeed or fail together."""
    row = WebhookOutbox(organization_id=organization_id, event=event, payload=data)
    session.add(row)
    return row


def _maker():
    if AsyncSessionLocal is None:
        init_engine()
    from app.database.session import AsyncSessionLocal as Maker

    return Maker


def start_outbox_worker() -> None:
    """Launch the drain loop once (idempotent)."""
    global _task
    if _task is not None and not _task.done():
        return
    try:
        loop = asyncio.get_event_loop()
        _task = loop.create_task(_loop())
        log.info("webhook outbox worker started")
    except RuntimeError:
        log.warning("no running event loop; webhook outbox worker not started")


async def stop_outbox_worker() -> None:
    """Cancel the drain loop and wait for it to unwind — called on app
    shutdown so a restart doesn't leave a dangling task on the old event loop
    or race the DB engine being disposed mid-tick."""
    global _task
    if _task is None or _task.done():
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    log.info("webhook outbox worker stopped")


async def _loop() -> None:
    await asyncio.sleep(5)  # let app startup finish first
    while True:
        try:
            await _tick()
        except Exception as exc:  # pragma: no cover - resilience
            log.warning("outbox tick failed: %s", exc)
        await asyncio.sleep(_POLL_SECONDS)


async def _tick() -> None:
    from app.services import webhook_service  # local import — avoid a cycle at module load

    Maker = _maker()
    async with Maker() as session:  # type: ignore[misc]
        # Reclaim rows stuck in PROCESSING past the stale threshold — this is
        # what happens if the worker process crashes/is killed between
        # claiming a batch and finishing delivery. Without this, such rows
        # would be stuck forever since nothing else ever revisits PROCESSING.
        from datetime import timedelta

        stale_cutoff = _utcnow() - timedelta(seconds=_STALE_PROCESSING_SECONDS)
        stale_rows = list(
            (
                await session.scalars(
                    select(WebhookOutbox).where(
                        WebhookOutbox.status == OutboxStatus.PROCESSING,
                        WebhookOutbox.updated_at < stale_cutoff,
                    )
                )
            ).all()
        )
        for row in stale_rows:
            log.warning("reclaiming stale PROCESSING outbox row id=%s (worker likely crashed mid-delivery)", row.id)
            row.status = OutboxStatus.PENDING
        if stale_rows:
            await session.commit()

        rows = list(
            (
                await session.scalars(
                    select(WebhookOutbox)
                    .where(WebhookOutbox.status == OutboxStatus.PENDING)
                    .order_by(WebhookOutbox.created_at)
                    .limit(_BATCH_SIZE)
                )
            ).all()
        )
        if not rows:
            return
        # Claim them (PROCESSING) in one commit so a second poller replica
        # (if ever run) wouldn't double-process the same batch.
        for row in rows:
            row.status = OutboxStatus.PROCESSING
        await session.commit()

    for row in rows:
        await _deliver_outbox_row(row.id)


async def _deliver_outbox_row(outbox_id: uuid.UUID) -> None:
    from app.services import webhook_service

    Maker = _maker()
    async with Maker() as session:  # type: ignore[misc]
        row = await session.get(WebhookOutbox, outbox_id)
        if row is None:
            return
        try:
            scheduled = await webhook_service.dispatch(row.organization_id, row.event, row.payload.get("data", row.payload))
            row.status = OutboxStatus.COMPLETED
            row.processed_at = _utcnow()
            row.attempts = (row.attempts or 0) + 1
            log.info("outbox delivered id=%s event=%s scheduled=%d", row.id, row.event, scheduled)
        except Exception as e:  # noqa: BLE001
            row.attempts = (row.attempts or 0) + 1
            row.last_error = str(e)[:500]
            row.status = (
                OutboxStatus.FAILED if row.attempts >= _MAX_ATTEMPTS else OutboxStatus.PENDING
            )
            log.warning("outbox delivery failed id=%s event=%s attempt=%d err=%s", row.id, row.event, row.attempts, e)
        await session.commit()
