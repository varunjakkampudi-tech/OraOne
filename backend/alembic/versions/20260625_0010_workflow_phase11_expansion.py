"""Phase 11 expansion: AI nodes, approval, versioning.

Adds new values to the workflow enum types (AI decision nodes + the
``approval`` step, plus ``awaiting_approval`` run/step statuses) and a
``workflow_versions`` table holding immutable definition snapshots.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0010_workflow_phase11_expansion"
down_revision: Union[str, None] = "0009_workflow_run_step_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_STEP_TYPE_VALUES = (
    "ai_classify",
    "ai_extract",
    "ai_summarize",
    "ai_sentiment",
    "ai_translate",
    "approval",
)


def upgrade() -> None:
    # New enum values must be added outside a transaction block.
    with op.get_context().autocommit_block():
        for val in _STEP_TYPE_VALUES:
            op.execute(
                f"ALTER TYPE workflow_step_type ADD VALUE IF NOT EXISTS '{val}'"
            )
        op.execute(
            "ALTER TYPE workflow_run_status ADD VALUE IF NOT EXISTS 'awaiting_approval'"
        )
        op.execute(
            "ALTER TYPE workflow_run_step_status ADD VALUE IF NOT EXISTS 'awaiting_approval'"
        )

    op.create_table(
        "workflow_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        if_not_exists=True,
    )
    op.create_index(
        "ix_workflow_versions_workflow_id",
        "workflow_versions",
        ["workflow_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_versions_workflow_id", table_name="workflow_versions")
    op.drop_table("workflow_versions")
    # Enum values are intentionally left in place (Postgres can't easily
    # drop a single enum value without recreating the type).
