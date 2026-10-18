"""Escalations: record which team members were already notified.

Revision ID: 0064_escalation_notified
Revises: 0063_escalations

Adds ``escalations.notified_addresses`` so a retry emails only the team members
who did not receive the first send. Downgrade drops the column, and retries
then resend to everyone.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0064_escalation_notified"
down_revision: Union[str, None] = "0063_escalations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "escalations",
        sa.Column(
            "notified_addresses",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("escalations", "notified_addresses")
