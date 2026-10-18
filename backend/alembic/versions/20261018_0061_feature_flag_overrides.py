"""Beta feature flag overrides.

Revision ID: 0061_feature_flag_overrides
Revises: 0060_admin_config_drafts, 0060_error_events (merges both current heads)

Adds ``feature_flag_overrides``: runtime organisation and beta-cohort switches
written by super-admin requests. Flag definitions stay in code, so this table
holds only the overrides. No personal data is stored; cohort rows are keyed by
a pseudonymous email hash.

Downgrade drops the table. Every runtime override is lost, so flags fall back
to their code defaults and rollout lists.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0061_feature_flag_overrides"
down_revision: Union[str, Sequence[str], None] = (
    "0060_admin_config_drafts",
    "0060_error_events",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_flag_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("flag_key", sa.String(length=80), nullable=False),
        sa.Column("scope", sa.String(length=24), nullable=False),
        sa.Column("scope_value", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "flag_key",
            "scope",
            "scope_value",
            name="uq_feature_flag_overrides_key_scope",
        ),
        sa.CheckConstraint(
            "scope IN ('organization', 'cohort_member')",
            name="ck_feature_flag_overrides_scope",
        ),
    )
    op.create_index(
        "ix_feature_flag_overrides_flag_key",
        "feature_flag_overrides",
        ["flag_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_feature_flag_overrides_flag_key",
        table_name="feature_flag_overrides",
    )
    op.drop_table("feature_flag_overrides")
