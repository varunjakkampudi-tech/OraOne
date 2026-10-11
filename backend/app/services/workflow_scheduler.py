"""In-process workflow scheduler (Phase 11).

A lightweight asyncio loop that periodically scans for *active* workflows
whose trigger is ``schedule`` and which are due to run, then enqueues a run
and dispatches it through the workflow engine.

Scheduling config lives in ``workflow.trigger_config``:

    {"interval_minutes": 60}            # run roughly hourly
    {"every": "daily"}                  # daily / hourly / weekly preset

"Due" is computed from ``workflow.last_run_at``. This is a best-effort,
single-process scheduler — fine for self-hosted / single-node deployments.
It is intentionally tolerant: any error in a tick is logged and the loop
keeps going.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from app.database.models.workflow import (
    RunStatus,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTrigger,
)
from app.database.session import AsyncSessionLocal, init_engine
from app.services.workflow_engine import execute_run

log = logging.getLogger("app.workflow.scheduler")

_POLL_SECONDS = 60
_PRESET_MINUTES = {"hourly": 60, "daily": 1440, "weekly": 10080, "monthly": 43200}

_task: Optional[asyncio.Task] = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _maker():
    if AsyncSessionLocal is None:
        init_engine()
    from app.database.session import AsyncSessionLocal as Maker

    return Maker


def _interval_minutes(cfg: dict) -> Optional[int]:
    if not isinstance(cfg, dict):
        return None
    if cfg.get("interval_minutes"):
        try:
            return max(1, int(cfg["interval_minutes"]))
        except (TypeError, ValueError):
            return None
    every = str(cfg.get("every", "")).lower().strip()
    return _PRESET_MINUTES.get(every)


def start_scheduler() -> None:
    """Launch the scheduler loop once (idempotent)."""
    global _task
    if _task is not None and not _task.done():
        return
    try:
        loop = asyncio.get_event_loop()
        _task = loop.create_task(_loop())
        log.info("workflow scheduler started")
    except RuntimeError:
        log.warning("no running event loop; scheduler not started")


async def stop_scheduler() -> None:
    """Cancel the scheduler loop and wait for it to unwind — called on app
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
    log.info("workflow scheduler stopped")


async def _loop() -> None:
    # Small initial delay so app startup completes first.
    await asyncio.sleep(10)
    while True:
        try:
            await _tick()
        except Exception as exc:  # pragma: no cover - resilience
            log.warning("scheduler tick failed: %s", exc)
        await asyncio.sleep(_POLL_SECONDS)


async def _tick() -> None:
    Maker = _maker()
    async with Maker() as session:  # type: ignore[misc]
        rows = list(
            (
                await session.scalars(
                    select(Workflow)
                    .where(Workflow.status == WorkflowStatus.active)
                    .where(Workflow.trigger_type == WorkflowTrigger.schedule)
                    .where(Workflow.deleted_at.is_(None))
                )
            ).all()
        )
        now = _utcnow()
        due_run_ids: list[uuid.UUID] = []

        for wf in rows:
            interval = _interval_minutes(wf.trigger_config or {})
            if not interval:
                continue
            last = wf.last_run_at
            if last is not None and (now - last) < timedelta(minutes=interval):
                continue

            steps = list(
                (
                    await session.scalars(
                        select(WorkflowStep)
                        .where(WorkflowStep.workflow_id == wf.id)
                        .order_by(WorkflowStep.order_index)
                    )
                ).all()
            )
            if not steps:
                continue

            run = WorkflowRun(
                workflow_id=wf.id,
                organization_id=wf.organization_id,
                status=RunStatus.queued,
                trigger=WorkflowTrigger.schedule,
                triggered_by=None,
                input={},
                steps_total=len(steps),
            )
            session.add(run)
            await session.flush()
            for step in steps:
                session.add(
                    WorkflowRunStep(
                        run_id=run.id,
                        organization_id=wf.organization_id,
                        step_id=step.id,
                        order_index=step.order_index,
                        type=step.type,
                        name=step.name,
                        config=step.config or {},
                    )
                )
            # Mark last_run_at now so we don't double-fire before it finishes.
            wf.last_run_at = now
            due_run_ids.append(run.id)

        if due_run_ids:
            await session.commit()
            log.info("scheduler dispatched %d run(s)", len(due_run_ids))

    # Dispatch outside the scan session; each run owns its own session.
    for run_id in due_run_ids:
        asyncio.create_task(execute_run(run_id))
