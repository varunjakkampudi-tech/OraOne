"""VisitorProfile — one persistent identity for a visitor/contact across ALL channels.

This is the keystone of the unified Conversational AI Platform: a single
person who chats on the website today and calls the phone number tomorrow is
the *same* :class:`VisitorProfile`. It accumulates non-sensitive shared
context and a small rolling memory so the agent "already knows them" — no
repeated questions — regardless of which channel they arrive on.

Identity resolution key (``visitor_key``) is stable per organization:
* website widget  → the browser ``visitor_id`` token,
* phone           → the normalised caller phone number,
* api / forms     → an explicit ``external_id`` or normalised email.

Conversations link to a profile via ``conversations.visitor_profile_id``.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VisitorProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "visitor_profiles"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "visitor_key", name="uq_visitor_profiles_org_key"
        ),
        Index("ix_visitor_profiles_organization_id", "organization_id"),
        Index("ix_visitor_profiles_email", "email"),
        Index("ix_visitor_profiles_phone", "phone"),
        Index("ix_visitor_profiles_last_seen_at", "last_seen_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Stable cross-channel resolution key (widget visitor token, normalised
    # phone, normalised email, or an explicit external id).
    visitor_key: Mapped[str] = mapped_column(String(160), nullable=False)

    # Identity (optional — filled in as the visitor is recognised).
    name: Mapped[Optional[str]] = mapped_column(String(160))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(40))

    # Non-sensitive context accumulated from every channel
    # (plan, company, language, last page, custom traits via SDK, …).
    shared_context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    # Channels this visitor has ever used, e.g. ["chat", "whatsapp"].
    channels_used: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Alternate resolution keys merged into this identity (other channels'
    # visitor_keys, e.g. a browser token folded into a phone-keyed profile).
    # Looked up alongside ``visitor_key`` so a person is never duplicated.
    aliases: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Rolling, capped memory of cross-channel highlights:
    # [{"channel": "chat", "role": "user", "text": "...", "at": "iso"}].
    memory: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    # Lightweight lead signals (continuity for qualification across channels).
    lead_score: Mapped[Optional[int]] = mapped_column(Integer)
    lead_status: Mapped[Optional[str]] = mapped_column(String(40))

    # Pointer to the most recent conversation on any channel. Kept FK-free to
    # avoid a circular dependency with ``conversations``.
    last_conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True)
    )
    last_channel: Mapped[Optional[str]] = mapped_column(String(20))
    conversation_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.utcnow()
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<VisitorProfile {self.visitor_key} org={self.organization_id}>"
