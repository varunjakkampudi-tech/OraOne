"""ConversationFolder — user-owned folder to organize chat threads (R1).

Folders are flat (one level) and scoped to both organization and the
owning user, mirroring the isolation model of AI chat threads. A
conversation references at most one folder via ``conversations.folder_id``.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # pragma: no cover
    pass


class ConversationFolder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "conversation_folders"
    __table_args__ = (
        Index("ix_conversation_folders_org_user", "organization_id", "user_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(9))
    icon: Mapped[Optional[str]] = mapped_column(String(40))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ConversationFolder {self.name} user={self.user_id}>"
