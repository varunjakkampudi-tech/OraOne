"""Workflow Automation API (Phase 11).

OraOne workflows chain the org's own AI, knowledge bases and agents into
repeatable automations. Authors define an ordered list of steps; runs
execute them sequentially and record a per-step timeline.

Endpoints
---------
* ``GET    /api/workflows``                  — list workflows
* ``POST   /api/workflows``                  — create (with steps)
* ``GET    /api/workflows/{id}``             — workflow + steps
* ``PATCH  /api/workflows/{id}``             — update (optionally replace steps)
* ``DELETE /api/workflows/{id}``             — soft-delete
* ``POST   /api/workflows/{id}/run``         — trigger a run (background)
* ``GET    /api/workflows/{id}/runs``        — recent runs for a workflow
* ``GET    /api/workflows/runs/{run_id}``    — one run + its step timeline

Tenant-safe: every read/write is scoped to the caller's organization.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.workflow import (
    RunStatus,
    StepType,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStatus,
    WorkflowStep,
    WorkflowTrigger,
    WorkflowVersion,
)
from app.database.repositories.workflow_repository import WorkflowRepository
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_role,
)
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.workflows import (
    ApprovalDecision,
    RunDetail,
    RunListResponse,
    RunRead,
    RunRequest,
    RunStepRead,
    StepCreate,
    StepRead,
    WorkflowAnalytics,
    WorkflowCreate,
    WorkflowDetail,
    WorkflowListResponse,
    WorkflowRead,
    WorkflowUpdate,
    WorkflowVersionListResponse,
    WorkflowVersionRead,
)
from app.services.audit import audit
from app.services import usage_service
from app.services.workflow_engine import execute_run, resume_run

log = logging.getLogger("app.workflows")

router = APIRouter(tags=["workflows"])

_VALID_STEP_TYPES = {t.value for t in StepType}
_VALID_TRIGGERS = {t.value for t in WorkflowTrigger}
_VALID_STATUSES = {s.value for s in WorkflowStatus}


def _repo(session: AsyncSession, ctx: OrgContext) -> WorkflowRepository:
    return WorkflowRepository(session, ctx.organization_id)


def _validate_step(step: StepCreate) -> None:
    if step.type not in _VALID_STEP_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown step type '{step.type}'. Allowed: {sorted(_VALID_STEP_TYPES)}",
        )


def _detail(workflow: Workflow, steps: list[WorkflowStep]) -> WorkflowDetail:
    data = WorkflowRead.model_validate(workflow).model_dump()
    data["steps"] = [StepRead.model_validate(s) for s in steps]
    return WorkflowDetail(**data)


def _snapshot(workflow: Workflow, steps: list[WorkflowStep]) -> dict:
    """Capture a workflow definition for the version history."""
    return {
        "name": workflow.name,
        "description": workflow.description,
        "trigger_type": workflow.trigger_type.value
        if hasattr(workflow.trigger_type, "value")
        else str(workflow.trigger_type),
        "trigger_config": dict(workflow.trigger_config or {}),
        "steps": [
            {
                "type": s.type.value if hasattr(s.type, "value") else str(s.type),
                "name": s.name,
                "config": dict(s.config or {}),
                "order_index": s.order_index,
            }
            for s in steps
        ],
    }


# ─────────────────── list / create ───────────────────

@router.get("/api/workflows", response_model=WorkflowListResponse, summary="List workflows")
async def list_workflows(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> WorkflowListResponse:
    ctx = pctx.org
    repo = WorkflowRepository(session, ctx.organization_id, pctx.project_id)
    rows = await repo.list(limit=limit, offset=offset)
    total = await repo.count()
    return WorkflowListResponse(
        items=[WorkflowRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/api/workflows",
    response_model=WorkflowDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workflow",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def create_workflow(
    payload: WorkflowCreate,
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> WorkflowDetail:
    ctx = pctx.org
    if payload.trigger_type not in _VALID_TRIGGERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown trigger '{payload.trigger_type}'.",
        )
    for step in payload.steps:
        _validate_step(step)

    # Phase 12 Module 2: enforce the plan's workflow quota before creating.
    await usage_service.enforce_quota(session, ctx.organization_id, "workflows")

    workflow = Workflow(
        organization_id=ctx.organization_id,
        project_id=pctx.project_id,
        name=payload.name.strip(),
        description=payload.description,
        trigger_type=WorkflowTrigger(payload.trigger_type),
        trigger_config=payload.trigger_config or {},
        created_by=ctx.user_id,
    )
    session.add(workflow)
    await session.flush()

    steps = _materialise_steps(workflow, ctx.organization_id, payload.steps)
    for s in steps:
        session.add(s)
    await session.commit()
    await session.refresh(workflow)

    audit(
        "create",
        resource="workflow",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(workflow.id),
        after={"name": workflow.name, "steps": len(steps)},
    )
    return _detail(workflow, steps)


# ─────────────────── analytics ───────────────────

@router.get(
    "/api/workflows/analytics",
    response_model=WorkflowAnalytics,
    summary="Workflow analytics for the organization",
)
async def workflow_analytics(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WorkflowAnalytics:
    repo = _repo(session, ctx)
    data = await repo.analytics()
    return WorkflowAnalytics(**data)


# ─────────────────── retrieve / update / delete ───────────────────

@router.get("/api/workflows/{workflow_id}", response_model=WorkflowDetail, summary="Get a workflow")
async def get_workflow(
    workflow_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WorkflowDetail:
    repo = _repo(session, ctx)
    workflow = await repo.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    steps = await repo.steps_for(workflow_id)
    return _detail(workflow, steps)


@router.patch(
    "/api/workflows/{workflow_id}",
    response_model=WorkflowDetail,
    summary="Update a workflow",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def update_workflow(
    workflow_id: uuid.UUID,
    payload: WorkflowUpdate,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WorkflowDetail:
    repo = _repo(session, ctx)
    workflow = await repo.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")

    # Snapshot the current definition into version history before mutating.
    current_steps = await repo.steps_for(workflow_id)
    version_no = await repo.next_version_number(workflow_id)
    session.add(
        WorkflowVersion(
            workflow_id=workflow.id,
            organization_id=ctx.organization_id,
            version=version_no,
            snapshot=_snapshot(workflow, current_steps),
            created_by=ctx.user_id,
        )
    )

    if payload.name is not None:
        workflow.name = payload.name.strip()
    if payload.description is not None:
        workflow.description = payload.description
    if payload.status is not None:
        if payload.status not in _VALID_STATUSES:
            raise HTTPException(status_code=422, detail=f"Unknown status '{payload.status}'.")
        workflow.status = WorkflowStatus(payload.status)
    if payload.trigger_type is not None:
        if payload.trigger_type not in _VALID_TRIGGERS:
            raise HTTPException(status_code=422, detail=f"Unknown trigger '{payload.trigger_type}'.")
        workflow.trigger_type = WorkflowTrigger(payload.trigger_type)
    if payload.trigger_config is not None:
        workflow.trigger_config = payload.trigger_config

    if payload.steps is not None:
        for step in payload.steps:
            _validate_step(step)
        # Replace the whole step list (delete-orphan handles removal).
        existing = await repo.steps_for(workflow_id)
        for s in existing:
            await session.delete(s)
        await session.flush()
        for s in _materialise_steps(workflow, ctx.organization_id, payload.steps):
            session.add(s)

    await session.commit()
    await session.refresh(workflow)
    steps = await repo.steps_for(workflow_id)

    audit(
        "update",
        resource="workflow",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(workflow.id),
    )
    return _detail(workflow, steps)


@router.delete(
    "/api/workflows/{workflow_id}",
    summary="Delete a workflow",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def delete_workflow(
    workflow_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from datetime import datetime, timezone

    repo = _repo(session, ctx)
    workflow = await repo.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    workflow.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    audit(
        "delete",
        resource="workflow",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(workflow_id),
    )
    return {"deleted": True}


# ─────────────────── run ───────────────────

@router.post(
    "/api/workflows/{workflow_id}/run",
    response_model=RunRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a workflow run",
    dependencies=[Depends(require_role("owner", "admin", "member"))],
)
async def run_workflow(
    workflow_id: uuid.UUID,
    payload: RunRequest,
    background: BackgroundTasks,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> RunRead:
    repo = _repo(session, ctx)
    workflow = await repo.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    steps = await repo.steps_for(workflow_id)
    if not steps:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow has no steps.")

    run = WorkflowRun(
        workflow_id=workflow.id,
        organization_id=ctx.organization_id,
        status=RunStatus.queued,
        trigger=WorkflowTrigger.manual,
        triggered_by=ctx.user_id,
        input=payload.input or {},
        steps_total=len(steps),
    )
    session.add(run)
    await session.flush()

    for step in steps:
        session.add(
            WorkflowRunStep(
                run_id=run.id,
                organization_id=ctx.organization_id,
                step_id=step.id,
                order_index=step.order_index,
                type=step.type,
                name=step.name,
                config=step.config or {},
            )
        )
    await session.commit()
    await session.refresh(run)

    background.add_task(execute_run, run.id)

    audit(
        "run",
        resource="workflow",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(workflow.id),
        meta={"run_id": str(run.id)},
    )
    return RunRead.model_validate(run)


@router.get(
    "/api/workflows/{workflow_id}/runs",
    response_model=RunListResponse,
    summary="List runs for a workflow",
)
async def list_runs(
    workflow_id: uuid.UUID,
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> RunListResponse:
    repo = _repo(session, ctx)
    workflow = await repo.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    rows = await repo.list_runs(workflow_id=workflow_id, limit=limit, offset=offset)
    total = await repo.count_runs(workflow_id=workflow_id)
    return RunListResponse(
        items=[RunRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/api/workflows/runs/{run_id}",
    response_model=RunDetail,
    summary="Get a run with its step timeline",
)
async def get_run(
    run_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> RunDetail:
    repo = _repo(session, ctx)
    run = await repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    run_steps = await repo.run_steps_for(run_id)
    data = RunRead.model_validate(run).model_dump()
    data["run_steps"] = [RunStepRead.model_validate(s) for s in run_steps]
    return RunDetail(**data)


# ─────────────────── human approval ───────────────────

@router.post(
    "/api/workflows/runs/{run_id}/decision",
    response_model=RunDetail,
    summary="Approve or reject a paused run",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def decide_run(
    run_id: uuid.UUID,
    payload: ApprovalDecision,
    background: BackgroundTasks,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> RunDetail:
    repo = _repo(session, ctx)
    run = await repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    if run.status != RunStatus.awaiting_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This run is not awaiting approval.",
        )
    decision = payload.decision.strip().lower()
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=422, detail="decision must be 'approve' or 'reject'.")

    approved = decision == "approve"
    background.add_task(resume_run, run_id, approved=approved, note=payload.note or "")

    audit(
        "approve" if approved else "reject",
        resource="workflow_run",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(run_id),
        meta={"workflow_id": str(run.workflow_id)},
    )

    run_steps = await repo.run_steps_for(run_id)
    data = RunRead.model_validate(run).model_dump()
    data["run_steps"] = [RunStepRead.model_validate(s) for s in run_steps]
    return RunDetail(**data)


# ─────────────────── versioning ───────────────────

@router.get(
    "/api/workflows/{workflow_id}/versions",
    response_model=WorkflowVersionListResponse,
    summary="List a workflow's version history",
)
async def list_versions(
    workflow_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WorkflowVersionListResponse:
    repo = _repo(session, ctx)
    workflow = await repo.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    rows = await repo.list_versions(workflow_id)
    return WorkflowVersionListResponse(
        items=[WorkflowVersionRead.model_validate(v) for v in rows],
        total=len(rows),
    )


@router.post(
    "/api/workflows/{workflow_id}/versions/{version}/rollback",
    response_model=WorkflowDetail,
    summary="Roll a workflow back to a previous version",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def rollback_version(
    workflow_id: uuid.UUID,
    version: int,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WorkflowDetail:
    repo = _repo(session, ctx)
    workflow = await repo.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
    target = await repo.get_version(workflow_id, version)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found.")

    snap = dict(target.snapshot or {})

    # Snapshot the current state first so the rollback itself is reversible.
    current_steps = await repo.steps_for(workflow_id)
    next_no = await repo.next_version_number(workflow_id)
    session.add(
        WorkflowVersion(
            workflow_id=workflow.id,
            organization_id=ctx.organization_id,
            version=next_no,
            snapshot=_snapshot(workflow, current_steps),
            created_by=ctx.user_id,
        )
    )

    # Apply the target snapshot.
    if snap.get("name"):
        workflow.name = str(snap["name"])
    workflow.description = snap.get("description")
    if snap.get("trigger_type") in _VALID_TRIGGERS:
        workflow.trigger_type = WorkflowTrigger(snap["trigger_type"])
    workflow.trigger_config = snap.get("trigger_config") or {}

    for s in current_steps:
        await session.delete(s)
    await session.flush()

    snap_steps = snap.get("steps") or []
    for i, st in enumerate(snap_steps):
        stype = st.get("type")
        if stype not in _VALID_STEP_TYPES:
            continue
        session.add(
            WorkflowStep(
                workflow_id=workflow.id,
                organization_id=ctx.organization_id,
                order_index=st.get("order_index", i),
                type=StepType(stype),
                name=str(st.get("name") or "Step"),
                config=st.get("config") or {},
            )
        )

    await session.commit()
    await session.refresh(workflow)
    steps = await repo.steps_for(workflow_id)

    audit(
        "rollback",
        resource="workflow",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(workflow.id),
        meta={"to_version": version},
    )
    return _detail(workflow, steps)


# ─────────────────── helpers ───────────────────

def _materialise_steps(
    workflow: Workflow, organization_id: uuid.UUID, steps: list[StepCreate]
) -> list[WorkflowStep]:
    out: list[WorkflowStep] = []
    for i, step in enumerate(steps):
        out.append(
            WorkflowStep(
                workflow_id=workflow.id,
                organization_id=organization_id,
                order_index=step.order_index if step.order_index is not None else i,
                type=StepType(step.type),
                name=step.name.strip(),
                config=step.config or {},
            )
        )
    return out
