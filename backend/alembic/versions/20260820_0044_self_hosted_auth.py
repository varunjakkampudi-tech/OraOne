"""Self-hosted authentication — add password_hash + is_email_verified to users.

Replaces AWS Cognito as the auth-of-record. Adds the two columns the new
Argon2 + JWT auth service (app/services/auth_service.py) needs, and
backfills a password hash for the local admin account (email from
LOCAL_ADMIN_EMAIL / default admin@oraone.in, password from
LOCAL_ADMIN_PASSWORD / default "admin") if that row already exists, so
existing local deployments keep working without a manual step.
"""
from __future__ import annotations

import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0044_self_hosted_auth"
down_revision: Union[str, None] = "0043_drop_voice_platform"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )

    # Backfill the local admin account's password so existing deployments
    # don't get locked out by this migration.
    admin_email = os.environ.get("LOCAL_ADMIN_EMAIL", "admin@oraone.in").strip().lower()
    admin_password = os.environ.get("LOCAL_ADMIN_PASSWORD", "admin")
    try:
        from argon2 import PasswordHasher

        password_hash = PasswordHasher().hash(admin_password)
    except Exception:  # pragma: no cover — argon2-cffi not installed at migration time
        password_hash = None

    if password_hash:
        bind = op.get_bind()
        bind.execute(
            sa.text(
                "UPDATE users SET password_hash = :ph, is_email_verified = true "
                "WHERE lower(email) = :email AND password_hash IS NULL"
            ),
            {"ph": password_hash, "email": admin_email},
        )


def downgrade() -> None:
    op.drop_column("users", "is_email_verified")
    op.drop_column("users", "password_hash")
