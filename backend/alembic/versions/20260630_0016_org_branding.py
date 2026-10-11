"""Phase 12 Module 15: white-label branding.

Adds ``org_branding`` (one row per org). No new enum types.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0016_org_branding"
down_revision: Union[str, None] = "0015_ai_model_policy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_branding",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("brand_name", sa.String(length=120), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("primary_color", sa.String(length=9), nullable=False, server_default="#4F46E5"),
        sa.Column("accent_color", sa.String(length=9), nullable=False, server_default="#06B6D4"),
        sa.Column("support_email", sa.String(length=160), nullable=True),
        sa.Column("support_url", sa.String(length=500), nullable=True),
        sa.Column("custom_domain", sa.String(length=255), nullable=True),
        sa.Column("hide_powered_by", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", name="uq_org_branding_org"),
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("org_branding")
