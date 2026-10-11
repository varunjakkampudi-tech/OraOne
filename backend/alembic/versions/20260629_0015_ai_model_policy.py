"""Phase 12 Module 13: AI model routing policy.

Adds ``ai_model_policies`` (one row per org). No new enum types.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0015_ai_model_policy"
down_revision: Union[str, None] = "0014_api_keys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_model_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("default_model", sa.String(length=80), nullable=False),
        sa.Column("fallback_models", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("disabled_models", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", name="uq_ai_model_policies_org"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("ai_model_policies")
