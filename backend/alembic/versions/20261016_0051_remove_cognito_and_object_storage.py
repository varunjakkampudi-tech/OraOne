"""Rename identity and storage columns after removing Cognito and S3.

Also normalizes stored agent model ids to their OpenRouter form.

Users are identified by ``auth_subject`` (the subject claim of OraOne's own
access tokens) instead of ``cognito_sub``. Document bytes are stored on local
disk, so ``s3_key`` becomes the neutral ``storage_key``. The data itself is
unchanged: only the names move.

Revision ID: 0051_remove_cognito_s3
Revises: 0050_webhook_delivery_identity
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0051_remove_cognito_s3"
down_revision: Union[str, Sequence[str], None] = "0050_webhook_delivery_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename the subject column, its unique constraint, and the storage keys."""
    op.alter_column("users", "cognito_sub", new_column_name="auth_subject")
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT uq_users_cognito_sub TO uq_users_auth_subject"
    )
    op.alter_column("documents", "s3_key", new_column_name="storage_key")
    op.alter_column("document_versions", "s3_key", new_column_name="storage_key")
    # Agents created before the OpenRouter switch stored bare OpenAI ids.
    op.execute(
        "UPDATE agents SET model = 'openai/gpt-4o-mini' WHERE model = 'gpt-4o-mini'"
    )


def downgrade() -> None:
    """Restore the original Cognito-era column names and model ids."""
    op.execute(
        "UPDATE agents SET model = 'gpt-4o-mini' WHERE model = 'openai/gpt-4o-mini'"
    )
    op.alter_column("document_versions", "storage_key", new_column_name="s3_key")
    op.alter_column("documents", "storage_key", new_column_name="s3_key")
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT uq_users_auth_subject TO uq_users_cognito_sub"
    )
    op.alter_column("users", "auth_subject", new_column_name="cognito_sub")
