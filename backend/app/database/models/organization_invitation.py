"""OrganizationInvitation — pending team invites (Phase 12, Module 3).

Invites are token-based: since the platform has no email service yet, the
backend mints a secure token and the frontend surfaces a shareable
``/app/invite/{token}`` link. A signed-in user whose email matches the
invite can accept it to join the organisation.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.models.organization_member import MemberRole

if TYPE_CHECKING:
    from app.database.models.organization import Organization
    from app.database.models.user import User


class InvitationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    revoked = "revoked"
    expired = "expired"


class OrganizationInvitation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_invitations"
    __table_args__ = (
        UniqueConstraint("token", name="uq_org_invitations_token"),
        Index("ix_org_invitations_organization_id", "organization_id"),
        Index("ix_org_invitations_email", "email"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[MemberRole] = mapped_column(
        Enum(MemberRole, name="member_role"),
        nullable=False,
        default=MemberRole.member,
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, name="invitation_status"),
        nullable=False,
        default=InvitationStatus.pending,
    )

    invited_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    accepted_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    organization: Mapped["Organization"] = relationship()
    invited_by: Mapped[Optional["User"]] = relationship(
        foreign_keys=[invited_by_user_id]
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrgInvitation org={self.organization_id} email={self.email} status={self.status}>"
