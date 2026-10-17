"""Admin configuration console: encrypted per-environment overrides.

Revision ID: 0059_admin_config_overrides
Revises: 0058_marketing_campaigns

Adds ``admin_config_overrides``: one encrypted value per (environment, key),
written only by super-admin requests to the configuration console. Values are
read at process start by ``app.core.config_overrides``.

Downgrade drops the table and every console-managed override. Afterwards the
application falls back to the environment's own values, so downgrade only when
the console is not in use.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0059_admin_config_overrides"
down_revision: Union[str, Sequence[str], None] = "0058_marketing_campaigns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_config_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("value_encrypted", sa.Text(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "environment", "name", name="uq_admin_config_overrides_env_name"
        ),
        sa.CheckConstraint(
            "environment IN ('local', 'production')",
            name="ck_admin_config_overrides_environment",
        ),
    )
    op.create_index(
        "ix_admin_config_overrides_environment",
        "admin_config_overrides",
        ["environment"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_config_overrides_environment",
        table_name="admin_config_overrides",
    )
    op.drop_table("admin_config_overrides")
