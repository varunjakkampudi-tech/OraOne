"""R6 Embedded Website Widget platform.

Creates widgets / widget_domains / widget_sessions / widget_events for the
embeddable, white-label AI chat widget. Widgets bind an agent + knowledge
base to a public, domain-restricted chat experience served via a single
``<script>`` tag and powered by the Enterprise RAG engine (R4).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0021_embedded_widget"
down_revision: Union[str, None] = "0020_website_crawling"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── widgets ──
    op.create_table(
        "widgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("widget_type", sa.String(length=20), nullable=False, server_default="bubble"),
        sa.Column("position", sa.String(length=20), nullable=False, server_default="bottom-right"),
        sa.Column("auth_mode", sa.String(length=20), nullable=False, server_default="public"),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("theme", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="SET NULL"),
        if_not_exists=True,
    )
    op.create_index("ix_widgets_organization_id", "widgets", ["organization_id"], if_not_exists=True)
    op.create_index("ix_widgets_public_key", "widgets", ["public_key"], unique=True, if_not_exists=True)
    op.create_index("ix_widgets_status", "widgets", ["status"], if_not_exists=True)

    # ── widget_domains ──
    op.create_table(
        "widget_domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("widget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["widget_id"], ["widgets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("widget_id", "domain", name="uq_widget_domains_widget_domain"),
        if_not_exists=True,
    )
    op.create_index("ix_widget_domains_widget_id", "widget_domains", ["widget_id"], if_not_exists=True)

    # ── widget_sessions ──
    op.create_table(
        "widget_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("widget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("visitor_id", sa.String(length=80), nullable=False),
        sa.Column("user_context", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("referer", sa.String(length=2048), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["widget_id"], ["widgets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        if_not_exists=True,
    )
    op.create_index("ix_widget_sessions_widget_id", "widget_sessions", ["widget_id"], if_not_exists=True)
    op.create_index("ix_widget_sessions_visitor_id", "widget_sessions", ["visitor_id"], if_not_exists=True)
    op.create_index("ix_widget_sessions_organization_id", "widget_sessions", ["organization_id"], if_not_exists=True)

    # ── widget_events ──
    op.create_table(
        "widget_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("widget_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event", sa.String(length=40), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["widget_id"], ["widgets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["widget_sessions.id"], ondelete="CASCADE"),
        if_not_exists=True,
    )
    op.create_index("ix_widget_events_widget_id", "widget_events", ["widget_id"], if_not_exists=True)
    op.create_index("ix_widget_events_organization_id", "widget_events", ["organization_id"], if_not_exists=True)
    op.create_index("ix_widget_events_event", "widget_events", ["event"], if_not_exists=True)
    op.create_index("ix_widget_events_created_at", "widget_events", ["created_at"], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("widget_events")
    op.drop_table("widget_sessions")
    op.drop_table("widget_domains")
    op.drop_table("widgets")
