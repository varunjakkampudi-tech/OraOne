"""Self-hosted authentication — add password_hash + is_email_verified to users.

Replaces AWS Cognito as the auth-of-record. Adds the two columns the new
Argon2 + JWT auth service (app/services/auth_service.py) needs. Any password
backfill is strictly opt-in: both LOCAL_ADMIN_EMAIL and LOCAL_ADMIN_PASSWORD
must be supplied by the operator. There is no fallback identity or password.
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

    # Backfill only when an operator explicitly supplies both values. Never
    # create or assume a predictable admin identity during a migration.
    admin_email = os.environ.get("LOCAL_ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("LOCAL_ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        return
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
