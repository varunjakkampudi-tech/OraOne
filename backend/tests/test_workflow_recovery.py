"""Committed-but-unstarted workflow runs are recovered by the scheduler, whatever their trigger.

A public API or manual run commits as queued and then starts in a background
task. If the process dies between those two steps, the scheduler must still start it.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from app.services import workflow_scheduler


def _sql(query) -> str:
    return str(
        query.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def test_recovery_query_covers_every_trigger_and_only_queued_runs():
    sql = _sql(workflow_scheduler.queued_runs_query(datetime.now(timezone.utc)))
    assert "status = 'queued'" in sql
    assert "trigger" not in sql.lower()


def test_recovery_query_leaves_recent_runs_to_their_request():
    now = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
    sql = _sql(workflow_scheduler.queued_runs_query(now))
    cutoff = (now - workflow_scheduler.QUEUED_RECOVERY_AFTER).strftime("%Y-%m-%d %H:%M")
    assert cutoff in sql


def test_dispatcher_starts_each_recovered_run(monkeypatch):
    run_ids = [uuid.uuid4(), uuid.uuid4()]
    started: list[uuid.UUID] = []

    class _Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        async def scalars(self, _query):
            return SimpleNamespace(all=lambda: run_ids)

    async def _execute_run(run_id):
        started.append(run_id)

    monkeypatch.setattr(workflow_scheduler, "_maker", lambda: lambda: _Session())
    monkeypatch.setattr(workflow_scheduler, "execute_run", _execute_run)

    async def _drive():
        await workflow_scheduler._dispatch_queued_runs()
        await asyncio.gather(
            *list(workflow_scheduler._inflight), return_exceptions=True
        )

    asyncio.run(_drive())
    assert sorted(started, key=str) == sorted(run_ids, key=str)
    assert timedelta(seconds=60) == workflow_scheduler.QUEUED_RECOVERY_AFTER
