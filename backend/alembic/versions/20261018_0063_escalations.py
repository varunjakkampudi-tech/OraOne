"""Escalations: persistent human handoff for unanswered visitor questions.

Revision ID: 0063_escalations
Revises: 0062_visitor_project_scope

Creates ``escalations``. Each row is one question the assistant could not
answer, with ownership, delivery state and retry bookkeeping. Downgrade drops
the table, so any open escalations are lost. Export them first if the table
holds live handoffs.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0063_escalations"
down_revision: Union[str, None] = "0062_visitor_project_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("contact_name", sa.String(160), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(40), nullable=True),
        sa.Column(
            "has_contact", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "assigned_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notify_status", sa.String(20), nullable=False),
        sa.Column("notify_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(80), nullable=True),
    )
    op.create_index(
        "ix_escalations_org_project_status",
        "escalations",
        ["organization_id", "project_id", "status"],
    )
    op.create_index(
        "ix_escalations_notify_due",
        "escalations",
        ["notify_status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_escalations_notify_due", table_name="escalations")
    op.drop_index("ix_escalations_org_project_status", table_name="escalations")
    op.drop_table("escalations")
