"""Do-not-contact list: organization-wide phone and email suppression.

Revision ID: 0054_do_not_contact
Revises: 0053_outbound_call_campaigns

One row per (organization, normalised phone or email, channel scope). ``all``
blocks every channel; a single channel blocks only that channel. Entries come
from users, STOP-style replies, or imports.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0054_do_not_contact"
down_revision: Union[str, Sequence[str], None] = "0053_outbound_call_campaigns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "do_not_contact",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("normalised_value", sa.String(255), nullable=False),
        sa.Column("channel_scope", sa.String(16), nullable=False, server_default="all"),
        sa.Column("reason", sa.String(200), nullable=False, server_default=""),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "channel_scope IN ('all', 'call', 'sms', 'whatsapp', 'email', 'instagram')",
            name="ck_do_not_contact_channel_scope",
        ),
        sa.CheckConstraint(
            "source IN ('user', 'opt_out_reply', 'import')",
            name="ck_do_not_contact_source",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "normalised_value",
            "channel_scope",
            name="uq_do_not_contact_org_value_scope",
        ),
    )
    op.create_index(
        "ix_do_not_contact_organization_id", "do_not_contact", ["organization_id"]
    )
    op.create_index(
        "ix_do_not_contact_normalised_value", "do_not_contact", ["normalised_value"]
    )


def downgrade() -> None:
    op.drop_index("ix_do_not_contact_normalised_value", table_name="do_not_contact")
    op.drop_index("ix_do_not_contact_organization_id", table_name="do_not_contact")
    op.drop_table("do_not_contact")
