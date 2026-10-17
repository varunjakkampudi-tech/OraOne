"""Workflow engine completion: triggers, durable waits, send/create_task steps.

No database is used. The engine's data access goes through a small fake
session, and every external send goes through a recording fake sender.
Organization isolation is checked on the compiled SQL of the statements that
select workflows and runs.
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql

from app.database.models.collaboration import Task
from app.database.models.lead import Lead, LeadStatus, LeadTemperature
from app.database.models.workflow import (
    RunStatus,
    RunStepStatus,
    StepType,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStatus,
    WorkflowTrigger,
)
from app.services import workflow_engine as engine
from app.services import workflow_triggers as triggers

DAYTIME = datetime(2026, 10, 17, 14, 0, tzinfo=timezone.utc)  # 15:00 in London


# ───────────────────────── fakes ─────────────────────────


class FakeSession:
    """Records adds and commits. Assigns ids on flush, as the real ORM does."""

    def __init__(self, rowcount: int = 1) -> None:
        self.added: list = []
        self.commits = 0
        self.rowcount = rowcount
        self.executed: list = []

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None and hasattr(obj, "__table__"):
                obj.id = uuid.uuid4()

    def add(self, obj) -> None:
        self.added.append(obj)

    async def execute(self, stmt):
        self.executed.append(stmt)
        return SimpleNamespace(rowcount=self.rowcount)

    async def scalar(self, stmt):
        return None

    @asynccontextmanager
    async def begin_nested(self):
        yield self


class RecordingSender:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self.error = error

    async def send(self, *, channel, recipient, text, organization_id, lead_id):
        if self.error is not None:
            raise self.error
        self.calls.append(
            {
                "channel": channel,
                "recipient": recipient,
                "text": text,
                "organization_id": organization_id,
                "lead_id": lead_id,
            }
        )


@pytest.fixture(autouse=True)
def _quiet_engine(monkeypatch):
    """Fixed daytime clock, no audit writes, no real sleeps, no attempt history."""
    monkeypatch.setattr(engine, "_utcnow", lambda: DAYTIME)
    monkeypatch.setattr(engine, "_audit_run", lambda *a, **k: None)

    async def no_history(*_args, **_kwargs):
        return 0

    async def no_inbound(*_args, **_kwargs):
        return None

    monkeypatch.setattr(engine, "_attempts_last_24h", no_history)
    monkeypatch.setattr(engine, "_last_inbound_at", no_inbound)
    yield
    engine.unregister_outbound_sender("whatsapp")
    engine.unregister_outbound_sender("email")


def _org() -> uuid.UUID:
    return uuid.uuid4()


def _workflow(org_id: uuid.UUID, event: str = "lead.created") -> Workflow:
    return Workflow(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Follow up",
        status=WorkflowStatus.active,
        trigger_type=WorkflowTrigger.event,
        trigger_config={"event": event},
        run_count=0,
        success_count=0,
        created_by=None,
    )


def _lead(org_id: uuid.UUID, **overrides) -> Lead:
    values = dict(
        id=uuid.uuid4(),
        organization_id=org_id,
        project_id=None,
        conversation_id=None,
        name="Ada Lovelace",
        email="ada@example.com",
        phone="+447700900123",
        company=None,
        intent=None,
        source="widget",
        status=LeadStatus.new,
        temperature=LeadTemperature.hot,
        score=80,
        extra={"consent": "granted", "timezone": "Europe/London"},
    )
    values.update(overrides)
    return Lead(**values)


def _run_with_steps(workflow: Workflow, step_defs: list[tuple[str, str, dict]]):
    """Build an in-memory run and its step rows from (type, name, config) triples."""
    run = WorkflowRun(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        organization_id=workflow.organization_id,
        status=RunStatus.running,
        trigger=WorkflowTrigger.event,
        input={},
        output={},
        steps_total=len(step_defs),
        steps_completed=0,
    )
    steps = []
    for index, (stype, name, config) in enumerate(step_defs):
        steps.append(
            WorkflowRunStep(
                id=uuid.uuid4(),
                run_id=run.id,
                organization_id=workflow.organization_id,
                order_index=index,
                type=StepType(stype),
                name=name,
                status=RunStepStatus.pending,
                config=config,
                input={},
                output={},
            )
        )
    return run, steps


def _sql_params(stmt) -> set[str]:
    return {str(v) for v in stmt.compile(dialect=postgresql.dialect()).params.values()}


# ───────────────────────── triggers ─────────────────────────


async def test_lead_created_fires_one_run_and_repeat_delivery_creates_nothing(
    monkeypatch,
):
    org = _org()
    workflow = _workflow(org)
    steps = [
        SimpleNamespace(
            id=uuid.uuid4(),
            order_index=0,
            type=StepType.transform,
            name="t",
            config={"template": "hi", "output_var": "x"},
        ),
    ]

    async def matching(_session, organization_id, event, project_id):
        assert organization_id == org and event == "lead.created"
        return [workflow]

    async def lock(_session, _workflow_id):
        return None

    async def steps_for(_session, _workflow_id):
        return steps

    async def existing(_session, organization_id, workflow_id, event_key):
        for obj in session.added:
            if (
                isinstance(obj, WorkflowRun)
                and obj.workflow_id == workflow_id
                and obj.input.get("event_key") == event_key
            ):
                return obj.id
        return None

    monkeypatch.setattr(triggers, "_matching_workflows", matching)
    monkeypatch.setattr(triggers, "_lock_workflow", lock)
    monkeypatch.setattr(triggers, "_steps_for", steps_for)
    monkeypatch.setattr(triggers, "_existing_run_id", existing)

    session = FakeSession()
    lead = _lead(org)
    first = await triggers.fire_lead_created(session, lead)
    second = await triggers.fire_lead_created(session, lead)

    runs = [o for o in session.added if isinstance(o, WorkflowRun)]
    assert len(first) == 1 and second == []
    assert len(runs) == 1
    assert runs[0].trigger == WorkflowTrigger.event
    assert runs[0].status == RunStatus.queued
    assert runs[0].input["event_key"] == f"lead.created:{lead.id}"
    assert runs[0].input["lead_id"] == str(lead.id)


async def test_trigger_failure_does_not_block_the_lead(monkeypatch):
    async def broken(*_args, **_kwargs):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(triggers, "_matching_workflows", broken)
    lead = _lead(_org())
    assert await triggers.fire_lead_created(FakeSession(), lead) == []


def test_matching_workflows_query_is_scoped_to_the_event_org():
    org_a, org_b = _org(), _org()
    params = _sql_params(
        triggers.matching_workflows_stmt(org_a, "message.received", None)
    )
    assert str(org_a) in params
    assert str(org_b) not in params
    assert "message.received" in params


def test_run_idempotency_query_is_scoped_to_the_run_org():
    org_a, org_b = _org(), _org()
    workflow_id = uuid.uuid4()
    params = _sql_params(
        triggers.existing_event_run_stmt(org_a, workflow_id, "lead.created:x")
    )
    assert str(org_a) in params
    assert str(org_b) not in params


# ───────────────────────── durable waits ─────────────────────────


async def test_wait_schedules_a_resume_point_and_never_sleeps(monkeypatch):
    async def no_sleep(*_args, **_kwargs):
        raise AssertionError("a wait step must not sleep")

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    org = _org()
    workflow = _workflow(org)
    run, steps = _run_with_steps(
        workflow,
        [
            ("delay", "wait an hour", {"hours": 1}),
            ("transform", "after", {"template": "done", "output_var": "done"}),
        ],
    )
    session = FakeSession()
    await engine._run_loop(session, workflow, run, steps, {}, start_index=0)

    wait = steps[0]
    assert run.status == RunStatus.running
    assert wait.status == RunStepStatus.running
    assert wait.output["waiting"] is True
    resume_at = datetime.fromisoformat(wait.output["resume_at"])
    assert resume_at == DAYTIME + timedelta(hours=1)
    assert steps[1].status == RunStepStatus.pending  # not executed yet

    assert engine._wait_is_due(wait, DAYTIME + timedelta(minutes=59)) is False
    assert engine._wait_is_due(wait, DAYTIME + timedelta(hours=1, seconds=1)) is True


async def test_resumed_wait_continues_with_the_checkpointed_context(monkeypatch):
    org = _org()
    workflow = _workflow(org)
    run, steps = _run_with_steps(
        workflow,
        [
            ("delay", "wait", {"seconds": 60}),
            ("transform", "after", {"template": "hello {{who}}", "output_var": "msg"}),
        ],
    )
    session = FakeSession()
    await engine._run_loop(session, workflow, run, steps, {"who": "Ada"}, start_index=0)

    # What resume_wait does after its atomic claim: mark the wait done, then go on.
    steps[0].status = RunStepStatus.completed
    checkpoint = dict(run.output)
    await engine._run_loop(session, workflow, run, steps, checkpoint, start_index=1)

    assert steps[1].status == RunStepStatus.completed
    assert steps[1].output["value"] == "hello Ada"
    assert run.status == RunStatus.completed


def test_wait_bounds_are_enforced():
    assert engine._wait_seconds({"hours": 1}) == 3600
    with pytest.raises(ValueError):
        engine._wait_seconds({"days": 31})
    with pytest.raises(ValueError):
        engine._wait_seconds({"minutes": "soon"})


# ───────────────────────── send_message ─────────────────────────


async def _run_send(
    monkeypatch, lead: Lead, cfg: dict, session: FakeSession | None = None
):
    org = lead.organization_id

    async def load_lead(_session, _workflow, _context):
        return lead

    monkeypatch.setattr(engine, "_load_lead", load_lead)
    workflow = _workflow(org)
    run, steps = _run_with_steps(
        workflow, [("notification", "send", {"action": "send_message", **cfg})]
    )
    session = session or FakeSession()
    await engine._run_loop(session, workflow, run, steps, {}, start_index=0)
    return run, steps[0]


async def test_send_is_skipped_with_a_reason_when_consent_is_not_given(monkeypatch):
    sender = RecordingSender()
    engine.register_outbound_sender("whatsapp", sender)
    lead = _lead(_org(), extra={"consent": "unknown", "timezone": "Europe/London"})

    run, step = await _run_send(
        monkeypatch, lead, {"channel": "whatsapp", "message": "Hi {{lead.name}}"}
    )

    assert sender.calls == []
    assert step.status == RunStepStatus.skipped
    assert "consent" in step.output["reason"].lower()
    assert step.output["dispatched"] is False
    assert run.status == RunStatus.completed  # a consent skip does not fail the run


async def test_withdrawn_consent_is_skipped(monkeypatch):
    sender = RecordingSender()
    engine.register_outbound_sender("whatsapp", sender)
    lead = _lead(_org(), extra={"consent": "denied", "timezone": "Europe/London"})
    _run, step = await _run_send(
        monkeypatch, lead, {"channel": "whatsapp", "message": "Hi"}
    )
    assert step.status == RunStepStatus.skipped
    assert sender.calls == []


async def test_send_fails_plainly_when_no_adapter_is_configured(monkeypatch):
    lead = _lead(_org())  # consent granted, so only the missing adapter can stop it
    run, step = await _run_send(
        monkeypatch, lead, {"channel": "whatsapp", "message": "Hi {{lead.name}}"}
    )

    assert step.status == RunStepStatus.failed
    assert "No outbound adapter is configured for whatsapp" in step.error_message
    assert step.output["dispatched"] is False
    assert run.status == RunStatus.failed


async def test_send_reaches_the_registered_sender_once(monkeypatch):
    sender = RecordingSender()
    engine.register_outbound_sender("whatsapp", sender)
    org = _org()
    lead = _lead(org)
    run, step = await _run_send(
        monkeypatch, lead, {"channel": "whatsapp", "message": "Hi {{lead.name}}"}
    )

    assert step.status == RunStepStatus.completed
    assert step.output["sent"] is True
    assert len(sender.calls) == 1
    assert sender.calls[0]["recipient"] == "+447700900123"
    assert sender.calls[0]["text"] == "Hi Ada Lovelace"
    assert sender.calls[0]["organization_id"] == org
    assert run.status == RunStatus.completed


async def test_provider_error_is_reported_as_a_failure_without_its_detail(monkeypatch):
    engine.register_outbound_sender(
        "whatsapp", RecordingSender(error=RuntimeError("secret token abc123"))
    )
    run, step = await _run_send(
        monkeypatch, _lead(_org()), {"channel": "whatsapp", "message": "Hi"}
    )
    assert step.status == RunStepStatus.failed
    assert "did not accept" in step.error_message
    assert "abc123" not in step.error_message
    assert run.status == RunStatus.failed


async def test_send_needs_a_lead_and_says_so(monkeypatch):
    org = _org()

    async def no_lead(_session, _workflow, _context):
        return None

    monkeypatch.setattr(engine, "_load_lead", no_lead)
    workflow = _workflow(org)
    run, steps = _run_with_steps(
        workflow,
        [
            (
                "notification",
                "send",
                {"action": "send_message", "channel": "email", "message": "Hi"},
            )
        ],
    )
    await engine._run_loop(FakeSession(), workflow, run, steps, {}, start_index=0)
    assert steps[0].status == RunStepStatus.failed
    assert "no lead attached" in steps[0].error_message


# ───────────────────────── condition branch ─────────────────────────


async def test_condition_not_met_skips_the_rest_with_a_reason(monkeypatch):
    org = _org()
    lead = _lead(org, temperature=LeadTemperature.cold)

    async def load_lead(_session, _workflow, _context):
        return lead

    monkeypatch.setattr(engine, "_load_lead", load_lead)
    workflow = _workflow(org)
    run, steps = _run_with_steps(
        workflow,
        [
            (
                "condition",
                "only hot leads",
                {
                    "left": "{{lead.temperature}}",
                    "op": "eq",
                    "right": "hot",
                },
            ),
            ("transform", "after", {"template": "x", "output_var": "x"}),
        ],
    )
    await engine._run_loop(FakeSession(), workflow, run, steps, {}, start_index=0)

    assert steps[0].status == RunStepStatus.completed
    assert steps[0].output["passed"] is False
    assert steps[1].status == RunStepStatus.skipped
    assert "condition" in steps[1].output["reason"].lower()
    assert run.status == RunStatus.completed


async def test_condition_met_lets_the_next_step_run(monkeypatch):
    org = _org()
    lead = _lead(org, temperature=LeadTemperature.hot)

    async def load_lead(_session, _workflow, _context):
        return lead

    monkeypatch.setattr(engine, "_load_lead", load_lead)
    workflow = _workflow(org)
    run, steps = _run_with_steps(
        workflow,
        [
            (
                "condition",
                "only hot leads",
                {
                    "left": "{{lead.temperature}}",
                    "op": "eq",
                    "right": "hot",
                },
            ),
            ("transform", "after", {"template": "go", "output_var": "x"}),
        ],
    )
    await engine._run_loop(FakeSession(), workflow, run, steps, {}, start_index=0)

    assert steps[0].output["passed"] is True
    assert steps[1].status == RunStepStatus.completed
    assert run.status == RunStatus.completed


# ───────────────────────── create_task ─────────────────────────


async def test_create_task_writes_a_task_in_the_workflow_org(monkeypatch):
    org = _org()
    lead = _lead(org, name="Ada")

    async def load_lead(_session, _workflow, _context):
        return lead

    monkeypatch.setattr(engine, "_load_lead", load_lead)
    workflow = _workflow(org)
    run, steps = _run_with_steps(
        workflow,
        [
            (
                "transform",
                "task",
                {"action": "create_task", "title": "Call {{lead.name}}"},
            )
        ],
    )
    session = FakeSession()
    await engine._run_loop(session, workflow, run, steps, {}, start_index=0)

    tasks = [o for o in session.added if isinstance(o, Task)]
    assert len(tasks) == 1
    assert tasks[0].organization_id == org
    assert tasks[0].title == "Call Ada"
    assert tasks[0].resource_type == "lead"
    assert tasks[0].resource_id == str(lead.id)
    assert steps[0].status == RunStepStatus.completed
    assert run.status == RunStatus.completed


# ───────────────────────── step authoring and claims ─────────────────────────


def test_authored_action_types_are_stored_as_existing_step_types():
    assert engine.normalise_step_type("wait", {"hours": 1}) == (
        StepType.delay,
        {"hours": 1},
    )
    assert engine.normalise_step_type("send_message", {"message": "x"}) == (
        StepType.notification,
        {"message": "x", "action": "send_message"},
    )
    assert engine.normalise_step_type("create_task", {"title": "t"}) == (
        StepType.transform,
        {"title": "t", "action": "create_task"},
    )
    assert engine.normalise_step_type("condition", {}) == (StepType.condition, {})
    with pytest.raises(ValueError):
        engine.normalise_step_type("teleport", {})


async def test_a_run_that_is_not_queued_is_never_loaded_or_executed(monkeypatch):
    async def must_not_load(*_args, **_kwargs):
        raise AssertionError("an already-claimed run must not be loaded")

    monkeypatch.setattr(engine, "_load", must_not_load)
    await engine._start(FakeSession(rowcount=0), uuid.uuid4())


async def test_a_queued_run_is_claimed_once(monkeypatch):
    assert await engine._claim_queued_run(FakeSession(rowcount=1), uuid.uuid4()) is True
    assert (
        await engine._claim_queued_run(FakeSession(rowcount=0), uuid.uuid4()) is False
    )
