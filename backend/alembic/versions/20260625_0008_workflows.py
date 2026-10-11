"""Workflow automation tables (Phase 11).

Creates ``workflows`` / ``workflow_steps`` / ``workflow_runs`` /
``workflow_run_steps`` plus their enum types. Enums are created
idempotently with ``checkfirst`` so partially-applied dev DBs survive.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0008_workflows"
down_revision: Union[str, None] = "0007_integration_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


workflow_status = postgresql.ENUM(
    "draft", "active", "paused", name="workflow_status", create_type=False
)
workflow_trigger = postgresql.ENUM(
    "manual", "schedule", "event", "integration",
    name="workflow_trigger", create_type=False,
)
step_type = postgresql.ENUM(
    "ai_prompt", "kb_query", "agent_run", "condition", "transform",
    "notification", "delay", "webhook",
    name="workflow_step_type", create_type=False,
)
run_status = postgresql.ENUM(
    "queued", "running", "completed", "failed", "cancelled",
    name="workflow_run_status", create_type=False,
)
run_step_status = postgresql.ENUM(
    "pending", "running", "completed", "failed", "skipped",
    name="workflow_run_step_status", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (workflow_status, workflow_trigger, step_type, run_status, run_step_status):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", workflow_status, nullable=False, server_default="draft"),
        sa.Column("trigger_type", workflow_trigger, nullable=False, server_default="manual"),
        sa.Column("trigger_config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        if_not_exists=True,
    )
    op.create_index("ix_workflows_organization_id", "workflows", ["organization_id"], if_not_exists=True)
    op.create_index("ix_workflows_status", "workflows", ["status"], if_not_exists=True)

    op.create_table(
        "workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("type", step_type, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        if_not_exists=True,
    )
    op.create_index("ix_workflow_steps_workflow_id", "workflow_steps", ["workflow_id"], if_not_exists=True)

    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", run_status, nullable=False, server_default="queued"),
        sa.Column("trigger", workflow_trigger, nullable=False, server_default="manual"),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("output", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("steps_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("steps_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        if_not_exists=True,
    )
    op.create_index("ix_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"], if_not_exists=True)
    op.create_index("ix_workflow_runs_organization_id", "workflow_runs", ["organization_id"], if_not_exists=True)
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"], if_not_exists=True)

    op.create_table(
        "workflow_run_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("type", step_type, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", run_step_status, nullable=False, server_default="pending"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("input", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("output", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        if_not_exists=True,
    )
    op.create_index("ix_workflow_run_steps_run_id", "workflow_run_steps", ["run_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("workflow_run_steps", if_exists=True)
    op.drop_table("workflow_runs", if_exists=True)
    op.drop_table("workflow_steps", if_exists=True)
    op.drop_table("workflows", if_exists=True)
    bind = op.get_bind()
    for name in (
        "workflow_run_step_status",
        "workflow_run_status",
        "workflow_step_type",
        "workflow_trigger",
        "workflow_status",
    ):
        op.execute(sa.text(f"DROP TYPE IF EXISTS {name}"))
