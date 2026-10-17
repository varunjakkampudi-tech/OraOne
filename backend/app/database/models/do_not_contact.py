"""Do-not-contact list: phone numbers and email addresses an organization must not reach.

Every row carries ``organization_id``; every query must filter on it. Values are
stored normalised (see ``app.services.contact_policy_service``), so lookups are
exact matches.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ContactScope:
    all = "all"
    call = "call"
    sms = "sms"
    whatsapp = "whatsapp"
    email = "email"
    instagram = "instagram"

    ALL = ("all", "call", "sms", "whatsapp", "email", "instagram")
    #: Scopes a single outbound channel can match (``all`` always applies).
    CHANNELS = ("call", "sms", "whatsapp", "email", "instagram")


class ContactSource:
    user = "user"
    opt_out_reply = "opt_out_reply"
    import_ = "import"

    ALL = ("user", "opt_out_reply", "import")


class DoNotContact(Base):
    __tablename__ = "do_not_contact"
    __table_args__ = (
        CheckConstraint(
            "channel_scope IN ('all', 'call', 'sms', 'whatsapp', 'email', 'instagram')",
            name="ck_do_not_contact_channel_scope",
        ),
        CheckConstraint(
            "source IN ('user', 'opt_out_reply', 'import')",
            name="ck_do_not_contact_source",
        ),
        UniqueConstraint(
            "organization_id",
            "normalised_value",
            "channel_scope",
            name="uq_do_not_contact_org_value_scope",
        ),
        Index("ix_do_not_contact_organization_id", "organization_id"),
        Index("ix_do_not_contact_normalised_value", "normalised_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    normalised_value: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_scope: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ContactScope.all
    )
    reason: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
