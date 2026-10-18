"""Billing: record accepted Stripe events, and order subscription changes by event time.

Revision ID: 0070_billing_webhook_events
Revises: 0069_mkt_claimed_at

Creates ``billing_webhook_events`` (a unique Stripe event id per row, so a replayed
event is a no-op) and adds ``subscriptions.stripe_event_created_at`` (the newest applied
event time, so an older event arriving later is ignored). Existing subscriptions get NULL,
which means "no event applied yet". Downgrade drops both.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0070_billing_webhook_events"
down_revision: Union[str, None] = "0069_mkt_claimed_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_billing_webhook_events_event_id"),
    )
    op.add_column(
        "subscriptions",
        sa.Column("stripe_event_created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "stripe_event_created_at")
    op.drop_table("billing_webhook_events")
