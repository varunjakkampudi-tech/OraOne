"""Event triggers for workflows: ``lead.created`` and ``message.received``.

An event creates one queued run per matching active workflow, inside the
caller's transaction, so the run commits together with the event that caused
it. The workflow scheduler executes queued event runs (see
``workflow_scheduler``) and claims each one atomically, so a run executes once.

Authoring: a workflow with ``trigger_type = event`` and
``trigger_config = {"event": "lead.created"}`` (or ``"message.received"``).

Idempotency: a run is keyed by workflow id and ``event_key``, which is
``"<event>:<event id>"``. The workflow row is locked before the existence check,
so two deliveries of the same event serialise and only one run is created.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.workflow import (
    RunStatus,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTrigger,
)

log = logging.getLogger("app.workflow.triggers")

SUPPORTED_EVENTS = ("lead.created", "message.received")


# ───────────────────────── statements (org-scoped) ─────────────────────────


def matching_workflows_stmt(
    organization_id: uuid.UUID, event: str, project_id: Optional[uuid.UUID]
):
    stmt = select(Workflow).where(
        Workflow.organization_id == organization_id,
        Workflow.status == WorkflowStatus.active,
        Workflow.trigger_type == WorkflowTrigger.event,
        Workflow.trigger_config["event"].astext == event,
        Workflow.deleted_at.is_(None),
    )
    if project_id is not None:
        stmt = stmt.where(
            or_(Workflow.project_id.is_(None), Workflow.project_id == project_id)
        )
    return stmt


def existing_event_run_stmt(
    organization_id: uuid.UUID, workflow_id: uuid.UUID, event_key: str
):
    return (
        select(WorkflowRun.id)
        .where(
            WorkflowRun.organization_id == organization_id,
            WorkflowRun.workflow_id == workflow_id,
            WorkflowRun.input["event_key"].astext == event_key,
        )
        .limit(1)
    )


# ───────────────────────── database access ─────────────────────────


async def _matching_workflows(
    session: AsyncSession,
    organization_id: uuid.UUID,
    event: str,
    project_id: Optional[uuid.UUID],
) -> list[Workflow]:
    return list(
        (
            await session.scalars(
                matching_workflows_stmt(organization_id, event, project_id)
            )
        ).all()
    )


async def _lock_workflow(session: AsyncSession, workflow_id: uuid.UUID) -> None:
    await session.execute(
        select(Workflow.id).where(Workflow.id == workflow_id).with_for_update()
    )


async def _existing_run_id(
    session: AsyncSession,
    organization_id: uuid.UUID,
    workflow_id: uuid.UUID,
    event_key: str,
) -> Optional[uuid.UUID]:
    return await session.scalar(
        existing_event_run_stmt(organization_id, workflow_id, event_key)
    )


async def _steps_for(
    session: AsyncSession, workflow_id: uuid.UUID
) -> list[WorkflowStep]:
    return list(
        (
            await session.scalars(
                select(WorkflowStep)
                .where(WorkflowStep.workflow_id == workflow_id)
                .order_by(WorkflowStep.order_index)
            )
        ).all()
    )


# ───────────────────────── public API ─────────────────────────


async def fire_event(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    event: str,
    event_id: str,
    project_id: Optional[uuid.UUID] = None,
    payload: Optional[dict[str, Any]] = None,
) -> list[uuid.UUID]:
    """Create one queued run per matching workflow. The caller commits.

    Returns the ids of the runs created. A repeat call with the same event id
    creates nothing.
    """
    if event not in SUPPORTED_EVENTS:
        raise ValueError(f"Unsupported workflow event '{event}'.")
    event_key = f"{event}:{event_id}"
    created: list[uuid.UUID] = []

    for workflow in await _matching_workflows(
        session, organization_id, event, project_id
    ):
        await _lock_workflow(session, workflow.id)
        if await _existing_run_id(session, organization_id, workflow.id, event_key):
            continue
        steps = await _steps_for(session, workflow.id)
        if not steps:
            continue

        run_input: dict[str, Any] = {"event": event, "event_key": event_key}
        run_input.update({k: v for k, v in (payload or {}).items() if v is not None})
        run = WorkflowRun(
            workflow_id=workflow.id,
            organization_id=organization_id,
            status=RunStatus.queued,
            trigger=WorkflowTrigger.event,
            triggered_by=None,
            input=run_input,
            steps_total=len(steps),
        )
        session.add(run)
        await session.flush()
        for step in steps:
            session.add(
                WorkflowRunStep(
                    run_id=run.id,
                    organization_id=organization_id,
                    step_id=step.id,
                    order_index=step.order_index,
                    type=step.type,
                    name=step.name,
                    config=step.config or {},
                )
            )
        created.append(run.id)
    if created:
        await session.flush()
    return created


async def _fire_guarded(session: AsyncSession, **kwargs: Any) -> list[uuid.UUID]:
    """Record an event inside a savepoint. A trigger failure never blocks the
    lead or message that caused it."""
    try:
        async with session.begin_nested():
            return await fire_event(session, **kwargs)
    except Exception:  # noqa: BLE001
        log.exception("workflow event %s could not be recorded", kwargs.get("event"))
        return []


async def fire_lead_created(session: AsyncSession, lead: Any) -> list[uuid.UUID]:
    """Call after a Lead is flushed (create_lead, import commit)."""
    return await _fire_guarded(
        session,
        organization_id=lead.organization_id,
        event="lead.created",
        event_id=str(lead.id),
        project_id=lead.project_id,
        payload={
            "lead_id": str(lead.id),
            "conversation_id": str(lead.conversation_id)
            if lead.conversation_id
            else None,
            "source": lead.source,
        },
    )


async def fire_message_received(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    project_id: Optional[uuid.UUID],
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Call after an inbound customer message is flushed."""
    return await _fire_guarded(
        session,
        organization_id=organization_id,
        project_id=project_id,
        event="message.received",
        event_id=str(message_id),
        payload={
            "conversation_id": str(conversation_id),
            "message_id": str(message_id),
        },
    )
