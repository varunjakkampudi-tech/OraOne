"""Phase 12 Module 3 — Team management API.

Members + token-based invitations. Read endpoints require ``team.read``;
mutating endpoints require ``team.manage``. Invite *acceptance* only
requires authentication (the accepting user may not yet belong to the org).
"""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.organization_invitation import OrganizationInvitation
from app.database.models.user import User
from app.database.repositories.team_repository import TeamRepository
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_permission,
)
from app.schemas.team import (
    InvitationListResponse,
    InvitationRead,
    InviteAcceptRequest,
    InviteAcceptResponse,
    InviteCreateRequest,
    InviteCreateResponse,
    InvitePreviewResponse,
    MemberListResponse,
    MemberRead,
    RoleUpdateRequest,
)
from app.services import email_service
from app.services import team_service
from app.services import usage_service
from app.services.audit import audit
from app.database.models.organization import Organization

router = APIRouter(tags=["team"])

_APP_URL = os.getenv("APP_URL", "http://localhost:3000")


def _invitation_read(inv: OrganizationInvitation, *, with_url: bool) -> InvitationRead:
    invited_by = None
    if inv.invited_by is not None:
        invited_by = inv.invited_by.full_name or inv.invited_by.email
    return InvitationRead(
        id=inv.id,
        email=inv.email,
        role=inv.role.value,
        status=inv.status.value,
        invited_by=invited_by,
        invite_url=team_service.build_invite_url(_APP_URL, inv.token) if with_url else None,
        expires_at=inv.expires_at,
        created_at=inv.created_at,
        accepted_at=inv.accepted_at,
    )


# ───────────────────────── members ─────────────────────────


@router.get("/api/team/members", response_model=MemberListResponse)
async def list_members(
    ctx: OrgContext = Depends(require_permission("team.read")),
    session: AsyncSession = Depends(get_db),
) -> MemberListResponse:
    repo = TeamRepository(session, ctx.organization_id)
    rows = await repo.list_members()
    items = [
        MemberRead(
            id=m.id,
            user_id=m.user_id,
            email=u.email,
            full_name=u.full_name,
            avatar_url=u.avatar_url,
            role=m.role.value,
            status=m.status.value,
            joined_at=m.joined_at,
            last_login_at=u.last_login_at,
            is_you=(m.user_id == ctx.user_id),
        )
        for m, u in rows
    ]
    return MemberListResponse(items=items, total=len(items))


@router.patch("/api/team/members/{member_id}", response_model=MemberRead)
async def change_member_role(
    member_id: uuid.UUID,
    body: RoleUpdateRequest,
    ctx: OrgContext = Depends(require_permission("team.manage")),
    session: AsyncSession = Depends(get_db),
) -> MemberRead:
    member = await team_service.update_member_role(
        session,
        organization_id=ctx.organization_id,
        member_id=member_id,
        new_role=body.role,
        actor_user_id=ctx.user_id,
    )
    user = await session.get(User, member.user_id)
    audit(
        "team.member.role_changed",
        resource="organization_member",
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        resource_id=member.id,
        meta={"new_role": member.role.value},
    )
    await session.commit()
    return MemberRead(
        id=member.id,
        user_id=member.user_id,
        email=user.email if user else "",
        full_name=user.full_name if user else None,
        avatar_url=user.avatar_url if user else None,
        role=member.role.value,
        status=member.status.value,
        joined_at=member.joined_at,
        last_login_at=user.last_login_at if user else None,
        is_you=(member.user_id == ctx.user_id),
    )


@router.delete("/api/team/members/{member_id}")
async def remove_member(
    member_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission("team.manage")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await team_service.remove_member(
        session,
        organization_id=ctx.organization_id,
        member_id=member_id,
        actor_user_id=ctx.user_id,
    )
    audit(
        "team.member.removed",
        resource="organization_member",
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        resource_id=member_id,
    )
    await session.commit()
    return {"removed": True, "member_id": str(member_id)}


# ─────────────────────── invitations ───────────────────────


@router.get("/api/team/invitations", response_model=InvitationListResponse)
async def list_invitations(
    ctx: OrgContext = Depends(require_permission("team.read")),
    session: AsyncSession = Depends(get_db),
) -> InvitationListResponse:
    repo = TeamRepository(session, ctx.organization_id)
    invites = await repo.list_invitations()
    items = [_invitation_read(i, with_url=True) for i in invites]
    return InvitationListResponse(items=items, total=len(items))


@router.post("/api/team/invitations", response_model=InviteCreateResponse, status_code=201)
async def create_invitation(
    body: InviteCreateRequest,
    ctx: OrgContext = Depends(require_permission("team.manage")),
    session: AsyncSession = Depends(get_db),
) -> InviteCreateResponse:
    # Phase 12 Module 2: enforce the plan's seat (users) quota before inviting.
    await usage_service.enforce_quota(session, ctx.organization_id, "users")
    invite = await team_service.create_invitation(
        session,
        organization_id=ctx.organization_id,
        invited_by_user_id=ctx.user_id,
        email=str(body.email),
        role=body.role,
    )
    audit(
        "team.invitation.created",
        resource="organization_invitation",
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        resource_id=invite.id,
        meta={"email": invite.email, "role": invite.role.value},
    )
    await session.commit()
    await session.refresh(invite, ["invited_by"])

    # Best-effort transactional email (no-op/log when email isn't configured).
    try:
        org = await session.get(Organization, ctx.organization_id)
        email_service.send_team_invite(
            invite.email,
            org_name=org.name if org else "your team",
            inviter_name=(invite.invited_by.full_name or invite.invited_by.email),
            role=invite.role.value,
            accept_url=team_service.build_invite_url(_APP_URL, invite.token),
        )
    except Exception:  # pragma: no cover - notifications never block the API
        pass

    return InviteCreateResponse(
        invitation=_invitation_read(invite, with_url=True),
        message=f"Invitation ready for {invite.email}. Share the link to let them join.",
    )


@router.delete("/api/team/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission("team.manage")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await team_service.revoke_invitation(
        session,
        organization_id=ctx.organization_id,
        invitation_id=invitation_id,
    )
    audit(
        "team.invitation.revoked",
        resource="organization_invitation",
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        resource_id=invitation_id,
    )
    await session.commit()
    return {"revoked": True, "invitation_id": str(invitation_id)}


# ───────────────────── accept / preview ─────────────────────


@router.get("/api/team/invite/preview", response_model=InvitePreviewResponse)
async def preview_invitation(
    token: str = Query(...),
    _ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> InvitePreviewResponse:
    valid, invite, org, reason = await team_service.preview_invitation(
        session, token=token
    )
    await session.commit()
    if not valid:
        return InvitePreviewResponse(
            valid=False,
            email=invite.email if invite else None,
            role=invite.role.value if invite else None,
            status=invite.status.value if invite else None,
            reason=reason,
        )
    return InvitePreviewResponse(
        valid=True,
        organization_name=org.name if org else None,
        email=invite.email,
        role=invite.role.value,
        status=invite.status.value,
    )


@router.post("/api/team/invite/accept", response_model=InviteAcceptResponse)
async def accept_invitation(
    body: InviteAcceptRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> InviteAcceptResponse:
    user = await session.get(User, ctx.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    org, role = await team_service.accept_invitation(
        session, token=body.token, user=user
    )
    audit(
        "team.invitation.accepted",
        resource="organization",
        organization_id=org.id,
        user_id=user.id,
        meta={"role": role.value},
    )
    await session.commit()
    return InviteAcceptResponse(
        organization_id=org.id,
        organization_name=org.name,
        role=role.value,
        message=f"You've joined {org.name} as {role.value}.",
    )
