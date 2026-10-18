"""Workflow automation: human approval, event triggers, the schedule loop and the API guards.

Complements test_workflow_engine_completion.py (send/wait/condition/claim behaviour). No database
and no network: sessions are scripted and external work is replaced with recorders.
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.workflows import routes as wf_routes
from app.database.models.workflow import (
    RunStatus,
    RunStepStatus,
    StepType,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTrigger,
)
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import workflow_engine as engine
from app.services import workflow_scheduler as scheduler
from app.services import workflow_triggers as triggers

ORG = uuid.uuid4()
OTHER_ORG = uuid.uuid4()
PROJECT = uuid.uuid4()
USER = uuid.uuid4()
NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


class _Rows:
    def __init__(self, items, rowcount=1):
        self._items = list(items)
        # Conditional UPDATEs (the approval claim) report how many rows they matched.
        self.rowcount = rowcount

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self, *, scalars=()):
        self._scalars = list(scalars)
        self.added = []
        self.commits = 0
        self.flushes = 0

    async def scalars(self, stmt):
        return _Rows(self._scalars.pop(0) if self._scalars else [])

    async def scalar(self, stmt):
        return None

    async def execute(self, stmt):
        return _Rows([])

    async def get(self, model, pk):
        return None

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushes += 1
        # The database assigns primary keys on flush; mirror that for new rows.
        for obj in self.added:
            if hasattr(obj, "id") and getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None

    @asynccontextmanager
    async def begin_nested(self):
        yield self


class FakeMaker:
    """Stands in for the async session factory: ``async with Maker() as session``."""

    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *exc):
        return False


def _run(status=RunStatus.awaiting_approval, **overrides):
    base = dict(
        id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        organization_id=ORG,
        status=status,
        trigger=WorkflowTrigger.manual,
        triggered_by=USER,
        input={},
        output={"lead": "Ada"},
        error_message=None,
        steps_total=2,
        steps_completed=1,
        started_at=NOW,
        finished_at=None,
        created_at=NOW,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _workflow(**overrides):
    base = dict(
        id=uuid.uuid4(),
        organization_id=ORG,
        project_id=PROJECT,
        name="Follow-up",
        description=None,
        trigger_type=WorkflowTrigger.manual,
        trigger_config={},
        status=WorkflowStatus.active,
        created_by=USER,
        run_count=0,
        last_run_at=None,
        deleted_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ── human approval ───────────────────────────────────────────────────────────


@pytest.fixture
def approval_env(monkeypatch):
    env = SimpleNamespace(loop_calls=[], audits=[], session=FakeSession())
    monkeypatch.setattr(engine, "_maker", lambda: FakeMaker(env.session))
    monkeypatch.setattr(
        engine, "_audit_run", lambda wf, run, extra=None: env.audits.append(extra or {})
    )

    async def fake_loop(session, workflow, run, steps, context, *, start_index):
        env.loop_calls.append(start_index)

    monkeypatch.setattr(engine, "_run_loop", fake_loop)
    return env


def _paused_steps():
    run_id = uuid.uuid4()
    approval = WorkflowRunStep(
        run_id=run_id,
        step_id=uuid.uuid4(),
        order_index=0,
        type=StepType.approval,
        name="Manager sign-off",
        config={},
        status=RunStepStatus.awaiting_approval,
    )
    after = WorkflowRunStep(
        run_id=run_id,
        step_id=uuid.uuid4(),
        order_index=1,
        type=StepType.notification,
        name="Notify",
        config={},
        status=RunStepStatus.pending,
    )
    return [approval, after]


def test_approved_run_resumes_after_the_approval_step(approval_env, monkeypatch):
    steps = _paused_steps()
    run = _run()
    workflow = _workflow()
    monkeypatch.setattr(engine, "_load", _loader(run, workflow, steps))

    asyncio.run(engine.resume_run(run.id, approved=True, note="looks good"))

    assert steps[0].status == RunStepStatus.completed
    assert steps[0].output["decision"] == "approved"
    assert steps[0].output["note"] == "looks good"
    assert run.status == RunStatus.running
    assert run.steps_completed == 2
    assert approval_env.loop_calls == [1]


def test_rejected_run_is_cancelled_and_later_steps_never_run(approval_env, monkeypatch):
    steps = _paused_steps()
    run = _run()
    workflow = _workflow(run_count=4)
    monkeypatch.setattr(engine, "_load", _loader(run, workflow, steps))

    asyncio.run(engine.resume_run(run.id, approved=False, note="not today"))

    assert steps[0].status == RunStepStatus.skipped
    assert steps[0].output["decision"] == "rejected"
    assert steps[1].status == RunStepStatus.pending
    assert run.status == RunStatus.cancelled
    assert run.error_message.startswith("Rejected at approval step.")
    assert "not today" in run.error_message
    assert workflow.run_count == 5
    assert run.finished_at is not None
    assert approval_env.loop_calls == []
    assert approval_env.session.commits == 1


def test_a_run_that_is_not_waiting_cannot_be_resumed(approval_env, monkeypatch):
    steps = _paused_steps()
    run = _run(status=RunStatus.completed)
    monkeypatch.setattr(engine, "_load", _loader(run, _workflow(), steps))

    asyncio.run(engine.resume_run(run.id, approved=True))

    assert run.status == RunStatus.completed
    assert steps[0].status == RunStepStatus.awaiting_approval
    assert approval_env.loop_calls == []


def test_resuming_a_missing_run_does_nothing(approval_env, monkeypatch):
    monkeypatch.setattr(engine, "_load", _loader(None, None, []))
    asyncio.run(engine.resume_run(uuid.uuid4(), approved=True))
    assert approval_env.loop_calls == []


def test_reaching_an_approval_step_pauses_the_run_before_later_steps(monkeypatch):
    run = WorkflowRun(
        id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        organization_id=ORG,
        status=RunStatus.running,
        trigger=WorkflowTrigger.manual,
        input={},
        steps_total=2,
        steps_completed=0,
    )
    workflow = Workflow(
        id=run.workflow_id,
        organization_id=ORG,
        name="x",
        trigger_type=WorkflowTrigger.manual,
    )
    steps = _paused_steps()
    steps[0].status = RunStepStatus.pending
    steps[0].config = {"message": "Approve {{ lead }}?"}
    session = FakeSession()
    audits = []
    monkeypatch.setattr(
        engine, "_audit_run", lambda wf, r, extra=None: audits.append(extra)
    )

    asyncio.run(
        engine._run_loop(session, workflow, run, steps, {"lead": "Ada"}, start_index=0)
    )

    assert run.status == RunStatus.awaiting_approval
    assert steps[0].status == RunStepStatus.awaiting_approval
    assert steps[0].output["text"] == "Approve Ada?"
    assert steps[1].status == RunStepStatus.pending
    assert run.output == {"lead": "Ada"}
    assert audits == [{"paused": True}]


def _loader(run, workflow, steps):
    async def _load(session, run_id):
        return run, workflow, steps

    return _load


# ── event triggers ───────────────────────────────────────────────────────────


def test_unsupported_event_is_refused():
    with pytest.raises(ValueError):
        asyncio.run(
            triggers.fire_event(
                FakeSession(), organization_id=ORG, event="invoice.paid", event_id="1"
            )
        )


def _patch_triggers(monkeypatch, *, workflows, steps_by_wf, existing=()):
    async def fake_match(session, org, event, project):
        return workflows

    async def fake_lock(session, wid):
        return None

    async def fake_existing(session, org, wid, key):
        return uuid.uuid4() if (wid, key) in existing else None

    async def fake_steps(session, wid):
        return steps_by_wf.get(wid, [])

    monkeypatch.setattr(triggers, "_matching_workflows", fake_match)
    monkeypatch.setattr(triggers, "_lock_workflow", fake_lock)
    monkeypatch.setattr(triggers, "_existing_run_id", fake_existing)
    monkeypatch.setattr(triggers, "_steps_for", fake_steps)


def _step(order):
    return WorkflowStep(
        id=uuid.uuid4(),
        workflow_id=uuid.uuid4(),
        organization_id=ORG,
        order_index=order,
        type=StepType.notification,
        name=f"step {order}",
        config={},
    )


def test_event_creates_one_queued_run_per_matching_workflow_with_its_steps(monkeypatch):
    lead_id = "lead-1"
    wf_with_steps = _workflow(trigger_type=WorkflowTrigger.event)
    wf_without_steps = _workflow(trigger_type=WorkflowTrigger.event)
    _patch_triggers(
        monkeypatch,
        workflows=[wf_with_steps, wf_without_steps],
        steps_by_wf={wf_with_steps.id: [_step(0), _step(1)], wf_without_steps.id: []},
    )
    session = FakeSession()

    created = asyncio.run(
        triggers.fire_event(
            session,
            organization_id=ORG,
            event="lead.created",
            event_id=lead_id,
            payload={"source": None, "lead_id": lead_id},
        )
    )

    assert len(created) == 1
    runs = [o for o in session.added if isinstance(o, WorkflowRun)]
    run_steps = [o for o in session.added if isinstance(o, WorkflowRunStep)]
    assert len(runs) == 1
    assert runs[0].status == RunStatus.queued
    assert runs[0].trigger == WorkflowTrigger.event
    assert runs[0].input["event_key"] == f"lead.created:{lead_id}"
    assert "source" not in runs[0].input  # None payload values are dropped
    assert runs[0].steps_total == 2
    assert len(run_steps) == 2


def test_replayed_event_creates_no_second_run(monkeypatch):
    wf = _workflow(trigger_type=WorkflowTrigger.event)
    _patch_triggers(
        monkeypatch,
        workflows=[wf],
        steps_by_wf={wf.id: [_step(0)]},
        existing={(wf.id, "message.received:msg-9")},
    )
    session = FakeSession()

    created = asyncio.run(
        triggers.fire_event(
            session, organization_id=ORG, event="message.received", event_id="msg-9"
        )
    )

    assert created == []
    assert [o for o in session.added if isinstance(o, WorkflowRun)] == []


def test_inbound_message_fires_the_message_received_event_with_the_message_id(
    monkeypatch,
):
    seen = {}

    async def fake_fire(session, **kwargs):
        seen.update(kwargs)
        return [uuid.uuid4()]

    monkeypatch.setattr(triggers, "fire_event", fake_fire)
    conversation, message = uuid.uuid4(), uuid.uuid4()

    created = asyncio.run(
        triggers.fire_message_received(
            FakeSession(),
            organization_id=ORG,
            project_id=PROJECT,
            conversation_id=conversation,
            message_id=message,
        )
    )

    assert len(created) == 1
    assert seen["event"] == "message.received"
    assert seen["event_id"] == str(message)
    assert seen["payload"] == {
        "conversation_id": str(conversation),
        "message_id": str(message),
    }


def test_a_failing_trigger_is_logged_and_never_raised_to_the_caller(monkeypatch):
    async def boom(session, **kwargs):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(triggers, "fire_event", boom)
    lead = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=ORG,
        project_id=PROJECT,
        conversation_id=None,
        source="web",
    )

    assert asyncio.run(triggers.fire_lead_created(FakeSession(), lead)) == []


# ── schedule loop ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "cfg, expected",
    [
        ({"interval_minutes": 15}, 15),
        ({"interval_minutes": -5}, 1),
        ({"interval_minutes": "soon"}, None),
        ({"every": "daily"}, 1440),
        ({"every": " Hourly "}, 60),
        ({"every": "weekly"}, 10080),
        ({"every": "fortnightly"}, None),
        ({}, None),
        (None, None),
    ],
)
def test_schedule_interval_is_read_from_the_workflow_config(cfg, expected):
    assert scheduler._interval_minutes(cfg) == expected


def _scheduler_env(monkeypatch, *, workflows, steps_by_wf, scheduled=None):
    scheduled = [] if scheduled is None else scheduled
    # Scripted results in query order: the workflow scan first, then each workflow's steps.
    step_session = FakeSession(
        scalars=[workflows] + [steps_by_wf.get(w.id, []) for w in workflows]
    )
    monkeypatch.setattr(scheduler, "_maker", lambda: FakeMaker(step_session))

    async def fake_execute_run(run_id):
        scheduled.append(run_id)

    monkeypatch.setattr(scheduler, "execute_run", fake_execute_run)
    return step_session, scheduled


@pytest.mark.asyncio
async def test_due_scheduled_workflow_gets_one_queued_run_and_is_marked(monkeypatch):
    wf = _workflow(
        trigger_type=WorkflowTrigger.schedule,
        trigger_config={"every": "hourly"},
        last_run_at=NOW - timedelta(hours=2),
    )
    session, scheduled = _scheduler_env(
        monkeypatch, workflows=[wf], steps_by_wf={wf.id: [_step(0)]}
    )
    monkeypatch.setattr(scheduler, "_utcnow", lambda: NOW)

    await scheduler._tick()
    await asyncio.sleep(0)

    runs = [o for o in session.added if isinstance(o, WorkflowRun)]
    assert len(runs) == 1
    assert runs[0].trigger == WorkflowTrigger.schedule
    assert runs[0].status == RunStatus.queued
    assert wf.last_run_at == NOW
    assert session.commits == 1
    assert scheduled == [runs[0].id]


@pytest.mark.asyncio
async def test_workflow_that_ran_recently_is_not_fired_again(monkeypatch):
    wf = _workflow(
        trigger_type=WorkflowTrigger.schedule,
        trigger_config={"interval_minutes": 60},
        last_run_at=NOW - timedelta(minutes=10),
    )
    session, scheduled = _scheduler_env(
        monkeypatch, workflows=[wf], steps_by_wf={wf.id: [_step(0)]}
    )
    monkeypatch.setattr(scheduler, "_utcnow", lambda: NOW)

    await scheduler._tick()
    await asyncio.sleep(0)

    assert [o for o in session.added if isinstance(o, WorkflowRun)] == []
    assert session.commits == 0
    assert scheduled == []


@pytest.mark.asyncio
async def test_scheduled_workflow_without_steps_is_not_fired(monkeypatch):
    wf = _workflow(
        trigger_type=WorkflowTrigger.schedule,
        trigger_config={"every": "daily"},
        last_run_at=None,
    )
    session, scheduled = _scheduler_env(
        monkeypatch, workflows=[wf], steps_by_wf={wf.id: []}
    )
    monkeypatch.setattr(scheduler, "_utcnow", lambda: NOW)

    await scheduler._tick()
    await asyncio.sleep(0)

    assert [o for o in session.added if isinstance(o, WorkflowRun)] == []
    assert scheduled == []


@pytest.mark.asyncio
async def test_event_runs_are_dispatched_once_each(monkeypatch):
    run_ids = [uuid.uuid4(), uuid.uuid4()]
    session = FakeSession(scalars=[run_ids])
    monkeypatch.setattr(scheduler, "_maker", lambda: FakeMaker(session))
    scheduled = []

    async def fake_execute_run(run_id):
        scheduled.append(run_id)

    monkeypatch.setattr(scheduler, "execute_run", fake_execute_run)

    await scheduler._dispatch_queued_runs()
    await asyncio.sleep(0)

    assert sorted(scheduled, key=str) == sorted(run_ids, key=str)


@pytest.mark.asyncio
async def test_scheduler_start_is_idempotent_and_stop_is_clean(monkeypatch):
    async def idle_loop():
        await asyncio.sleep(3600)

    monkeypatch.setattr(scheduler, "_loop", idle_loop)
    monkeypatch.setattr(scheduler, "_task", None)

    scheduler.start_scheduler()
    first = scheduler._task
    scheduler.start_scheduler()
    assert scheduler._task is first

    await scheduler.stop_scheduler()
    assert first.cancelled() or first.done()
    await scheduler.stop_scheduler()  # stopping twice is harmless


# ── API guards ───────────────────────────────────────────────────────────────


class StoreRepo:
    """Organization-scoped in-memory repository used by the route tests."""

    store: dict = {}

    def __init__(self, session, organization_id, project_id=None):
        self.org = organization_id

    async def get(self, workflow_id):
        wf = self.store["workflows"].get(workflow_id)
        if wf is None or wf.organization_id != self.org or wf.deleted_at is not None:
            return None
        return wf

    async def steps_for(self, workflow_id):
        return self.store["steps"].get(workflow_id, [])

    async def get_run(self, run_id):
        run = self.store["runs"].get(run_id)
        if run is None or run.organization_id != self.org:
            return None
        return run

    async def run_steps_for(self, run_id):
        return []


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(wf_routes, "audit", lambda *a, **k: None)
    monkeypatch.setattr(wf_routes.usage_service, "enforce_quota", _noop_async)
    monkeypatch.setattr(wf_routes, "WorkflowRepository", StoreRepo)
    StoreRepo.store = {"workflows": {}, "steps": {}, "runs": {}}

    state = SimpleNamespace(
        role="admin", org=ORG, session=FakeSession(), resumed=[], executed=[]
    )

    async def _org():
        return OrgContext(
            user_id=USER,
            auth_subject="s",
            organization_id=state.org,
            membership_role=state.role,
        )

    async def _project():
        return ProjectContext(
            user_id=USER,
            organization_id=state.org,
            membership_role=state.role,
            project_id=PROJECT,
            project_slug="default",
            is_default_project=True,
        )

    async def recorder_resume(run_id, *, approved, note=""):
        state.resumed.append((run_id, approved))

    monkeypatch.setattr(wf_routes, "resume_run", recorder_resume)

    app = FastAPI()
    app.include_router(wf_routes.router)
    app.dependency_overrides[get_current_organization] = _org
    app.dependency_overrides[get_current_project] = _project
    app.dependency_overrides[get_db] = lambda: state.session
    state.client = TestClient(app)
    return state


async def _noop_async(*a, **k):
    return None


def test_member_cannot_create_a_workflow(api):
    api.role = "member"
    response = api.client.post("/api/workflows", json={"name": "x", "steps": []})
    assert response.status_code == 403


def test_unknown_trigger_is_refused(api):
    response = api.client.post(
        "/api/workflows", json={"name": "x", "trigger_type": "cron", "steps": []}
    )
    assert response.status_code == 422
    assert "Unknown trigger" in response.json()["detail"]


def test_event_trigger_must_name_a_supported_event(api):
    response = api.client.post(
        "/api/workflows",
        json={
            "name": "x",
            "trigger_type": "event",
            "trigger_config": {"event": "invoice.paid"},
            "steps": [],
        },
    )
    assert response.status_code == 422
    assert "lead.created" in response.json()["detail"]


def test_unknown_step_type_is_refused_before_anything_is_saved(api):
    response = api.client.post(
        "/api/workflows",
        json={"name": "x", "steps": [{"type": "teleport", "name": "beam"}]},
    )
    assert response.status_code == 422
    assert "Unknown step type" in response.json()["detail"]
    assert api.session.added == []


def test_workflow_from_another_organization_is_not_visible(api):
    foreign = _workflow(organization_id=OTHER_ORG)
    StoreRepo.store["workflows"][foreign.id] = foreign
    response = api.client.get(f"/api/workflows/{foreign.id}")
    assert response.status_code == 404


def test_delete_soft_deletes_only_the_callers_workflow(api):
    own = _workflow()
    foreign = _workflow(organization_id=OTHER_ORG)
    StoreRepo.store["workflows"].update({own.id: own, foreign.id: foreign})

    refused = api.client.delete(f"/api/workflows/{foreign.id}")
    assert refused.status_code == 404
    assert foreign.deleted_at is None

    accepted = api.client.delete(f"/api/workflows/{own.id}")
    assert accepted.status_code == 200
    assert accepted.json() == {"deleted": True}
    assert own.deleted_at is not None


def test_running_a_workflow_with_no_steps_is_refused(api):
    wf = _workflow()
    StoreRepo.store["workflows"][wf.id] = wf
    response = api.client.post(f"/api/workflows/{wf.id}/run", json={"input": {}})
    assert response.status_code == 400
    assert response.json()["detail"] == "Workflow has no steps."


def test_deciding_on_a_run_that_is_not_waiting_is_a_conflict(api):
    run = _run(status=RunStatus.completed)
    StoreRepo.store["runs"][run.id] = run
    response = api.client.post(
        f"/api/workflows/runs/{run.id}/decision", json={"decision": "approve"}
    )
    assert response.status_code == 409


def test_decision_must_be_approve_or_reject(api):
    run = _run(status=RunStatus.awaiting_approval)
    StoreRepo.store["runs"][run.id] = run
    response = api.client.post(
        f"/api/workflows/runs/{run.id}/decision", json={"decision": "maybe"}
    )
    assert response.status_code == 422
    assert api.resumed == []


def test_approving_a_waiting_run_resumes_it_in_the_background(api):
    run = _run(status=RunStatus.awaiting_approval)
    StoreRepo.store["runs"][run.id] = run
    response = api.client.post(
        f"/api/workflows/runs/{run.id}/decision",
        json={"decision": "approve", "note": "ok"},
    )
    assert response.status_code == 200
    assert api.resumed == [(run.id, True)]


def test_a_member_cannot_decide_on_an_approval(api):
    api.role = "member"
    run = _run(status=RunStatus.awaiting_approval)
    StoreRepo.store["runs"][run.id] = run
    response = api.client.post(
        f"/api/workflows/runs/{run.id}/decision", json={"decision": "approve"}
    )
    assert response.status_code == 403
    assert api.resumed == []


def test_another_organization_cannot_decide_on_a_run(api):
    run = _run(status=RunStatus.awaiting_approval, organization_id=OTHER_ORG)
    StoreRepo.store["runs"][run.id] = run
    response = api.client.post(
        f"/api/workflows/runs/{run.id}/decision", json={"decision": "approve"}
    )
    assert response.status_code == 404
    assert api.resumed == []
