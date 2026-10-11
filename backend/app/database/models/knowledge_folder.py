"""KnowledgeFolder — nested folder to organize documents in a KB (R2).

Folders form a tree via ``parent_folder_id`` (NULL == root). Each folder
is scoped to a knowledge base (and denormalised organization) so tenant
checks stay single-table. A document references at most one folder via
``documents.folder_id``.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeFolder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_folders"
    __table_args__ = (
        Index("ix_knowledge_folders_kb", "knowledge_base_id"),
        Index("ix_knowledge_folders_org", "organization_id"),
        Index("ix_knowledge_folders_parent", "parent_folder_id"),
    )

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("knowledge_folders.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(9))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<KnowledgeFolder {self.name} kb={self.knowledge_base_id}>"
