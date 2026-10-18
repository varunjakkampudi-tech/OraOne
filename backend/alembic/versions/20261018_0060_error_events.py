"""Structured server error events for the admin log viewer.

Revision ID: 0060_error_events
Revises: 0059_admin_config_overrides

Adds ``error_events``: one row per 5xx response or unhandled exception, keyed
by the request ID returned to the caller. Text columns hold scrubbed content.
Rows older than 30 days are pruned by ``app.services.ops_service``.

Downgrade drops the table and every stored error record.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0060_error_events"
down_revision: Union[str, Sequence[str], None] = "0059_admin_config_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "error_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("method", sa.String(length=12), nullable=False),
        sa.Column("route", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("exception_type", sa.String(length=120), nullable=True),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("release_version", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("actor_hash", sa.String(length=32), nullable=True),
        sa.Column("org_hash", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_error_events_request_id", "error_events", ["request_id"])
    op.create_index("ix_error_events_occurred_at", "error_events", ["occurred_at"])
    op.create_index("ix_error_events_route", "error_events", ["route"])
    op.create_index("ix_error_events_status_code", "error_events", ["status_code"])


def downgrade() -> None:
    op.drop_index("ix_error_events_status_code", table_name="error_events")
    op.drop_index("ix_error_events_route", table_name="error_events")
    op.drop_index("ix_error_events_occurred_at", table_name="error_events")
    op.drop_index("ix_error_events_request_id", table_name="error_events")
    op.drop_table("error_events")
