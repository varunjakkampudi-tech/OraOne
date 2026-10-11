"""User — system-of-record identity.

Authentication is self-hosted (Argon2 password hash + JWT access/refresh
tokens, see app/core/security.py and app/services/auth_service.py).
``cognito_sub`` is kept as the column name for backward compatibility with
every downstream consumer that already reads it as "the auth subject id" /
JWT ``sub`` claim, but it no longer refers to AWS Cognito — for accounts
created through the self-hosted flow it holds a freshly generated UUID.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.organization import Organization
    from app.database.models.organization_member import OrganizationMember


class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class UserStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    deleted = "deleted"


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("cognito_sub", name="uq_users_cognito_sub"),
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
    )

    cognito_sub: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(160))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Self-hosted auth (Argon2). Nullable so social/legacy rows without a
    # local password can still exist; login always requires it to be set.
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.owner,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.active,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    owned_orgs: Mapped[list["Organization"]] = relationship(
        back_populates="owner", foreign_keys="Organization.owner_user_id"
    )
    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user", foreign_keys="OrganizationMember.user_id"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"
