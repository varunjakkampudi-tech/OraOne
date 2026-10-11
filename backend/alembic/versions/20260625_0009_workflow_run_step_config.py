"""Add config column to workflow_run_steps (Phase 11 fix).

Idempotent: on some environments (notably a fresh database created after
0008_workflows already inlined this column into the initial CREATE TABLE)
the column exists before this migration runs. Guard with an inspector check
so `alembic upgrade head` succeeds either way.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0009_workflow_run_step_config"
down_revision: Union[str, None] = "0008_workflows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {c["name"] for c in inspector.get_columns("workflow_run_steps")}
    if "config" not in existing:
        op.add_column(
            "workflow_run_steps",
            sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    op.drop_column("workflow_run_steps", "config")
