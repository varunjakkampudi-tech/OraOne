"""Distributed crawler — frontier queue + tuning/telemetry columns.

Turns the single-process crawler into a distributed, resumable one:

* New ``crawl_frontier`` table — a durable, lockable URL queue so multiple
  workers can cooperate (``FOR UPDATE SKIP LOCKED``) and a crawl can be paused
  and resumed without losing its place.
* ``websites`` gains ``render_js``, ``crawl_delay_ms``, ``max_concurrency``.
* ``crawl_jobs`` gains ``worker_count``, ``concurrency``, ``frontier_size``,
  ``heartbeat_at`` for live engine telemetry.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0027_distributed_crawler"
down_revision: Union[str, None] = "0026_ai_model_policy_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── websites: crawl tuning ──
    op.add_column("websites", sa.Column("render_js", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("websites", sa.Column("crawl_delay_ms", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("websites", sa.Column("max_concurrency", sa.Integer(), nullable=False, server_default="0"))

    # ── crawl_jobs: engine telemetry ──
    op.add_column("crawl_jobs", sa.Column("worker_count", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("crawl_jobs", sa.Column("concurrency", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crawl_jobs", sa.Column("frontier_size", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("crawl_jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))

    # ── crawl_frontier: the distributed URL queue ──
    op.create_table(
        "crawl_frontier",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claimed_by", sa.String(length=64), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_id"], ["crawl_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["website_id"], ["websites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("job_id", "url", name="uq_crawl_frontier_job_url"),
    )
    op.create_index("ix_crawl_frontier_job_status", "crawl_frontier", ["job_id", "status"])
    op.create_index("ix_crawl_frontier_website_id", "crawl_frontier", ["website_id"])


def downgrade() -> None:
    op.drop_index("ix_crawl_frontier_website_id", table_name="crawl_frontier")
    op.drop_index("ix_crawl_frontier_job_status", table_name="crawl_frontier")
    op.drop_table("crawl_frontier")

    op.drop_column("crawl_jobs", "heartbeat_at")
    op.drop_column("crawl_jobs", "frontier_size")
    op.drop_column("crawl_jobs", "concurrency")
    op.drop_column("crawl_jobs", "worker_count")

    op.drop_column("websites", "max_concurrency")
    op.drop_column("websites", "crawl_delay_ms")
    op.drop_column("websites", "render_js")
