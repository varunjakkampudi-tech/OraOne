"""Crash matrix for workflow runs: what the sweep does when a worker stopped at each boundary.

Each case puts a run into the state a crash would leave behind, runs the recovery sweep on the
real database, and checks the outcome. Running the sweep twice must change nothing the second time.
Database-backed; skips when Postgres is not reachable.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import pytest
import pytest_asyncio

from app.database.models.workflow import (
    RunStatus,
    RunStepStatus,
    StepType,
    WorkflowTrigger,
)


def _postgres_reachable() -> bool:
    import asyncpg

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    dsn = url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    async def _probe() -> bool:
        try:
            conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=3)
            await conn.close()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_probe())
    except RuntimeError:
        return False


# Probe once at import time: inside a running test event loop the probe cannot start its own loop.
_DB_REACHABLE = _postgres_reachable()
db_only = pytest.mark.skipif(
    not _DB_REACHABLE, reason="Postgres is not reachable from this host."
)


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
    from app.database import session as db_session_module
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    maker = db_session_module.AsyncSessionLocal
    assert maker is not None
    async with maker() as s:
        yield s
        await s.rollback()
    await dispose_engine()


async def _seed_run(
    session, *, started_ago: timedelta, step_states: list[tuple[str, str]]
):
    """A workflow with one run. ``step_states`` gives (step type, step status) per step, in order."""
    from app.core.security import hash_password
    from app.database.models.organization import Organization, OrgPlan
    from app.database.models.project import Project, ProjectStatus
    from app.database.models.user import User
    from app.database.models.workflow import (
        Workflow,
        WorkflowRun,
        WorkflowRunStep,
        WorkflowStatus,
    )

    suffix = uuid.uuid4().hex[:8]
    owner = User(
        auth_subject=f"sub-wf-{suffix}",
        email=f"wf-{suffix}@example.test",
        full_name="Workflow Owner",
        password_hash=hash_password("not-used-in-this-test-11"),
        is_email_verified=True,
    )
    session.add(owner)
    await session.flush()
    org = Organization(
        name=f"WF {suffix}",
        slug=f"wf-{suffix}",
        plan=OrgPlan.free,
        owner_user_id=owner.id,
    )
    session.add(org)
    await session.flush()
    project = Project(
        organization_id=org.id,
        name="WF",
        slug=f"wf-main-{suffix}",
        is_default=True,
        status=ProjectStatus.active,
    )
    session.add(project)
    await session.flush()
    workflow = Workflow(
        organization_id=org.id,
        project_id=project.id,
        name="Crash matrix",
        status=WorkflowStatus.active,
        trigger_type=WorkflowTrigger.manual,
        trigger_config={},
    )
    session.add(workflow)
    await session.flush()
    started = datetime.now(timezone.utc) - started_ago
    run = WorkflowRun(
        workflow_id=workflow.id,
        organization_id=org.id,
        status=RunStatus.running,
        trigger=WorkflowTrigger.manual,
        input={},
        output={},
        steps_total=len(step_states),
        started_at=started,
    )
    session.add(run)
    await session.flush()
    for index, (step_type, step_status) in enumerate(step_states):
        session.add(
            WorkflowRunStep(
                run_id=run.id,
                organization_id=org.id,
                order_index=index,
                type=StepType(step_type),
                name=f"step {index}",
                status=RunStepStatus(step_status),
                config={},
                input={},
                output={},
            )
        )
    await session.commit()
    return run.id


async def _sweep_twice(monkeypatch):
    from app.database import session as db_session_module
    from app.services import workflow_engine

    monkeypatch.setattr(
        workflow_engine, "_maker", lambda: db_session_module.AsyncSessionLocal
    )
    first = await workflow_engine.reap_interrupted_runs()
    second = await workflow_engine.reap_interrupted_runs()
    return first, second


async def _fetch(run_id):
    from app.database import session as db_session_module
    from app.database.models.workflow import WorkflowRun, WorkflowRunStep
    from sqlalchemy import select

    async with db_session_module.AsyncSessionLocal() as session:
        run = await session.get(WorkflowRun, run_id)
        steps = list(
            (
                await session.scalars(
                    select(WorkflowRunStep)
                    .where(WorkflowRunStep.run_id == run_id)
                    .order_by(WorkflowRunStep.order_index)
                )
            ).all()
        )
        return run, steps


@db_only
@pytest.mark.asyncio
async def test_crash_after_claim_before_any_step_requeues_the_run(
    db_session, monkeypatch
):
    run_id = await _seed_run(
        db_session,
        started_ago=timedelta(hours=1),
        step_states=[("transform", "pending"), ("transform", "pending")],
    )
    first, second = await _sweep_twice(monkeypatch)
    run, steps = await _fetch(run_id)

    assert first["requeued"] == 1
    assert run.status == RunStatus.queued
    assert run.started_at is None
    assert all(step.status == RunStepStatus.pending for step in steps)
    assert second["requeued"] == 0  # idempotent


@db_only
@pytest.mark.asyncio
async def test_crash_mid_step_fails_the_run_and_never_retries_it(
    db_session, monkeypatch
):
    run_id = await _seed_run(
        db_session,
        started_ago=timedelta(hours=1),
        step_states=[
            ("transform", "completed"),
            ("notification", "running"),
            ("transform", "pending"),
        ],
    )
    first, second = await _sweep_twice(monkeypatch)
    run, steps = await _fetch(run_id)

    assert first["failed"] == 1
    assert run.status == RunStatus.failed
    assert "interrupted" in run.error_message
    assert steps[1].status == RunStepStatus.failed
    assert steps[2].status == RunStepStatus.pending  # never started, so never executed
    assert second["failed"] == 0


@db_only
@pytest.mark.asyncio
async def test_crash_after_the_last_step_completes_the_run(db_session, monkeypatch):
    run_id = await _seed_run(
        db_session,
        started_ago=timedelta(hours=1),
        step_states=[("transform", "completed"), ("transform", "skipped")],
    )
    first, _second = await _sweep_twice(monkeypatch)
    run, _steps = await _fetch(run_id)

    assert first["completed"] == 1
    assert run.status == RunStatus.completed
    assert run.finished_at is not None


@db_only
@pytest.mark.asyncio
async def test_durable_delay_in_progress_is_left_for_the_wait_resumer(
    db_session, monkeypatch
):
    run_id = await _seed_run(
        db_session,
        started_ago=timedelta(hours=1),
        step_states=[("delay", "running"), ("transform", "pending")],
    )
    first, _second = await _sweep_twice(monkeypatch)
    run, steps = await _fetch(run_id)

    assert first["waiting"] >= 1  # counts include runs left by earlier tests
    assert run.status == RunStatus.running
    assert steps[0].status == RunStepStatus.running


async def test_a_recent_run_is_not_touched(db_session, monkeypatch):
    run_id = await _seed_run(
        db_session,
        started_ago=timedelta(seconds=30),
        step_states=[("transform", "running")],
    )
    await _sweep_twice(monkeypatch)
    run, steps = await _fetch(run_id)

    # Counts are database-wide, so this checks the run itself: still running, step untouched.
    assert run.status == RunStatus.running
    assert steps[0].status == RunStepStatus.running
