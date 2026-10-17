"""Widget sessions: store a hash of the visitor session token.

Revision ID: 0056_widget_session_token_hash
Revises: 0055_voice_conversation_channel

The public widget API issues each visitor an unguessable session token when a
chat starts. Only its SHA-256 hex digest is stored, on the visitor's
``widget_sessions`` row. Later public calls must present the token in the
``X-Widget-Session`` header. Rows created before this migration have no hash
and therefore fail closed: their transcripts cannot be read through the
public API.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0056_widget_session_token_hash"
down_revision: Union[str, Sequence[str], None] = "0055_voice_conversation_channel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "widget_sessions",
        sa.Column("session_token_hash", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("widget_sessions", "session_token_hash")
