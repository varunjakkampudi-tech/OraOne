"""Pydantic schemas for the Workflow Automation API (Phase 11)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ──────────────── Steps ────────────────

class StepCreate(BaseModel):
    type: str
    name: str = Field(min_length=1, max_length=200)
    config: dict[str, Any] = Field(default_factory=dict)
    order_index: Optional[int] = None


class StepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    order_index: int
    type: str
    name: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ──────────────── Workflows ────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    trigger_type: str = "manual"
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    steps: list[StepCreate] = Field(default_factory=list)


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    status: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict[str, Any]] = None
    steps: Optional[list[StepCreate]] = None


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str
    trigger_type: str
    trigger_config: dict[str, Any]
    created_by: Optional[uuid.UUID] = None
    run_count: int
    success_count: int
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class WorkflowDetail(WorkflowRead):
    steps: list[StepRead] = Field(default_factory=list)


class WorkflowListResponse(BaseModel):
    items: list[WorkflowRead]
    total: int
    limit: int
    offset: int


# ──────────────── Runs ────────────────

class RunRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class RunStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    step_id: Optional[uuid.UUID] = None
    order_index: int
    type: str
    name: str
    status: str
    input: dict[str, Any]
    output: dict[str, Any]
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    organization_id: uuid.UUID
    status: str
    trigger: str
    triggered_by: Optional[uuid.UUID] = None
    input: dict[str, Any]
    output: dict[str, Any]
    error_message: Optional[str] = None
    steps_total: int
    steps_completed: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime


class RunDetail(RunRead):
    run_steps: list[RunStepRead] = Field(default_factory=list)


class RunListResponse(BaseModel):
    items: list[RunRead]
    total: int
    limit: int
    offset: int


# ──────────────── Human approval ────────────────

class ApprovalDecision(BaseModel):
    decision: str = Field(description="'approve' or 'reject'")
    note: Optional[str] = Field(default=None, max_length=2000)


# ──────────────── Versioning ────────────────

class WorkflowVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    version: int
    snapshot: dict[str, Any]
    created_by: Optional[uuid.UUID] = None
    created_at: datetime


class WorkflowVersionListResponse(BaseModel):
    items: list[WorkflowVersionRead]
    total: int


# ──────────────── Analytics ────────────────

class WorkflowAnalytics(BaseModel):
    total_workflows: int
    active_workflows: int
    total_runs: int
    completed_runs: int
    failed_runs: int
    awaiting_approval: int
    success_rate: float
    avg_duration_seconds: Optional[float] = None
    most_used: list[dict[str, Any]] = Field(default_factory=list)
