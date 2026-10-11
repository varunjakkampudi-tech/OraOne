"""Voice compliance: Do-Not-Call / suppression list (Product 2 #16).

Adds ``voice_suppression_entries`` — one org-scoped record per suppressed
phone number. The outbound dialer consults this list before placing a call so
numbers that opted out (or sit on a DND registry) are never contacted again.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0041_voice_suppression"
down_revision: Union[str, None] = "0040_marketplace_reviews"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_suppression_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("note", sa.Text()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "organization_id", "phone_number",
            name="uq_voice_suppression_org_phone",
        ),
    )
    op.create_index(
        "ix_voice_suppression_organization_id",
        "voice_suppression_entries",
        ["organization_id"],
    )
    op.create_index(
        "ix_voice_suppression_phone_number",
        "voice_suppression_entries",
        ["phone_number"],
    )
    op.create_index(
        "ix_voice_suppression_reason",
        "voice_suppression_entries",
        ["reason"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_voice_suppression_reason", table_name="voice_suppression_entries"
    )
    op.drop_index(
        "ix_voice_suppression_phone_number", table_name="voice_suppression_entries"
    )
    op.drop_index(
        "ix_voice_suppression_organization_id", table_name="voice_suppression_entries"
    )
    op.drop_table("voice_suppression_entries")
