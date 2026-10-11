"""R9 — Enterprise Team Collaboration models.

Turns OraOne from a per-user assistant into a shared workspace: teams
(departments) inside an organization, resource-level ACLs (owner / editor /
commenter / viewer like Google Docs), threaded comments + reactions, mentions,
notifications, an org-wide activity feed, task assignment, and resource follows.

Every table is strictly org-scoped; repositories MUST filter by
``organization_id``.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


# ─────────────────────────── enumerations ───────────────────────────
class TeamRole:
    """A member's role *within a team* (distinct from org-level role)."""

    LEAD = "lead"
    EDITOR = "editor"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"
    ALL = (LEAD, EDITOR, CONTRIBUTOR, VIEWER)


class ResourceType:
    """Every shareable / commentable object family in OraOne."""

    CONVERSATION = "conversation"
    AGENT = "agent"
    KNOWLEDGE_BASE = "knowledge_base"
    DOCUMENT = "document"
    FOLDER = "folder"
    WORKFLOW = "workflow"
    WIDGET = "widget"
    PROMPT = "prompt"
    DASHBOARD = "dashboard"
    ALL = (
        CONVERSATION,
        AGENT,
        KNOWLEDGE_BASE,
        DOCUMENT,
        FOLDER,
        WORKFLOW,
        WIDGET,
        PROMPT,
        DASHBOARD,
    )


class PrincipalType:
    """Who a permission is granted to."""

    USER = "user"
    TEAM = "team"
    ORGANIZATION = "organization"
    ALL = (USER, TEAM, ORGANIZATION)


class PermissionLevel:
    """Resource-level access tiers (à la Google Docs)."""

    OWNER = "owner"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"
    ALL = (OWNER, EDITOR, COMMENTER, VIEWER)
    #: ordering for "highest wins" resolution
    RANK = {VIEWER: 1, COMMENTER: 2, EDITOR: 3, OWNER: 4}


class NotificationType:
    MENTION = "mention"
    COMMENT = "comment"
    SHARE = "share"
    TASK_ASSIGNED = "task_assigned"
    WORKFLOW_FINISHED = "workflow_finished"
    KNOWLEDGE_UPDATED = "knowledge_updated"
    DOCUMENT_PROCESSED = "document_processed"
    AGENT_CHANGED = "agent_changed"
    TEAM_INVITE = "team_invite"
    ALL = (
        MENTION,
        COMMENT,
        SHARE,
        TASK_ASSIGNED,
        WORKFLOW_FINISHED,
        KNOWLEDGE_UPDATED,
        DOCUMENT_PROCESSED,
        AGENT_CHANGED,
        TEAM_INVITE,
    )


class TaskStatus:
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"
    ALL = (OPEN, IN_PROGRESS, DONE, CANCELLED)


# ─────────────────────────── teams ───────────────────────────
class Team(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A department / squad inside an organization."""

    __tablename__ = "teams"
    __table_args__ = (
        Index("ix_teams_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan", passive_deletes=True
    )


class TeamMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        Index("ix_team_members_team_id", "team_id"),
        Index("ix_team_members_user_id", "user_id"),
    )

    team_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TeamRole.CONTRIBUTOR, server_default=TeamRole.CONTRIBUTOR
    )
    joined_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    team: Mapped["Team"] = relationship(back_populates="members")


# ─────────────────────────── resource ACL ───────────────────────────
class ResourcePermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single grant: (resource) → (principal) @ (permission level)."""

    __tablename__ = "resource_permissions"
    __table_args__ = (
        UniqueConstraint(
            "resource_type",
            "resource_id",
            "principal_type",
            "principal_id",
            name="uq_resource_permissions_grant",
        ),
        Index("ix_resource_permissions_org", "organization_id"),
        Index("ix_resource_permissions_resource", "resource_type", "resource_id"),
        Index("ix_resource_permissions_principal", "principal_type", "principal_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # NULL principal_id == the whole organization (PrincipalType.ORGANIZATION)
    principal_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    permission: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PermissionLevel.VIEWER, server_default=PermissionLevel.VIEWER
    )
    granted_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


# ─────────────────────────── comments + reactions ───────────────────────────
class Comment(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_org", "organization_id"),
        Index("ix_comments_resource", "resource_type", "resource_id"),
        Index("ix_comments_parent", "parent_comment_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False)
    parent_comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Denormalised list of mentioned user-ids (also expanded into mentions table).
    mentions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")


class Mention(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mentions"
    __table_args__ = (
        Index("ix_mentions_comment", "comment_id"),
        Index("ix_mentions_user", "mentioned_user_id"),
    )

    comment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    mentioned_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class Reaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An emoji reaction on a resource (e.g. an AI message): 👍 👎 ❤️ 🎉."""

    __tablename__ = "reactions"
    __table_args__ = (
        UniqueConstraint(
            "resource_type", "resource_id", "user_id", "emoji",
            name="uq_reactions_unique",
        ),
        Index("ix_reactions_org", "organization_id"),
        Index("ix_reactions_resource", "resource_type", "resource_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    emoji: Mapped[str] = mapped_column(String(16), nullable=False)


# ─────────────────────────── notifications ───────────────────────────
class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user", "user_id"),
        Index("ix_notifications_org", "organization_id"),
        Index("ix_notifications_read", "read_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resource_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ─────────────────────────── activity feed ───────────────────────────
class ActivityEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activity_feed"
    __table_args__ = (
        Index("ix_activity_feed_org", "organization_id"),
        Index("ix_activity_feed_created", "created_at"),
        Index("ix_activity_feed_resource", "resource_type", "resource_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")


# ─────────────────────────── tasks ───────────────────────────
class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_org", "organization_id"),
        Index("ix_tasks_assignee", "assignee_user_id"),
        Index("ix_tasks_status", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TaskStatus.OPEN, server_default=TaskStatus.OPEN
    )
    assignee_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    comment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("comments.id", ondelete="SET NULL"), nullable=True
    )
    resource_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


# ─────────────────────────── follows ───────────────────────────
class ResourceFollow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user "watching" a resource — receives notifications on updates."""

    __tablename__ = "resource_follows"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "resource_type", "resource_id",
            name="uq_resource_follows_unique",
        ),
        Index("ix_resource_follows_org", "organization_id"),
        Index("ix_resource_follows_resource", "resource_type", "resource_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(80), nullable=False)
