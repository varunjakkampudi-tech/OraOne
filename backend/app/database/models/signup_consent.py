"""Consent recorded when an account is created (signup legal acceptance).

One row per document per account: the required Terms of Service and Privacy Policy
acceptances, and the optional marketing choice (recorded whether granted or declined).
Each row keeps the document version the person saw and a UTC timestamp.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin

SIGNUP_DOCUMENTS = ("terms", "privacy", "marketing")


class SignupConsent(UUIDPrimaryKeyMixin, Base):
    """A person's recorded answer to one signup document, at one version."""

    __tablename__ = "signup_consents"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "document", name="uq_signup_consents_user_document"
        ),
        CheckConstraint(
            "document IN ('terms', 'privacy', 'marketing')",
            name="ck_signup_consents_document",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
