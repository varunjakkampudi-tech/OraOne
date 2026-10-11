"""Project — a workspace within an Organization.

A **Project** sits between the Organization (the company / tenant) and all
operational resources (agents, knowledge bases, conversations, workflows,
websites, widgets, integrations, webhooks, API keys, analytics).

Rationale: as soon as a customer runs multiple businesses, products, or
departments, keeping every resource flat at the org level becomes
unmanageable and risks cross-contamination (e.g. a Construction agent
retrieving Insurance documents from a shared vector index). Projects give
each business line an isolated namespace while the Organization remains the
billing / membership / settings boundary.

Every org has at least one Project. On migration, a single ``Default``
project is created per existing org and all existing resources are
back-filled onto it (``is_default = True``). The default project cannot be
deleted.
"""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.organization import Organization
    from app.database.models.user import User


class ProjectStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class Project(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """An isolated workspace for one business / product / department."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_projects_org_slug"),
        Index("ix_projects_organization_id", "organization_id"),
        Index("ix_projects_status", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        nullable=False,
        default=ProjectStatus.active,
        server_default=ProjectStatus.active.value,
    )

    # UI affordances for the project switcher.
    color: Mapped[Optional[str]] = mapped_column(String(20))
    icon: Mapped[Optional[str]] = mapped_column(String(40))

    # Exactly one project per org carries ``is_default = True``. It is
    # auto-selected when no ``X-Project-Id`` is supplied and cannot be
    # deleted.
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="projects")
    created_by: Mapped[Optional["User"]] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Project {self.slug} org={self.organization_id}>"
