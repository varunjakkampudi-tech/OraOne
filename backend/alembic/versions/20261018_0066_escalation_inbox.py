"""Escalation inbox: response due time and internal notes.

Revision ID: 0066_escalation_inbox
Revises: 0065_outbox_next_attempt

Adds ``escalations.due_at`` (the team's response target) and
``escalations.internal_notes`` (team-only notes). Existing rows get a due time of
created_at plus 24 hours. Downgrade drops both columns, so notes are lost.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0066_escalation_inbox"
down_revision: Union[str, None] = "0065_outbox_next_attempt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "escalations",
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "escalations",
        sa.Column(
            "internal_notes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.execute(
        "UPDATE escalations SET due_at = created_at + INTERVAL '24 hours' WHERE due_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("escalations", "internal_notes")
    op.drop_column("escalations", "due_at")
