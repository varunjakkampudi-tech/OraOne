"""Omnichannel: extend conversation_channel with messaging surfaces.

Phase M — one AI across every channel. ``whatsapp`` already existed; this adds
the remaining messaging/embedded surfaces so a single :class:`Conversation`
thread can carry SMS, email, social DMs, team chat and the mobile/desktop SDKs.

Only new enum *values* are added (no value is used in this migration), which
PostgreSQL 12+ permits inside the normal Alembic transaction.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0036_omnichannel"
down_revision: Union[str, None] = "0035_visitor_aliases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_VALUES = [
    "sms",
    "email",
    "messenger",
    "instagram",
    "telegram",
    "slack",
    "teams",
    "mobile",
    "desktop",
]


def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(
            f"ALTER TYPE conversation_channel ADD VALUE IF NOT EXISTS '{value}'"
        )


def downgrade() -> None:
    # PostgreSQL cannot drop enum values without recreating the type; the added
    # values are harmless if left in place, so downgrade is a no-op.
    pass
