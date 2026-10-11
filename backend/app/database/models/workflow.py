"""Workflow automation models (Phase 11).

A *workflow* is an ordered list of *steps* that run against the org's own
AI, knowledge bases, agents and integrations. Each execution is a *run*,
and every step in a run records its own input/output/status so the UI can
show a live timeline and operators can debug failures.

    Workflow ──< WorkflowStep        (the definition / recipe)
    Workflow ──< WorkflowRun ──< WorkflowRunStep   (one execution)

Tenant-safe: every row carries ``organization_id``.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class WorkflowStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"


class WorkflowTrigger(str, enum.Enum):
    manual = "manual"        # run on demand / via API
    schedule = "schedule"    # cron-like (config.cron)
    event = "event"          # internal event (config.event)
    integration = "integration"  # an integration sync finished


class StepType(str, enum.Enum):
    ai_prompt = "ai_prompt"          # call the LLM with a templated prompt
    kb_query = "kb_query"            # RAG retrieval from knowledge base(s)
    agent_run = "agent_run"          # run one of the org's agents
    condition = "condition"          # branch / stop on a predicate
    transform = "transform"          # map/join variables into a new variable
    notification = "notification"    # emit a notification (email/slack/webhook)
    delay = "delay"                  # wait N seconds (bounded)
    webhook = "webhook"              # outbound HTTP POST
    # AI decision nodes (Phase 11 expansion) — structured LLM reasoning.
    ai_classify = "ai_classify"      # classify text into one of N categories
    ai_extract = "ai_extract"        # extract structured fields → JSON
    ai_summarize = "ai_summarize"    # summarise text
    ai_sentiment = "ai_sentiment"    # positive / negative / neutral
    ai_translate = "ai_translate"    # translate to a target language
    approval = "approval"            # pause for a human decision


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    awaiting_approval = "awaiting_approval"  # paused on a human-approval step
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class RunStepStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    awaiting_approval = "awaiting_approval"  # waiting on a human decision
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class Workflow(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "workflows"
    __table_args__ = (
        Index("ix_workflows_organization_id", "organization_id"),
        Index("ix_workflows_status", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus, name="workflow_status"),
        nullable=False,
        default=WorkflowStatus.draft,
    )
    trigger_type: Mapped[WorkflowTrigger] = mapped_column(
        Enum(WorkflowTrigger, name="workflow_trigger"),
        nullable=False,
        default=WorkflowTrigger.manual,
    )
    trigger_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))

    # Aggregate run stats (denormalised for cheap list rendering).
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.order_index",
    )


class WorkflowStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        Index("ix_workflow_steps_workflow_id", "workflow_id"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type: Mapped[StepType] = mapped_column(
        Enum(StepType, name="workflow_step_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    workflow: Mapped["Workflow"] = relationship(back_populates="steps")


class WorkflowRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("ix_workflow_runs_workflow_id", "workflow_id"),
        Index("ix_workflow_runs_organization_id", "organization_id"),
        Index("ix_workflow_runs_status", "status"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="workflow_run_status"),
        nullable=False,
        default=RunStatus.queued,
    )
    trigger: Mapped[WorkflowTrigger] = mapped_column(
        Enum(WorkflowTrigger, name="workflow_trigger"),
        nullable=False,
        default=WorkflowTrigger.manual,
    )
    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    steps_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steps_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    run_steps: Mapped[list["WorkflowRunStep"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="WorkflowRunStep.order_index",
    )


class WorkflowRunStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_run_steps"
    __table_args__ = (
        Index("ix_workflow_run_steps_run_id", "run_id"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type: Mapped[StepType] = mapped_column(
        Enum(StepType, name="workflow_step_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[RunStepStatus] = mapped_column(
        Enum(RunStepStatus, name="workflow_run_step_status"),
        nullable=False,
        default=RunStepStatus.pending,
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    run: Mapped["WorkflowRun"] = relationship(back_populates="run_steps")


class WorkflowVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable snapshot of a workflow definition (Phase 11 versioning).

    Every edit captures the *prior* definition here so authors can review
    history and roll back. ``snapshot`` holds name/description/trigger and
    the full ordered step list.
    """

    __tablename__ = "workflow_versions"
    __table_args__ = (
        Index("ix_workflow_versions_workflow_id", "workflow_id"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
