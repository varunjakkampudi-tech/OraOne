"""Conversation channel: ensure ``voice`` is a value of ``conversation_channel``.

Revision ID: 0055_voice_conversation_channel
Revises: 0054_do_not_contact

``voice`` is already present in the enum from the initial schema on databases
created by this repo's migrations. ``IF NOT EXISTS`` makes this a no-op there
and adds the value on any database where it is missing.

``ALTER TYPE ... ADD VALUE`` must run outside a transaction on PostgreSQL before
12 and cannot be used by statements in the same transaction, so it runs in an
autocommit block (same pattern as 0010_workflow_phase11_expansion).

Downgrade is a no-op: PostgreSQL cannot drop an enum value without rebuilding
the type, and an unused extra value is harmless.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0055_voice_conversation_channel"
down_revision: Union[str, Sequence[str], None] = "0054_do_not_contact"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE conversation_channel ADD VALUE IF NOT EXISTS 'voice'")


def downgrade() -> None:
    # Enum values cannot be removed without rebuilding the type; see module docstring.
    pass
