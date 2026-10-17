"""Outbound calling queue: call campaigns and per-lead call attempts.

Revision ID: 0053_outbound_call_campaigns
Revises: 0052_model_catalogue
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0053_outbound_call_campaigns"
down_revision: Union[str, Sequence[str], None] = "0052_model_catalogue"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "call_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'running', 'paused', 'completed')",
            name="ck_call_campaigns_status",
        ),
    )
    op.create_index(
        "ix_call_campaigns_organization_id", "call_campaigns", ["organization_id"]
    )
    op.create_index("ix_call_campaigns_project_id", "call_campaigns", ["project_id"])

    op.create_table(
        "call_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("call_campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("twilio_call_sid", sa.String(64), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'calling', 'completed', 'failed', 'skipped')",
            name="ck_call_attempts_status",
        ),
    )
    op.create_index(
        "ix_call_attempts_organization_id", "call_attempts", ["organization_id"]
    )
    op.create_index(
        "ix_call_attempts_campaign_status", "call_attempts", ["campaign_id", "status"]
    )
    op.create_index(
        "ix_call_attempts_lead_attempted", "call_attempts", ["lead_id", "attempted_at"]
    )
    op.create_index(
        "ix_call_attempts_twilio_call_sid",
        "call_attempts",
        ["twilio_call_sid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_call_attempts_twilio_call_sid", table_name="call_attempts")
    op.drop_index("ix_call_attempts_lead_attempted", table_name="call_attempts")
    op.drop_index("ix_call_attempts_campaign_status", table_name="call_attempts")
    op.drop_index("ix_call_attempts_organization_id", table_name="call_attempts")
    op.drop_table("call_attempts")
    op.drop_index("ix_call_campaigns_project_id", table_name="call_campaigns")
    op.drop_index("ix_call_campaigns_organization_id", table_name="call_campaigns")
    op.drop_table("call_campaigns")
