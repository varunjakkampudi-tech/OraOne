"""Phase 12 Module 2: usage metering.

Adds the ``usage_counters`` table for accumulating metered events
(AI messages, workflow runs, API calls, ...) per organization, metric and
period bucket. No new enum types — ``metric`` and ``period`` are plain
strings to keep the metric registry flexible at the application layer.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0013_usage_counters"
down_revision: Union[str, None] = "0012_team_invitations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("metric", sa.String(length=60), nullable=False),
        sa.Column("period", sa.String(length=10), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "organization_id", "metric", "period",
            name="uq_usage_counters_org_metric_period",
        ),
        if_not_exists=True,
    )
    op.create_index(
        "ix_usage_counters_organization_id", "usage_counters",
        ["organization_id"], if_not_exists=True,
    )
    op.create_index(
        "ix_usage_counters_metric", "usage_counters",
        ["metric"], if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("usage_counters")
