"""Admin configuration console: drafts and publish history.

Revision ID: 0060_admin_config_drafts
Revises: 0059_admin_config_overrides

Adds two tables for the draft-and-publish flow:

  * ``admin_config_drafts``: one pending change per (environment, key). The
    value is encrypted; ``action`` is ``set`` (value in ``value_encrypted``) or
    ``clear`` (no value). Drafts never affect the running application.
  * ``admin_config_publish_events``: one row per publish. It records who
    published, when, why, and the key names with their change type. It never
    records a value.

Publishing copies drafts into ``admin_config_overrides`` (active values) and
deletes them, in one transaction.

Downgrade drops both tables. Pending drafts and publish history are lost, and
active values in ``admin_config_overrides`` are untouched.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0060_admin_config_drafts"
down_revision: Union[str, Sequence[str], None] = "0059_admin_config_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_config_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=8), nullable=False),
        sa.Column("value_encrypted", sa.Text(), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "environment", "name", name="uq_admin_config_drafts_env_name"
        ),
        sa.CheckConstraint(
            "environment IN ('local', 'production')",
            name="ck_admin_config_drafts_environment",
        ),
        sa.CheckConstraint(
            "action IN ('set', 'clear')",
            name="ck_admin_config_drafts_action",
        ),
        sa.CheckConstraint(
            "(action = 'set' AND value_encrypted IS NOT NULL) "
            "OR (action = 'clear' AND value_encrypted IS NULL)",
            name="ck_admin_config_drafts_value_matches_action",
        ),
    )
    op.create_index(
        "ix_admin_config_drafts_environment",
        "admin_config_drafts",
        ["environment"],
    )

    op.create_table(
        "admin_config_publish_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_by_email", sa.String(length=320), nullable=False),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "changes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.CheckConstraint(
            "environment IN ('local', 'production')",
            name="ck_admin_config_publish_events_environment",
        ),
    )
    op.create_index(
        "ix_admin_config_publish_events_env_published_at",
        "admin_config_publish_events",
        ["environment", "published_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_config_publish_events_env_published_at",
        table_name="admin_config_publish_events",
    )
    op.drop_table("admin_config_publish_events")
    op.drop_index(
        "ix_admin_config_drafts_environment",
        table_name="admin_config_drafts",
    )
    op.drop_table("admin_config_drafts")
