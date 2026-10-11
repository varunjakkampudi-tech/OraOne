"""AI chat & agent runtime columns (Phase 8).

Additive-only migration — does not touch existing columns, so the CRM
conversation/message surfaces from Phases 5–7 keep working unchanged.

* ``conversations.user_id``         — owner of an AI chat thread (FK users)
* ``conversations.title``           — auto-generated thread title
* ``conversations.last_message_at`` — sort key for the chat sidebar
* ``messages.token_count``          — total tokens billed to the message
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_chat_runtime"
down_revision: Union[str, None] = "0003_doc_processing_telemetry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations", sa.Column("title", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "conversations",
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_conversations_user_id_users",
        "conversations",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversations_user_id", "conversations", ["user_id"]
    )

    op.add_column(
        "messages", sa.Column("token_count", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("messages", "token_count")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_user_id_users", "conversations", type_="foreignkey"
    )
    op.drop_column("conversations", "last_message_at")
    op.drop_column("conversations", "title")
    op.drop_column("conversations", "user_id")
