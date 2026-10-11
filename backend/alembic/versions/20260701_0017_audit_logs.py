"""Phase 12 Module 5: persisted audit trail (audit_logs)."""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0017_audit_logs"
down_revision: Union[str, None] = "0016_org_branding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("resource", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        if_not_exists=True,
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"], if_not_exists=True)
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], if_not_exists=True)
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], if_not_exists=True)
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource"], if_not_exists=True)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("audit_logs")
