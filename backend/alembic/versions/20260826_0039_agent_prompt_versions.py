"""Agent prompt versioning (features #7/#8).

Adds ``agent_prompt_versions`` — immutable snapshots of an agent's prompt
and config, captured each time a new version is published. Powers the
version history timeline, prompt diff viewer, and one-click rollback.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0039_agent_prompt_versions"
down_revision: Union[str, None] = "0038_marketplace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("label", sa.String(160)),
        sa.Column("note", sa.Text()),
        sa.Column("system_prompt", sa.Text()),
        sa.Column("temperature", sa.Numeric(3, 2)),
        sa.Column("max_tokens", sa.Integer()),
        sa.Column("voice", sa.String(80)),
        sa.Column("language", sa.String(16)),
        sa.Column("greeting", sa.Text()),
        sa.Column(
            "config",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
    )
    op.create_index(
        "ix_agent_prompt_versions_agent",
        "agent_prompt_versions",
        ["agent_id", "version"],
    )
    op.create_index(
        "ix_agent_prompt_versions_org",
        "agent_prompt_versions",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_prompt_versions_org", table_name="agent_prompt_versions")
    op.drop_index("ix_agent_prompt_versions_agent", table_name="agent_prompt_versions")
    op.drop_table("agent_prompt_versions")
