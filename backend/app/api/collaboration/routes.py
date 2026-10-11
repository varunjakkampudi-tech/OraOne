"""R9 — Enterprise Team Collaboration API (dashboard, Cognito-auth).

Teams, resource-level sharing (ACL), threaded comments + mentions + reactions,
notifications, activity feed, task assignment, and resource follows. All
endpoints are strictly org-scoped via ``OrgContext``.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.models.collaboration import PermissionLevel, PrincipalType, ResourceType
from app.database.models.organization_member import MemberStatus, OrganizationMember
from app.database.models.user import User
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_permission,
)
from app.schemas.collaboration import (
    CommentCreateRequest,
    CommentResolveRequest,
    FollowRequest,
    ReactionRequest,
    ShareRequest,
    TaskCreateRequest,
    TaskUpdateRequest,
    TeamCreateRequest,
    TeamMemberAddRequest,
    TeamUpdateRequest,
)
from app.services import collaboration_service as collab
from app.services.audit import audit

router = APIRouter(tags=["collaboration"])


# ─────────────────────────── catalog / directory ───────────────────────────
@router.get("/api/collab/meta")
async def collab_meta(
    ctx: OrgContext = Depends(get_current_organization),
) -> dict:
    """Static catalogues used by the collaboration UI."""
    return {
        "resource_types": list(ResourceType.ALL),
        "permission_levels": list(PermissionLevel.ALL),
        "principal_types": list(PrincipalType.ALL),
        "emojis": ["👍", "👎", "❤️", "🎉", "🚀", "👀"],
    }


@router.get("/api/collab/members")
async def list_org_members(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """All active org members — for mention pickers and share dialogs."""
    rows = (
        await session.execute(
            select(User.id, User.full_name, User.email, User.avatar_url, OrganizationMember.role)
            .join(OrganizationMember, OrganizationMember.user_id == User.id)
            .where(
                OrganizationMember.organization_id == ctx.organization_id,
                OrganizationMember.status == MemberStatus.active,
            )
            .order_by(User.full_name.asc().nullslast())
        )
    ).all()
    return {
        "members": [
            {
                "user_id": str(uid),
                "name": full_name or (email.split("@")[0] if email else "Member"),
                "email": email,
                "avatar_url": avatar,
                "role": role.value if hasattr(role, "value") else role,
            }
            for uid, full_name, email, avatar, role in rows
        ]
    }


@router.get("/api/collab/workspace")
async def workspace_overview(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await collab.workspace_overview(session, ctx.organization_id, ctx.user_id)


# ─────────────────────────── teams ───────────────────────────
@router.get("/api/teams")
async def list_teams(
    ctx: OrgContext = Depends(require_permission(Permission.TEAM_READ)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return {"teams": await collab.list_teams(session, ctx.organization_id)}


@router.post("/api/teams", status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreateRequest,
    ctx: OrgContext = Depends(require_permission(Permission.TEAM_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    team = await collab.create_team(
        session,
        ctx.organization_id,
        ctx.user_id,
        name=payload.name,
        description=payload.description,
        color=payload.color,
        icon=payload.icon,
    )
    await collab.log_activity(
        session,
        ctx.organization_id,
        ctx.user_id,
        action="team_created",
        summary=f"Created team '{team.name}'",
        resource_type="team",
        resource_id=str(team.id),
    )
    audit(
        "create",
        resource="team",
        resource_id=str(team.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"name": team.name},
    )
    return await collab.get_team(session, ctx.organization_id, team.id)


@router.get("/api/teams/{team_id}")
async def get_team(
    team_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.TEAM_READ)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    team = await collab.get_team(session, ctx.organization_id, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    return team


@router.put("/api/teams/{team_id}")
async def update_team(
    team_id: uuid.UUID,
    payload: TeamUpdateRequest,
    ctx: OrgContext = Depends(require_permission(Permission.TEAM_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    team = await collab.update_team(
        session, ctx.organization_id, team_id, **payload.model_dump(exclude_none=True)
    )
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    return await collab.get_team(session, ctx.organization_id, team_id)


@router.delete("/api/teams/{team_id}")
async def delete_team(
    team_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.TEAM_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    ok = await collab.delete_team(session, ctx.organization_id, team_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Team not found.")
    audit(
        "delete",
        resource="team",
        resource_id=str(team_id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return {"status": "deleted", "id": str(team_id)}


@router.post("/api/teams/{team_id}/members", status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: uuid.UUID,
    payload: TeamMemberAddRequest,
    ctx: OrgContext = Depends(require_permission(Permission.TEAM_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    member = await collab.add_team_member(
        session, ctx.organization_id, team_id, payload.user_id, payload.role
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    return await collab.get_team(session, ctx.organization_id, team_id)


@router.delete("/api/teams/{team_id}/members/{member_id}")
async def remove_team_member(
    team_id: uuid.UUID,
    member_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.TEAM_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    ok = await collab.remove_team_member(session, ctx.organization_id, team_id, member_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Member not found.")
    return {"status": "removed", "id": str(member_id)}


# ─────────────────────────── sharing / ACL ───────────────────────────
@router.post("/api/collab/share", status_code=status.HTTP_201_CREATED)
async def share_resource(
    payload: ShareRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if payload.permission not in PermissionLevel.ALL:
        raise HTTPException(status_code=422, detail="Invalid permission level.")
    if payload.principal_type not in PrincipalType.ALL:
        raise HTTPException(status_code=422, detail="Invalid principal type.")
    grant = await collab.share_resource(
        session,
        ctx.organization_id,
        ctx.user_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        principal_type=payload.principal_type,
        principal_id=payload.principal_id,
        permission=payload.permission,
    )
    # notify a specific user they were granted access
    if payload.principal_type == PrincipalType.USER and payload.principal_id:
        try:
            await collab.notify(
                session,
                ctx.organization_id,
                uuid.UUID(payload.principal_id),
                type="share",
                title="A resource was shared with you",
                body=f"You now have {payload.permission} access to a {payload.resource_type}.",
                link=f"/app/{payload.resource_type}s",
                actor_user_id=ctx.user_id,
                resource_type=payload.resource_type,
                resource_id=payload.resource_id,
            )
        except (ValueError, TypeError):
            pass
    await collab.log_activity(
        session,
        ctx.organization_id,
        ctx.user_id,
        action="shared",
        summary=f"Shared a {payload.resource_type} ({payload.permission})",
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    audit(
        "share",
        resource=payload.resource_type,
        resource_id=payload.resource_id,
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"principal_type": payload.principal_type, "permission": payload.permission},
    )
    return {"id": str(grant.id), "permission": grant.permission}


@router.delete("/api/collab/share/{grant_id}")
async def unshare_resource(
    grant_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    ok = await collab.unshare_resource(session, ctx.organization_id, grant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Grant not found.")
    return {"status": "revoked", "id": str(grant_id)}


@router.get("/api/collab/permissions")
async def list_permissions(
    resource_type: str = Query(...),
    resource_id: str = Query(...),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    grants = await collab.list_permissions(session, ctx.organization_id, resource_type, resource_id)
    mine = await collab.effective_permission(
        session, ctx.organization_id, ctx.user_id, resource_type, resource_id
    )
    return {"permissions": grants, "my_permission": mine}


# ─────────────────────────── comments + reactions ───────────────────────────
@router.get("/api/collab/comments")
async def list_comments(
    resource_type: str = Query(...),
    resource_id: str = Query(...),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return {
        "comments": await collab.list_comments(
            session, ctx.organization_id, resource_type, resource_id
        )
    }


@router.post("/api/collab/comments", status_code=status.HTTP_201_CREATED)
async def create_comment(
    payload: CommentCreateRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    comment = await collab.create_comment(
        session,
        ctx.organization_id,
        ctx.user_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        body=payload.body,
        parent_comment_id=payload.parent_comment_id,
        mention_user_ids=payload.mention_user_ids,
    )
    return {"id": str(comment.id), "status": "created"}


@router.post("/api/collab/comments/{comment_id}/resolve")
async def resolve_comment(
    comment_id: uuid.UUID,
    payload: CommentResolveRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    comment = await collab.resolve_comment(
        session, ctx.organization_id, comment_id, payload.resolved
    )
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found.")
    return {"id": str(comment.id), "resolved": comment.resolved}


@router.get("/api/collab/reactions")
async def list_reactions(
    resource_type: str = Query(...),
    resource_id: str = Query(...),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return {
        "reactions": await collab.list_reactions(
            session, ctx.organization_id, resource_type, resource_id
        )
    }


@router.post("/api/collab/reactions")
async def toggle_reaction(
    payload: ReactionRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await collab.toggle_reaction(
        session,
        ctx.organization_id,
        ctx.user_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        emoji=payload.emoji,
    )


# ─────────────────────────── notifications ───────────────────────────
@router.get("/api/notifications")
async def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return await collab.list_notifications(
        session, ctx.organization_id, ctx.user_id, unread_only=unread_only, limit=limit
    )


@router.put("/api/notifications/{notif_id}/read")
async def mark_notification_read(
    notif_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    ok = await collab.mark_notification_read(session, ctx.organization_id, ctx.user_id, notif_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"status": "read", "id": str(notif_id)}


@router.post("/api/notifications/read-all")
async def mark_all_read(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    n = await collab.mark_all_read(session, ctx.organization_id, ctx.user_id)
    return {"status": "ok", "marked": n}


# ─────────────────────────── activity feed ───────────────────────────
@router.get("/api/activity")
async def list_activity(
    limit: int = Query(50, ge=1, le=200),
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return {
        "activity": await collab.list_activity(
            session,
            ctx.organization_id,
            limit=limit,
            resource_type=resource_type,
            resource_id=resource_id,
        )
    }


# ─────────────────────────── tasks ───────────────────────────
@router.get("/api/tasks")
async def list_tasks(
    mine: bool = Query(False),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=200),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return {
        "tasks": await collab.list_tasks(
            session,
            ctx.organization_id,
            assignee_user_id=ctx.user_id if mine else None,
            status=status_filter,
            limit=limit,
        )
    }


@router.post("/api/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreateRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    task = await collab.create_task(
        session,
        ctx.organization_id,
        ctx.user_id,
        title=payload.title,
        description=payload.description,
        assignee_user_id=payload.assignee_user_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        comment_id=payload.comment_id,
        due_at=payload.due_at,
    )
    return {"id": str(task.id), "status": "created"}


@router.put("/api/tasks/{task_id}")
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdateRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    task = await collab.update_task(
        session, ctx.organization_id, task_id, **payload.model_dump(exclude_none=True)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"id": str(task.id), "status": task.status}


# ─────────────────────────── follows ───────────────────────────
@router.get("/api/follow")
async def list_follows(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    return {"follows": await collab.list_follows(session, ctx.organization_id, ctx.user_id)}


@router.post("/api/follow", status_code=status.HTTP_201_CREATED)
async def follow_resource(
    payload: FollowRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await collab.follow_resource(
        session,
        ctx.organization_id,
        ctx.user_id,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    return {"status": "following"}


@router.delete("/api/follow")
async def unfollow_resource(
    resource_type: str = Query(...),
    resource_id: str = Query(...),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await collab.unfollow_resource(
        session,
        ctx.organization_id,
        ctx.user_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return {"status": "unfollowed"}
