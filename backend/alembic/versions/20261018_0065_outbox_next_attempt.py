"""Webhook outbox: exponential backoff between delivery attempts.

Revision ID: 0065_outbox_next_attempt
Revises: 0064_escalation_notified

Adds ``webhook_outbox.next_attempt_at``. Rows without a value are due at once,
so existing pending events keep their current behaviour. Downgrade drops the
column, and pending events are retried immediately.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0065_outbox_next_attempt"
down_revision: Union[str, None] = "0064_escalation_notified"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "webhook_outbox",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("webhook_outbox", "next_attempt_at")
