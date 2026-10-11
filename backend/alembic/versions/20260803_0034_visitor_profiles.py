"""Unified cross-channel visitor identity.

Creates ``visitor_profiles`` — one persistent identity per visitor/contact
across ALL channels (chat, voice, forms, api) — and links conversations to it
via ``conversations.visitor_profile_id``. This is what lets the agent share
memory across channels ("the AI already knows you").
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0034_visitor_profiles"
down_revision: Union[str, None] = "0033_appointments_callbacks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visitor_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("visitor_key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column(
            "shared_context",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "channels_used",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "memory",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("lead_score", sa.Integer(), nullable=True),
        sa.Column("lead_status", sa.String(length=40), nullable=True),
        sa.Column("last_conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_channel", sa.String(length=20), nullable=True),
        sa.Column(
            "conversation_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "visitor_key", name="uq_visitor_profiles_org_key"
        ),
    )
    op.create_index(
        "ix_visitor_profiles_organization_id", "visitor_profiles", ["organization_id"]
    )
    op.create_index("ix_visitor_profiles_email", "visitor_profiles", ["email"])
    op.create_index("ix_visitor_profiles_phone", "visitor_profiles", ["phone"])
    op.create_index(
        "ix_visitor_profiles_last_seen_at", "visitor_profiles", ["last_seen_at"]
    )

    op.add_column(
        "conversations",
        sa.Column(
            "visitor_profile_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.create_foreign_key(
        "fk_conversations_visitor_profile_id",
        "conversations",
        "visitor_profiles",
        ["visitor_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversations_visitor_profile_id",
        "conversations",
        ["visitor_profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_visitor_profile_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_visitor_profile_id", "conversations", type_="foreignkey"
    )
    op.drop_column("conversations", "visitor_profile_id")

    op.drop_index("ix_visitor_profiles_last_seen_at", table_name="visitor_profiles")
    op.drop_index("ix_visitor_profiles_phone", table_name="visitor_profiles")
    op.drop_index("ix_visitor_profiles_email", table_name="visitor_profiles")
    op.drop_index(
        "ix_visitor_profiles_organization_id", table_name="visitor_profiles"
    )
    op.drop_table("visitor_profiles")
