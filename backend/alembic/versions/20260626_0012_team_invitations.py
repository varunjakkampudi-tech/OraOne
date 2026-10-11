"""Phase 12 Module 3: team invitations.

Adds the ``organization_invitations`` table for token-based team invites.
The ``member_role`` enum already exists; only ``invitation_status`` is new.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0012_team_invitations"
down_revision: Union[str, None] = "0011_billing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    invitation_status = postgresql.ENUM(
        "pending", "accepted", "revoked", "expired", name="invitation_status"
    )
    invitation_status.create(bind, checkfirst=True)
    invitation_status.create_type = False

    # member_role already exists from the initial migration; reference it
    # without attempting to (re)create the type.
    member_role = postgresql.ENUM(
        "owner", "admin", "member", "viewer", name="member_role",
        create_type=False,
    )

    op.create_table(
        "organization_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", member_role, nullable=False, server_default="member"),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("status", invitation_status, nullable=False, server_default="pending"),
        sa.Column(
            "invited_by_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "accepted_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("token", name="uq_org_invitations_token"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_org_invitations_organization_id", "organization_invitations",
        ["organization_id"], if_not_exists=True,
    )
    op.create_index(
        "ix_org_invitations_email", "organization_invitations",
        ["email"], if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("organization_invitations")
    op.execute("DROP TYPE IF EXISTS invitation_status")
