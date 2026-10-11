"""Phase 6 — voice workflow triggers.

Adds ``voice_workflow_triggers``: binds a voice-call signal to an existing
Workflow so conversations can launch business automations.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0031_voice_workflow_triggers"
down_revision: Union[str, None] = "0030_voice_tickets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_workflow_triggers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("trigger_type", sa.String(length=20), nullable=False, server_default="intent"),
        sa.Column("match_values", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("once_per_call", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("fire_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("configuration", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_voice_workflow_triggers_organization_id", "voice_workflow_triggers", ["organization_id"])
    op.create_index("ix_voice_workflow_triggers_agent_id", "voice_workflow_triggers", ["agent_id"])
    op.create_index("ix_voice_workflow_triggers_workflow_id", "voice_workflow_triggers", ["workflow_id"])
    op.create_index("ix_voice_workflow_triggers_enabled", "voice_workflow_triggers", ["enabled"])


def downgrade() -> None:
    op.drop_index("ix_voice_workflow_triggers_enabled", table_name="voice_workflow_triggers")
    op.drop_index("ix_voice_workflow_triggers_workflow_id", table_name="voice_workflow_triggers")
    op.drop_index("ix_voice_workflow_triggers_agent_id", table_name="voice_workflow_triggers")
    op.drop_index("ix_voice_workflow_triggers_organization_id", table_name="voice_workflow_triggers")
    op.drop_table("voice_workflow_triggers")
