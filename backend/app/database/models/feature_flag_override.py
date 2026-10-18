"""Runtime overrides for beta feature flags.

Flag definitions live in code (``app.services.feature_flags``). This table only
stores changes made by super-admins at runtime: an organisation-level switch,
or a cohort-member switch keyed by a pseudonymous email hash. Plain emails are
never stored.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin


class FeatureFlagOverride(UUIDPrimaryKeyMixin, Base):
    """One override for one flag at one scope."""

    __tablename__ = "feature_flag_overrides"
    __table_args__ = (
        UniqueConstraint(
            "flag_key",
            "scope",
            "scope_value",
            name="uq_feature_flag_overrides_key_scope",
        ),
        CheckConstraint(
            "scope IN ('organization', 'cohort_member')",
            name="ck_feature_flag_overrides_scope",
        ),
    )

    flag_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(24), nullable=False)
    scope_value: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<FeatureFlagOverride {self.flag_key} {self.scope}>"
