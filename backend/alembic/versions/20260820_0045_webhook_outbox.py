"""Transactional outbox for webhooks — webhook_outbox table.

Closes the "DB committed, event never published" gap: callers now insert
an outbox row in the same transaction as their business data (see
app/services/webhook_outbox.py::enqueue), and a background poller
(start_outbox_worker) drains pending rows into the existing webhook
delivery machinery.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0045_webhook_outbox"
down_revision: Union[str, None] = "0044_self_hosted_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event", sa.String(length=60), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_webhook_outbox_status_created", "webhook_outbox", ["status", "created_at"])
    op.create_index("ix_webhook_outbox_organization_id", "webhook_outbox", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_webhook_outbox_organization_id", table_name="webhook_outbox")
    op.drop_index("ix_webhook_outbox_status_created", table_name="webhook_outbox")
    op.drop_table("webhook_outbox")
