"""Signup legal acceptance: record Terms, Privacy and marketing choices per account.

Revision ID: 0073_signup_consents
Revises: 0072_escalation_first_reply

Creates ``signup_consents``. Existing accounts get no rows: they signed up before this
record existed, and their access is unchanged. Downgrade drops the table.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0073_signup_consents"
down_revision: Union[str, None] = "0072_escalation_first_reply"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signup_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document", sa.String(length=20), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "document", name="uq_signup_consents_user_document"
        ),
        sa.CheckConstraint(
            "document IN ('terms', 'privacy', 'marketing')",
            name="ck_signup_consents_document",
        ),
    )
    op.create_index("ix_signup_consents_user_id", "signup_consents", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_signup_consents_user_id", table_name="signup_consents")
    op.drop_table("signup_consents")
