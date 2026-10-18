"""Escalations: at most one unresolved item per conversation, enforced by the database.

Revision ID: 0068_escalation_one_open
Revises: 0067_mkt_project_installs

Before the unique index is created, older unresolved duplicates for the same
conversation are marked resolved (the newest one per conversation stays open).
Their resolution time is set to now and an internal note records the change.
Downgrade removes the index only.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0068_escalation_one_open"
down_revision: Union[str, None] = "0067_mkt_project_installs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY conversation_id ORDER BY created_at DESC
                   ) AS rn
            FROM escalations
            WHERE conversation_id IS NOT NULL
              AND status <> 'resolved'
        )
        UPDATE escalations AS e
        SET status = 'resolved',
            resolved_at = now(),
            internal_notes = e.internal_notes || jsonb_build_array(
                jsonb_build_object(
                    'at', to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"'),
                    'user_id', 'system',
                    'text', 'Closed as a duplicate of a newer open escalation for this conversation.'
                )
            )
        FROM ranked AS r
        WHERE e.id = r.id AND r.rn > 1
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_escalations_one_open_per_conversation
        ON escalations (conversation_id)
        WHERE conversation_id IS NOT NULL AND status <> 'resolved'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_escalations_one_open_per_conversation")
