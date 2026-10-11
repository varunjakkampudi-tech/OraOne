"""R1 Enterprise Chat: conversation folders + organization/sharing columns."""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0018_chat_organization"
down_revision: Union[str, None] = "0017_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── conversation_folders ──
    op.create_table(
        "conversation_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("color", sa.String(length=9), nullable=True),
        sa.Column("icon", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        if_not_exists=True,
    )
    op.create_index(
        "ix_conversation_folders_org_user",
        "conversation_folders",
        ["organization_id", "user_id"],
        if_not_exists=True,
    )

    # ── conversations: new organization & sharing columns ──
    op.add_column("conversations", sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("conversations", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("conversations", sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("conversations", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("conversations", sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("conversations", sa.Column("share_token", sa.String(length=64), nullable=True))
    op.add_column("conversations", sa.Column("shared_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_conversations_share_token", "conversations", ["share_token"])
    op.create_index("ix_conversations_folder_id", "conversations", ["folder_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_conversations_folder_id", table_name="conversations")
    op.drop_constraint("uq_conversations_share_token", "conversations", type_="unique")
    for col in ("shared_at", "share_token", "tags", "folder_id", "is_favorite", "is_archived", "is_pinned"):
        op.drop_column("conversations", col)
    op.drop_table("conversation_folders")
