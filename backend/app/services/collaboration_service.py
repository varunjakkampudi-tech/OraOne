"""R9 — Collaboration service.

Org-scoped business logic for teams, resource-level sharing (ACL), threaded
comments + mentions + reactions, notifications, the activity feed, task
assignment, and resource follows. Every function takes an explicit
``organization_id`` and never trusts client-supplied tenant data.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.collaboration import (
    ActivityEvent,
    Comment,
    Mention,
    Notification,
    NotificationType,
    PermissionLevel,
    PrincipalType,
    Reaction,
    ResourceFollow,
    ResourcePermission,
    Task,
    TaskStatus,
    Team,
    TeamMember,
    TeamRole,
)
from app.database.models.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _user_directory(
    session: AsyncSession, user_ids: Iterable[uuid.UUID]
) -> dict[str, dict[str, Any]]:
    """Map ``user_id -> {id, name, email, avatar_url}`` for the given ids."""
    ids = [u for u in {x for x in user_ids if x is not None}]
    if not ids:
        return {}
    rows = (
        await session.execute(
            select(User.id, User.full_name, User.email, User.avatar_url).where(User.id.in_(ids))
        )
    ).all()
    out: dict[str, dict[str, Any]] = {}
    for uid, full_name, email, avatar in rows:
        out[str(uid)] = {
            "id": str(uid),
            "name": full_name or (email.split("@")[0] if email else "Member"),
            "email": email,
            "avatar_url": avatar,
        }
    return out


# ─────────────────────────── teams ───────────────────────────
async def list_teams(session: AsyncSession, org_id: uuid.UUID) -> list[dict[str, Any]]:
    teams = (
        await session.execute(
            select(Team)
            .where(Team.organization_id == org_id, Team.deleted_at.is_(None))
            .order_by(Team.created_at.asc())
        )
    ).scalars().all()
    counts = dict(
        (
            await session.execute(
                select(TeamMember.team_id, func.count(TeamMember.id))
                .where(TeamMember.team_id.in_([t.id for t in teams]) if teams else False)
                .group_by(TeamMember.team_id)
            )
        ).all()
    )
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "description": t.description,
            "color": t.color,
            "icon": t.icon,
            "member_count": int(counts.get(t.id, 0)),
            "created_at": t.created_at,
        }
        for t in teams
    ]


async def create_team(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    name: str,
    description: Optional[str] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None,
) -> Team:
    team = Team(
        organization_id=org_id,
        name=name,
        description=description,
        color=color,
        icon=icon,
        created_by_user_id=user_id,
    )
    session.add(team)
    await session.flush()
    # creator becomes the team lead
    session.add(
        TeamMember(team_id=team.id, user_id=user_id, role=TeamRole.LEAD, joined_at=_utcnow())
    )
    await session.commit()
    await session.refresh(team)
    return team


async def get_team(
    session: AsyncSession, org_id: uuid.UUID, team_id: uuid.UUID
) -> Optional[dict[str, Any]]:
    team = await session.scalar(
        select(Team).where(
            Team.id == team_id, Team.organization_id == org_id, Team.deleted_at.is_(None)
        )
    )
    if team is None:
        return None
    members = (
        await session.execute(
            select(TeamMember).where(TeamMember.team_id == team_id).order_by(TeamMember.joined_at.asc())
        )
    ).scalars().all()
    directory = await _user_directory(session, [m.user_id for m in members])
    return {
        "id": str(team.id),
        "name": team.name,
        "description": team.description,
        "color": team.color,
        "icon": team.icon,
        "created_at": team.created_at,
        "members": [
            {
                "id": str(m.id),
                "user_id": str(m.user_id),
                "role": m.role,
                "joined_at": m.joined_at,
                "user": directory.get(str(m.user_id)),
            }
            for m in members
        ],
    }


async def update_team(
    session: AsyncSession, org_id: uuid.UUID, team_id: uuid.UUID, **fields: Any
) -> Optional[Team]:
    team = await session.scalar(
        select(Team).where(
            Team.id == team_id, Team.organization_id == org_id, Team.deleted_at.is_(None)
        )
    )
    if team is None:
        return None
    for key in ("name", "description", "color", "icon"):
        if key in fields and fields[key] is not None:
            setattr(team, key, fields[key])
    await session.commit()
    await session.refresh(team)
    return team


async def delete_team(session: AsyncSession, org_id: uuid.UUID, team_id: uuid.UUID) -> bool:
    team = await session.scalar(
        select(Team).where(
            Team.id == team_id, Team.organization_id == org_id, Team.deleted_at.is_(None)
        )
    )
    if team is None:
        return False
    team.deleted_at = _utcnow()
    await session.commit()
    return True


async def add_team_member(
    session: AsyncSession,
    org_id: uuid.UUID,
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = TeamRole.CONTRIBUTOR,
) -> Optional[TeamMember]:
    team = await session.scalar(
        select(Team).where(
            Team.id == team_id, Team.organization_id == org_id, Team.deleted_at.is_(None)
        )
    )
    if team is None:
        return None
    existing = await session.scalar(
        select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
    )
    if existing is not None:
        existing.role = role
        await session.commit()
        await session.refresh(existing)
        return existing
    member = TeamMember(team_id=team_id, user_id=user_id, role=role, joined_at=_utcnow())
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


async def remove_team_member(
    session: AsyncSession, org_id: uuid.UUID, team_id: uuid.UUID, member_id: uuid.UUID
) -> bool:
    member = await session.scalar(
        select(TeamMember)
        .join(Team, Team.id == TeamMember.team_id)
        .where(
            TeamMember.id == member_id,
            TeamMember.team_id == team_id,
            Team.organization_id == org_id,
        )
    )
    if member is None:
        return False
    await session.delete(member)
    await session.commit()
    return True


async def _team_ids_for_user(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    rows = (
        await session.execute(select(TeamMember.team_id).where(TeamMember.user_id == user_id))
    ).scalars().all()
    return [str(t) for t in rows]


# ─────────────────────────── sharing / ACL ───────────────────────────
async def share_resource(
    session: AsyncSession,
    org_id: uuid.UUID,
    granted_by: uuid.UUID,
    *,
    resource_type: str,
    resource_id: str,
    principal_type: str,
    principal_id: Optional[str],
    permission: str,
) -> ResourcePermission:
    if principal_type == PrincipalType.ORGANIZATION:
        principal_id = None
    grant = await session.scalar(
        select(ResourcePermission).where(
            ResourcePermission.organization_id == org_id,
            ResourcePermission.resource_type == resource_type,
            ResourcePermission.resource_id == resource_id,
            ResourcePermission.principal_type == principal_type,
            ResourcePermission.principal_id.is_(None)
            if principal_id is None
            else ResourcePermission.principal_id == principal_id,
        )
    )
    if grant is not None:
        grant.permission = permission
        grant.granted_by_user_id = granted_by
    else:
        grant = ResourcePermission(
            organization_id=org_id,
            resource_type=resource_type,
            resource_id=resource_id,
            principal_type=principal_type,
            principal_id=principal_id,
            permission=permission,
            granted_by_user_id=granted_by,
        )
        session.add(grant)
    await session.commit()
    await session.refresh(grant)
    return grant


async def unshare_resource(
    session: AsyncSession, org_id: uuid.UUID, grant_id: uuid.UUID
) -> bool:
    grant = await session.scalar(
        select(ResourcePermission).where(
            ResourcePermission.id == grant_id, ResourcePermission.organization_id == org_id
        )
    )
    if grant is None:
        return False
    await session.delete(grant)
    await session.commit()
    return True


async def list_permissions(
    session: AsyncSession, org_id: uuid.UUID, resource_type: str, resource_id: str
) -> list[dict[str, Any]]:
    grants = (
        await session.execute(
            select(ResourcePermission)
            .where(
                ResourcePermission.organization_id == org_id,
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id,
            )
            .order_by(ResourcePermission.created_at.asc())
        )
    ).scalars().all()
    user_ids = [
        uuid.UUID(g.principal_id)
        for g in grants
        if g.principal_type == PrincipalType.USER and g.principal_id
    ]
    directory = await _user_directory(session, user_ids)
    team_ids = [
        uuid.UUID(g.principal_id)
        for g in grants
        if g.principal_type == PrincipalType.TEAM and g.principal_id
    ]
    team_names = dict(
        (
            await session.execute(
                select(Team.id, Team.name).where(Team.id.in_(team_ids) if team_ids else False)
            )
        ).all()
    )
    out: list[dict[str, Any]] = []
    for g in grants:
        label = "Entire organization"
        if g.principal_type == PrincipalType.USER and g.principal_id:
            label = (directory.get(g.principal_id) or {}).get("name", "Member")
        elif g.principal_type == PrincipalType.TEAM and g.principal_id:
            try:
                label = team_names.get(uuid.UUID(g.principal_id), "Team")
            except (ValueError, TypeError):
                label = "Team"
        out.append(
            {
                "id": str(g.id),
                "resource_type": g.resource_type,
                "resource_id": g.resource_id,
                "principal_type": g.principal_type,
                "principal_id": g.principal_id,
                "principal_label": label,
                "permission": g.permission,
                "created_at": g.created_at,
            }
        )
    return out


async def effective_permission(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, resource_type: str, resource_id: str
) -> Optional[str]:
    """Highest permission level a user has on a resource (None if no access)."""
    team_ids = await _team_ids_for_user(session, user_id)
    conds = [
        and_(
            ResourcePermission.principal_type == PrincipalType.USER,
            ResourcePermission.principal_id == str(user_id),
        ),
        ResourcePermission.principal_type == PrincipalType.ORGANIZATION,
    ]
    if team_ids:
        conds.append(
            and_(
                ResourcePermission.principal_type == PrincipalType.TEAM,
                ResourcePermission.principal_id.in_(team_ids),
            )
        )
    grants = (
        await session.execute(
            select(ResourcePermission.permission).where(
                ResourcePermission.organization_id == org_id,
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == resource_id,
                or_(*conds),
            )
        )
    ).scalars().all()
    if not grants:
        return None
    return max(grants, key=lambda p: PermissionLevel.RANK.get(p, 0))


# ─────────────────────────── comments + reactions ───────────────────────────
async def list_comments(
    session: AsyncSession, org_id: uuid.UUID, resource_type: str, resource_id: str
) -> list[dict[str, Any]]:
    comments = (
        await session.execute(
            select(Comment)
            .where(
                Comment.organization_id == org_id,
                Comment.resource_type == resource_type,
                Comment.resource_id == resource_id,
                Comment.deleted_at.is_(None),
            )
            .order_by(Comment.created_at.asc())
        )
    ).scalars().all()
    directory = await _user_directory(session, [c.user_id for c in comments])

    def _ser(c: Comment) -> dict[str, Any]:
        return {
            "id": str(c.id),
            "parent_comment_id": str(c.parent_comment_id) if c.parent_comment_id else None,
            "user": directory.get(str(c.user_id)),
            "body": c.body,
            "resolved": c.resolved,
            "mentions": c.mentions or [],
            "created_at": c.created_at,
            "replies": [],
        }

    by_id = {str(c.id): _ser(c) for c in comments}
    roots: list[dict[str, Any]] = []
    for c in comments:
        node = by_id[str(c.id)]
        parent = by_id.get(str(c.parent_comment_id)) if c.parent_comment_id else None
        if parent is not None:
            parent["replies"].append(node)
        else:
            roots.append(node)
    return roots


async def create_comment(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    resource_type: str,
    resource_id: str,
    body: str,
    parent_comment_id: Optional[uuid.UUID] = None,
    mention_user_ids: Optional[list[str]] = None,
) -> Comment:
    mention_user_ids = mention_user_ids or []
    comment = Comment(
        organization_id=org_id,
        resource_type=resource_type,
        resource_id=resource_id,
        parent_comment_id=parent_comment_id,
        user_id=user_id,
        body=body,
        mentions=mention_user_ids,
    )
    session.add(comment)
    await session.flush()

    actor = await _user_directory(session, [user_id])
    actor_name = (actor.get(str(user_id)) or {}).get("name", "Someone")
    link = f"/app/{resource_type}s"

    for raw in mention_user_ids:
        try:
            muid = uuid.UUID(str(raw))
        except (ValueError, TypeError):
            continue
        if muid == user_id:
            continue
        session.add(Mention(comment_id=comment.id, organization_id=org_id, mentioned_user_id=muid))
        session.add(
            Notification(
                organization_id=org_id,
                user_id=muid,
                type=NotificationType.MENTION,
                title=f"{actor_name} mentioned you",
                body=body[:280],
                link=link,
                actor_user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        )

    # notify followers of the resource (except the author + already-mentioned)
    follower_ids = await _follower_user_ids(session, resource_type, resource_id)
    notified = {str(user_id)} | {str(m) for m in mention_user_ids}
    for fid in follower_ids:
        if str(fid) in notified:
            continue
        session.add(
            Notification(
                organization_id=org_id,
                user_id=fid,
                type=NotificationType.COMMENT,
                title=f"{actor_name} commented",
                body=body[:280],
                link=link,
                actor_user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        )

    await log_activity(
        session,
        org_id,
        user_id,
        action="commented",
        summary=f"{actor_name} commented on a {resource_type}",
        resource_type=resource_type,
        resource_id=resource_id,
        commit=False,
    )
    await session.commit()
    await session.refresh(comment)
    return comment


async def resolve_comment(
    session: AsyncSession, org_id: uuid.UUID, comment_id: uuid.UUID, resolved: bool
) -> Optional[Comment]:
    comment = await session.scalar(
        select(Comment).where(
            Comment.id == comment_id,
            Comment.organization_id == org_id,
            Comment.deleted_at.is_(None),
        )
    )
    if comment is None:
        return None
    comment.resolved = resolved
    await session.commit()
    await session.refresh(comment)
    return comment


async def toggle_reaction(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    resource_type: str,
    resource_id: str,
    emoji: str,
) -> dict[str, Any]:
    existing = await session.scalar(
        select(Reaction).where(
            Reaction.organization_id == org_id,
            Reaction.resource_type == resource_type,
            Reaction.resource_id == resource_id,
            Reaction.user_id == user_id,
            Reaction.emoji == emoji,
        )
    )
    if existing is not None:
        await session.delete(existing)
        await session.commit()
        active = False
    else:
        session.add(
            Reaction(
                organization_id=org_id,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                emoji=emoji,
            )
        )
        await session.commit()
        active = True
    counts = await list_reactions(session, org_id, resource_type, resource_id)
    return {"active": active, "reactions": counts}


async def list_reactions(
    session: AsyncSession, org_id: uuid.UUID, resource_type: str, resource_id: str
) -> dict[str, int]:
    rows = (
        await session.execute(
            select(Reaction.emoji, func.count(Reaction.id))
            .where(
                Reaction.organization_id == org_id,
                Reaction.resource_type == resource_type,
                Reaction.resource_id == resource_id,
            )
            .group_by(Reaction.emoji)
        )
    ).all()
    return {emoji: int(n) for emoji, n in rows}


# ─────────────────────────── notifications ───────────────────────────
async def notify(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    type: str,
    title: str,
    body: Optional[str] = None,
    link: Optional[str] = None,
    actor_user_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    commit: bool = True,
) -> Notification:
    notif = Notification(
        organization_id=org_id,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        link=link,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    session.add(notif)
    if commit:
        await session.commit()
        await session.refresh(notif)
    return notif


async def list_notifications(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    unread_only: bool = False,
    limit: int = 50,
) -> dict[str, Any]:
    stmt = (
        select(Notification)
        .where(Notification.organization_id == org_id, Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    rows = (await session.execute(stmt)).scalars().all()
    actor_ids = [n.actor_user_id for n in rows if n.actor_user_id]
    directory = await _user_directory(session, actor_ids)
    unread = await unread_count(session, org_id, user_id)
    return {
        "unread_count": unread,
        "notifications": [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "link": n.link,
                "actor": directory.get(str(n.actor_user_id)) if n.actor_user_id else None,
                "resource_type": n.resource_type,
                "resource_id": n.resource_id,
                "read": n.read_at is not None,
                "created_at": n.created_at,
            }
            for n in rows
        ],
    }


async def unread_count(session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.count(Notification.id)).where(
                Notification.organization_id == org_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )


async def mark_notification_read(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, notif_id: uuid.UUID
) -> bool:
    notif = await session.scalar(
        select(Notification).where(
            Notification.id == notif_id,
            Notification.organization_id == org_id,
            Notification.user_id == user_id,
        )
    )
    if notif is None:
        return False
    if notif.read_at is None:
        notif.read_at = _utcnow()
        await session.commit()
    return True


async def mark_all_read(session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> int:
    rows = (
        await session.execute(
            select(Notification).where(
                Notification.organization_id == org_id,
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
        )
    ).scalars().all()
    now = _utcnow()
    for n in rows:
        n.read_at = now
    await session.commit()
    return len(rows)


# ─────────────────────────── activity feed ───────────────────────────
async def log_activity(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    *,
    action: str,
    summary: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
    commit: bool = True,
) -> ActivityEvent:
    event = ActivityEvent(
        organization_id=org_id,
        user_id=user_id,
        action=action,
        summary=summary,
        resource_type=resource_type,
        resource_id=resource_id,
        meta=meta or {},
    )
    session.add(event)
    if commit:
        await session.commit()
        await session.refresh(event)
    return event


async def list_activity(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    limit: int = 50,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    stmt = (
        select(ActivityEvent)
        .where(ActivityEvent.organization_id == org_id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(limit)
    )
    if resource_type:
        stmt = stmt.where(ActivityEvent.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(ActivityEvent.resource_id == resource_id)
    rows = (await session.execute(stmt)).scalars().all()
    directory = await _user_directory(session, [e.user_id for e in rows if e.user_id])
    return [
        {
            "id": str(e.id),
            "action": e.action,
            "summary": e.summary,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "actor": directory.get(str(e.user_id)) if e.user_id else None,
            "meta": e.meta or {},
            "created_at": e.created_at,
        }
        for e in rows
    ]


# ─────────────────────────── tasks ───────────────────────────
async def create_task(
    session: AsyncSession,
    org_id: uuid.UUID,
    created_by: uuid.UUID,
    *,
    title: str,
    description: Optional[str] = None,
    assignee_user_id: Optional[uuid.UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    comment_id: Optional[uuid.UUID] = None,
    due_at: Optional[datetime] = None,
) -> Task:
    task = Task(
        organization_id=org_id,
        title=title,
        description=description,
        assignee_user_id=assignee_user_id,
        created_by_user_id=created_by,
        resource_type=resource_type,
        resource_id=resource_id,
        comment_id=comment_id,
        due_at=due_at,
    )
    session.add(task)
    await session.flush()
    if assignee_user_id and assignee_user_id != created_by:
        actor = await _user_directory(session, [created_by])
        actor_name = (actor.get(str(created_by)) or {}).get("name", "Someone")
        await notify(
            session,
            org_id,
            assignee_user_id,
            type=NotificationType.TASK_ASSIGNED,
            title=f"{actor_name} assigned you a task",
            body=title,
            link="/app/tasks",
            actor_user_id=created_by,
            resource_type=resource_type,
            resource_id=resource_id,
            commit=False,
        )
    await session.commit()
    await session.refresh(task)
    return task


async def list_tasks(
    session: AsyncSession,
    org_id: uuid.UUID,
    *,
    assignee_user_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    stmt = (
        select(Task)
        .where(Task.organization_id == org_id)
        .order_by(Task.created_at.desc())
        .limit(limit)
    )
    if assignee_user_id:
        stmt = stmt.where(Task.assignee_user_id == assignee_user_id)
    if status:
        stmt = stmt.where(Task.status == status)
    rows = (await session.execute(stmt)).scalars().all()
    ids = [t.assignee_user_id for t in rows if t.assignee_user_id] + [
        t.created_by_user_id for t in rows if t.created_by_user_id
    ]
    directory = await _user_directory(session, ids)
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "assignee": directory.get(str(t.assignee_user_id)) if t.assignee_user_id else None,
            "created_by": directory.get(str(t.created_by_user_id)) if t.created_by_user_id else None,
            "resource_type": t.resource_type,
            "resource_id": t.resource_id,
            "due_at": t.due_at,
            "completed_at": t.completed_at,
            "created_at": t.created_at,
        }
        for t in rows
    ]


async def update_task(
    session: AsyncSession, org_id: uuid.UUID, task_id: uuid.UUID, **fields: Any
) -> Optional[Task]:
    task = await session.scalar(
        select(Task).where(Task.id == task_id, Task.organization_id == org_id)
    )
    if task is None:
        return None
    if "title" in fields and fields["title"]:
        task.title = fields["title"]
    if "description" in fields and fields["description"] is not None:
        task.description = fields["description"]
    if fields.get("assignee_user_id") is not None:
        task.assignee_user_id = fields["assignee_user_id"]
    if "status" in fields and fields["status"] in TaskStatus.ALL:
        task.status = fields["status"]
        if fields["status"] == TaskStatus.DONE:
            task.completed_at = _utcnow()
        else:
            task.completed_at = None
    await session.commit()
    await session.refresh(task)
    return task


# ─────────────────────────── follows ───────────────────────────
async def follow_resource(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    resource_type: str,
    resource_id: str,
) -> bool:
    existing = await session.scalar(
        select(ResourceFollow).where(
            ResourceFollow.user_id == user_id,
            ResourceFollow.resource_type == resource_type,
            ResourceFollow.resource_id == resource_id,
        )
    )
    if existing is not None:
        return True
    session.add(
        ResourceFollow(
            organization_id=org_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    )
    await session.commit()
    return True


async def unfollow_resource(
    session: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    resource_type: str,
    resource_id: str,
) -> bool:
    await session.execute(
        delete(ResourceFollow).where(
            ResourceFollow.user_id == user_id,
            ResourceFollow.resource_type == resource_type,
            ResourceFollow.resource_id == resource_id,
        )
    )
    await session.commit()
    return True


async def list_follows(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            select(ResourceFollow)
            .where(ResourceFollow.organization_id == org_id, ResourceFollow.user_id == user_id)
            .order_by(ResourceFollow.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": str(f.id),
            "resource_type": f.resource_type,
            "resource_id": f.resource_id,
            "created_at": f.created_at,
        }
        for f in rows
    ]


async def _follower_user_ids(
    session: AsyncSession, resource_type: str, resource_id: str
) -> list[uuid.UUID]:
    return (
        await session.execute(
            select(ResourceFollow.user_id).where(
                ResourceFollow.resource_type == resource_type,
                ResourceFollow.resource_id == resource_id,
            )
        )
    ).scalars().all()


# ─────────────────────────── workspace overview ───────────────────────────
async def workspace_overview(
    session: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID
) -> dict[str, Any]:
    teams = int(
        await session.scalar(
            select(func.count(Team.id)).where(
                Team.organization_id == org_id, Team.deleted_at.is_(None)
            )
        )
        or 0
    )
    shared = int(
        await session.scalar(
            select(func.count(func.distinct(ResourcePermission.resource_id))).where(
                ResourcePermission.organization_id == org_id
            )
        )
        or 0
    )
    comments = int(
        await session.scalar(
            select(func.count(Comment.id)).where(
                Comment.organization_id == org_id, Comment.deleted_at.is_(None)
            )
        )
        or 0
    )
    open_tasks = int(
        await session.scalar(
            select(func.count(Task.id)).where(
                Task.organization_id == org_id,
                Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_PROGRESS]),
            )
        )
        or 0
    )
    my_tasks = int(
        await session.scalar(
            select(func.count(Task.id)).where(
                Task.organization_id == org_id,
                Task.assignee_user_id == user_id,
                Task.status.in_([TaskStatus.OPEN, TaskStatus.IN_PROGRESS]),
            )
        )
        or 0
    )
    unread = await unread_count(session, org_id, user_id)
    recent = await list_activity(session, org_id, limit=8)
    return {
        "totals": {
            "teams": teams,
            "shared_resources": shared,
            "comments": comments,
            "open_tasks": open_tasks,
            "my_open_tasks": my_tasks,
            "unread_notifications": unread,
        },
        "recent_activity": recent,
    }
