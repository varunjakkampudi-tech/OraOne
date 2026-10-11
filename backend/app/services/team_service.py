"""Team service — invitations + membership management (Phase 12, Module 3).

Token-based invites (no email service yet): the backend mints a secure
token and returns a shareable link. A signed-in user whose email matches
the invite accepts it to join the organisation.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.organization import Organization
from app.database.models.organization_invitation import (
    InvitationStatus,
    OrganizationInvitation,
)
from app.database.models.organization_member import (
    MemberRole,
    MemberStatus,
    OrganizationMember,
)
from app.database.models.user import User
from app.database.repositories.organization_member_repository import (
    OrganizationMemberRepository,
)
from app.database.repositories.team_repository import TeamRepository

INVITE_TTL_DAYS = 7

#: Roles that may be assigned via an invitation or role change. ``owner`` is
#: deliberately excluded — ownership transfer is a separate, guarded action.
ASSIGNABLE_ROLES = {MemberRole.admin, MemberRole.member, MemberRole.viewer}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_role(role: str) -> MemberRole:
    try:
        parsed = MemberRole(role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown role '{role}'.",
        )
    if parsed not in ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role}' cannot be assigned here.",
        )
    return parsed


def build_invite_url(app_url: str, token: str) -> str:
    return f"{app_url.rstrip('/')}/app/invite/{token}"


async def create_invitation(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    invited_by_user_id: uuid.UUID,
    email: str,
    role: str,
) -> OrganizationInvitation:
    email = email.strip().lower()
    parsed_role = _parse_role(role)
    repo = TeamRepository(session, organization_id)

    # Already a member?
    existing_member = await repo.find_member_by_email(email)
    if existing_member is not None and existing_member.status != MemberStatus.removed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That person is already a member of this organisation.",
        )

    # Re-use / refresh an existing pending invite for the same email.
    invite = await repo.find_pending_invitation_by_email(email)
    if invite is None:
        invite = OrganizationInvitation(organization_id=organization_id, email=email)
        session.add(invite)

    invite.role = parsed_role
    invite.status = InvitationStatus.pending
    invite.token = secrets.token_urlsafe(32)
    invite.invited_by_user_id = invited_by_user_id
    invite.expires_at = _now() + timedelta(days=INVITE_TTL_DAYS)
    invite.accepted_at = None
    invite.accepted_user_id = None

    await session.flush()
    return invite


async def revoke_invitation(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    invitation_id: uuid.UUID,
) -> OrganizationInvitation:
    repo = TeamRepository(session, organization_id)
    invite = await repo.get_invitation(invitation_id)
    if invite is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if invite.status == InvitationStatus.pending:
        invite.status = InvitationStatus.revoked
        await session.flush()
    return invite


async def preview_invitation(
    session: AsyncSession, *, token: str
) -> tuple[bool, Optional[OrganizationInvitation], Optional[Organization], Optional[str]]:
    invite = await TeamRepository.get_invitation_by_token(session, token)
    if invite is None:
        return False, None, None, "This invitation link is invalid."
    if invite.status != InvitationStatus.pending:
        return False, invite, None, f"This invitation is {invite.status.value}."
    if invite.expires_at < _now():
        invite.status = InvitationStatus.expired
        await session.flush()
        return False, invite, None, "This invitation has expired."
    org = await session.get(Organization, invite.organization_id)
    return True, invite, org, None


async def accept_invitation(
    session: AsyncSession,
    *,
    token: str,
    user: User,
) -> tuple[Organization, MemberRole]:
    invite = await TeamRepository.get_invitation_by_token(session, token)
    if invite is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if invite.status != InvitationStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This invitation is {invite.status.value}.",
        )
    if invite.expires_at < _now():
        invite.status = InvitationStatus.expired
        await session.flush()
        raise HTTPException(status_code=410, detail="This invitation has expired.")
    if (user.email or "").lower() != invite.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This invitation was sent to a different email address. "
                "Sign in with the invited account to accept."
            ),
        )

    members = OrganizationMemberRepository(session)
    member = await members.ensure_membership(
        organization_id=invite.organization_id,
        user_id=user.id,
        role=invite.role,
        invited_by_user_id=invite.invited_by_user_id,
    )
    # If they already existed with a different role/status, normalise.
    member.role = invite.role
    member.status = MemberStatus.active
    if member.joined_at is None:
        member.joined_at = _now()

    invite.status = InvitationStatus.accepted
    invite.accepted_at = _now()
    invite.accepted_user_id = user.id
    await session.flush()

    org = await session.get(Organization, invite.organization_id)
    return org, invite.role


async def update_member_role(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    member_id: uuid.UUID,
    new_role: str,
    actor_user_id: uuid.UUID,
) -> OrganizationMember:
    parsed_role = _parse_role(new_role)
    repo = TeamRepository(session, organization_id)
    member = await repo.get_member(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    if member.role == MemberRole.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The owner's role cannot be changed here.",
        )
    if member.user_id == actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role.",
        )
    member.role = parsed_role
    await session.flush()
    return member


async def remove_member(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    member_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    repo = TeamRepository(session, organization_id)
    member = await repo.get_member(member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    if member.role == MemberRole.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The organisation owner cannot be removed.",
        )
    if member.user_id == actor_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself.",
        )
    member.status = MemberStatus.removed
    member.deleted_at = _now()
    await session.flush()
