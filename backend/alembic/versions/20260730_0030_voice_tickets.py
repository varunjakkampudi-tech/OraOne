"""Phase 4 — voice support tickets.

Adds ``voice_tickets``: support tickets raised from voice calls, with optional
external ticketing-provider linkage.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0030_voice_tickets"
down_revision: Union[str, None] = "0029_voice_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("customer_name", sa.String(length=200), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("customer_email", sa.String(length=254), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_provider", sa.String(length=40), nullable=True),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["call_id"], ["voice_calls.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_voice_tickets_organization_id", "voice_tickets", ["organization_id"])
    op.create_index("ix_voice_tickets_project_id", "voice_tickets", ["project_id"])
    op.create_index("ix_voice_tickets_agent_id", "voice_tickets", ["agent_id"])
    op.create_index("ix_voice_tickets_call_id", "voice_tickets", ["call_id"])
    op.create_index("ix_voice_tickets_status", "voice_tickets", ["status"])
    op.create_index("ix_voice_tickets_priority", "voice_tickets", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_voice_tickets_priority", table_name="voice_tickets")
    op.drop_index("ix_voice_tickets_status", table_name="voice_tickets")
    op.drop_index("ix_voice_tickets_call_id", table_name="voice_tickets")
    op.drop_index("ix_voice_tickets_agent_id", table_name="voice_tickets")
    op.drop_index("ix_voice_tickets_project_id", table_name="voice_tickets")
    op.drop_index("ix_voice_tickets_organization_id", table_name="voice_tickets")
    op.drop_table("voice_tickets")
