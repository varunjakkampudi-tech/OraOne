"""Phase 2 — appointments & callbacks.

Adds ``voice_appointments`` (TC-019..022, booking flows) and
``voice_callbacks`` (TC-060, callback requests) raised by the AI Receptionist.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0033_appointments_callbacks"
down_revision: Union[str, None] = "0032_voice_library"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_name", sa.String(length=200), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("service", sa.String(length=200), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="booked"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["call_id"], ["voice_calls.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_voice_appointments_organization_id", "voice_appointments", ["organization_id"])
    op.create_index("ix_voice_appointments_project_id", "voice_appointments", ["project_id"])
    op.create_index("ix_voice_appointments_agent_id", "voice_appointments", ["agent_id"])
    op.create_index("ix_voice_appointments_scheduled_at", "voice_appointments", ["scheduled_at"])
    op.create_index("ix_voice_appointments_status", "voice_appointments", ["status"])

    op.create_table(
        "voice_callbacks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_name", sa.String(length=200), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("preferred_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["call_id"], ["voice_calls.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_voice_callbacks_organization_id", "voice_callbacks", ["organization_id"])
    op.create_index("ix_voice_callbacks_project_id", "voice_callbacks", ["project_id"])
    op.create_index("ix_voice_callbacks_agent_id", "voice_callbacks", ["agent_id"])
    op.create_index("ix_voice_callbacks_status", "voice_callbacks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_voice_callbacks_status", table_name="voice_callbacks")
    op.drop_index("ix_voice_callbacks_agent_id", table_name="voice_callbacks")
    op.drop_index("ix_voice_callbacks_project_id", table_name="voice_callbacks")
    op.drop_index("ix_voice_callbacks_organization_id", table_name="voice_callbacks")
    op.drop_table("voice_callbacks")
    op.drop_index("ix_voice_appointments_status", table_name="voice_appointments")
    op.drop_index("ix_voice_appointments_scheduled_at", table_name="voice_appointments")
    op.drop_index("ix_voice_appointments_agent_id", table_name="voice_appointments")
    op.drop_index("ix_voice_appointments_project_id", table_name="voice_appointments")
    op.drop_index("ix_voice_appointments_organization_id", table_name="voice_appointments")
    op.drop_table("voice_appointments")
