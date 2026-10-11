"""Product 2 — Voice platform foundation.

Adds Voice as an additional channel on the existing Agent architecture:
``agent_channels``, ``voice_profiles``, ``voice_calls``, ``voice_messages``,
``voice_recordings`` (Phase 1), plus forward-looking config tables for the
AI Receptionist / Sales / Support agents, human handoff and outbound
campaigns (Phases 2-8). No ``voice_agents`` table — Voice reuses Agents.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0029_voice_foundation"
down_revision: Union[str, None] = "0028_feature_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts_cols() -> list:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    # ── agent_channels ──
    op.create_table(
        "agent_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="voice"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("configuration", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("agent_id", "channel", name="uq_agent_channels_agent_channel"),
    )
    op.create_index("ix_agent_channels_agent_id", "agent_channels", ["agent_id"])
    op.create_index("ix_agent_channels_organization_id", "agent_channels", ["organization_id"])
    op.create_index("ix_agent_channels_channel", "agent_channels", ["channel"])

    # ── voice_profiles ──
    op.create_table(
        "voice_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="elevenlabs"),
        sa.Column("voice_id", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("model", sa.String(length=80), nullable=False, server_default="eleven_turbo_v2_5"),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("sample_rate", sa.Integer(), nullable=False, server_default="8000"),
        sa.Column("speed", sa.Float(), nullable=False, server_default="1"),
        sa.Column("stability", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("similarity_boost", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("style", sa.Float(), nullable=False, server_default="0"),
        sa.Column("stt_provider", sa.String(length=40), nullable=False, server_default="deepgram"),
        sa.Column("stt_model", sa.String(length=80), nullable=False, server_default="nova-2"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("configuration", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_voice_profiles_agent_id", "voice_profiles", ["agent_id"])
    op.create_index("ix_voice_profiles_organization_id", "voice_profiles", ["organization_id"])

    # ── voice_campaigns (created before voice_calls for the FK) ──
    op.create_table(
        "voice_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("goal", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("from_number", sa.String(length=32), nullable=True),
        sa.Column("script", sa.Text(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("concurrency", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_contacts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_contacts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_contacts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("configuration", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_voice_campaigns_organization_id", "voice_campaigns", ["organization_id"])
    op.create_index("ix_voice_campaigns_project_id", "voice_campaigns", ["project_id"])
    op.create_index("ix_voice_campaigns_status", "voice_campaigns", ["status"])

    # ── voice_calls ──
    op.create_table(
        "voice_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="twilio"),
        sa.Column("provider_call_sid", sa.String(length=80), nullable=True),
        sa.Column("direction", sa.String(length=12), nullable=False, server_default="inbound"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("caller_number", sa.String(length=32), nullable=True),
        sa.Column("receiver_number", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("end_reason", sa.String(length=60), nullable=True),
        sa.Column("detected_intent", sa.String(length=80), nullable=True),
        sa.Column("detected_language", sa.String(length=16), nullable=True),
        sa.Column("sentiment", sa.String(length=20), nullable=True),
        sa.Column("resolution", sa.String(length=40), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("interruptions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recording_url", sa.String(length=1000), nullable=True),
        sa.Column("transcript_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["campaign_id"], ["voice_campaigns.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_voice_calls_organization_id", "voice_calls", ["organization_id"])
    op.create_index("ix_voice_calls_project_id", "voice_calls", ["project_id"])
    op.create_index("ix_voice_calls_agent_id", "voice_calls", ["agent_id"])
    op.create_index("ix_voice_calls_status", "voice_calls", ["status"])
    op.create_index("ix_voice_calls_direction", "voice_calls", ["direction"])
    op.create_index("ix_voice_calls_provider_call_sid", "voice_calls", ["provider_call_sid"])
    op.create_index("ix_voice_calls_started_at", "voice_calls", ["started_at"])

    # ── voice_messages ──
    op.create_table(
        "voice_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("speaker", sa.String(length=12), nullable=False, server_default="caller"),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("start_time", sa.Float(), nullable=False, server_default="0"),
        sa.Column("end_time", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["call_id"], ["voice_calls.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_voice_messages_call_id", "voice_messages", ["call_id"])
    op.create_index("ix_voice_messages_call_seq", "voice_messages", ["call_id", "sequence"])

    # ── voice_recordings ──
    op.create_table(
        "voice_recordings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="twilio"),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="call"),
        sa.Column("storage_key", sa.String(length=1000), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("format", sa.String(length=16), nullable=False, server_default="mp3"),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["call_id"], ["voice_calls.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_voice_recordings_call_id", "voice_recordings", ["call_id"])

    # ── receptionist_profiles ──
    op.create_table(
        "receptionist_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("business_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("greeting", sa.Text(), nullable=True),
        sa.Column("after_hours_message", sa.Text(), nullable=True),
        sa.Column("voicemail_prompt", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("default_language", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("languages", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("allow_recording", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allow_voicemail", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("business_hours", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("holidays", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("routing_rules", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("appointment_settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("configuration", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("agent_id", name="uq_receptionist_profiles_agent"),
    )
    op.create_index("ix_receptionist_profiles_organization_id", "receptionist_profiles", ["organization_id"])

    # ── sales_profiles ──
    op.create_table(
        "sales_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("qualification_strategy", sa.String(length=40), nullable=False, server_default="bant"),
        sa.Column("default_pipeline", sa.String(length=120), nullable=True),
        sa.Column("crm_provider", sa.String(length=40), nullable=True),
        sa.Column("calendar_provider", sa.String(length=40), nullable=True),
        sa.Column("allow_quote_generation", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("follow_up_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("qualification_questions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("products", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("pricing_rules", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("configuration", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("agent_id", name="uq_sales_profiles_agent"),
    )
    op.create_index("ix_sales_profiles_organization_id", "sales_profiles", ["organization_id"])

    # ── support_profiles ──
    op.create_table(
        "support_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("create_tickets", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ticketing_provider", sa.String(length=40), nullable=True),
        sa.Column("escalation_rules", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("sla_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("knowledge_base_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("configuration", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("agent_id", name="uq_support_profiles_agent"),
    )
    op.create_index("ix_support_profiles_organization_id", "support_profiles", ["organization_id"])

    # ── call_transfers ──
    op.create_table(
        "call_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transfer_type", sa.String(length=20), nullable=False, server_default="warm"),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("department", sa.String(length=80), nullable=True),
        sa.Column("queue", sa.String(length=80), nullable=True),
        sa.Column("target_number", sa.String(length=32), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="requested"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wait_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context_summary", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["call_id"], ["voice_calls.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_call_transfers_call_id", "call_transfers", ["call_id"])
    op.create_index("ix_call_transfers_status", "call_transfers", ["status"])
    op.create_index("ix_call_transfers_organization_id", "call_transfers", ["organization_id"])

    # ── voice_campaign_contacts ──
    op.create_table(
        "voice_campaign_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=60), nullable=True),
        sa.Column("variables", postgresql.JSONB(), nullable=False, server_default="{}"),
        *_ts_cols(),
        sa.ForeignKeyConstraint(["campaign_id"], ["voice_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_call_id"], ["voice_calls.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_voice_campaign_contacts_campaign_id", "voice_campaign_contacts", ["campaign_id"])
    op.create_index("ix_voice_campaign_contacts_status", "voice_campaign_contacts", ["status"])


def downgrade() -> None:
    op.drop_table("voice_campaign_contacts")
    op.drop_table("call_transfers")
    op.drop_table("support_profiles")
    op.drop_table("sales_profiles")
    op.drop_table("receptionist_profiles")
    op.drop_table("voice_recordings")
    op.drop_table("voice_messages")
    op.drop_table("voice_calls")
    op.drop_table("voice_campaigns")
    op.drop_table("voice_profiles")
    op.drop_table("agent_channels")
