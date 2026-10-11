"""Product 2 removal — drop the Voice Platform's exclusive tables.

OraOne Voice Platform has been discontinued; the application now focuses
exclusively on the Chat Platform. This migration drops every table that
existed *only* to support inbound/outbound AI calling. Shared omnichannel
infrastructure (``agent_channels``) is **not** touched — it is still used by
the Chat Platform's WhatsApp/SMS/website-widget channels.

This is a deliberate, one-way product removal rather than a reversible schema
tweak: ``downgrade()`` does not attempt to resurrect Voice Platform data. If a
rollback is ever required, restore from a pre-migration database backup.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0043_drop_voice_platform"
down_revision: Union[str, None] = "0042_products_entitlements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Children-before-parents order so foreign keys drop cleanly. Every table
# that has a `call_id` FK to voice_calls must be dropped before voice_calls
# itself; voice_campaign_contacts must drop before voice_campaigns.
_VOICE_TABLES: list[str] = [
    "voice_campaign_contacts",
    "call_transfers",
    "voice_messages",
    "voice_recordings",
    "voice_tickets",
    "voice_appointments",
    "voice_callbacks",
    "voice_payment_requests",
    "voice_customer_documents",
    "voice_calls",
    "voice_campaigns",
    "voice_workflow_triggers",
    "voice_suppression_entries",
    "voice_library",
    "voice_profiles",
    "receptionist_profiles",
    "sales_profiles",
    "support_profiles",
]


def upgrade() -> None:
    for table in _VOICE_TABLES:
        op.drop_table(table)

    # Retire the voice_platform product + any per-org overrides of it.
    op.execute(
        "DELETE FROM organization_entitlements WHERE product_key = 'voice_platform'"
    )
    op.execute("DELETE FROM products WHERE key = 'voice_platform'")


def downgrade() -> None:
    raise RuntimeError(
        "0043_drop_voice_platform is a one-way product removal. "
        "Restore the Voice Platform schema from a pre-migration backup "
        "instead of downgrading."
    )
