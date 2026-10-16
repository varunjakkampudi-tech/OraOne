"""Normalize agent models to the OpenRouter model catalogue.

Agents may still reference models that were removed from the catalogue. They
are moved to the default model so every agent resolves to a supported id.

Revision ID: 0052_model_catalogue
Revises: 0051_remove_cognito_s3
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0052_model_catalogue"
down_revision: Union[str, Sequence[str], None] = "0051_remove_cognito_s3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SUPPORTED_MODELS = (
    "openai/gpt-5.5",
    "anthropic/claude-sonnet-4",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
)


def upgrade() -> None:
    """Move agents on unsupported model ids to the default model."""
    supported = ", ".join(f"'{model}'" for model in SUPPORTED_MODELS)
    op.execute(
        f"UPDATE agents SET model = 'openai/gpt-5.5' WHERE model NOT IN ({supported})"
    )


def downgrade() -> None:
    """Data-only migration; the previous model ids are not restored."""
