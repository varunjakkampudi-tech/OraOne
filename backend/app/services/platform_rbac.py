"""Platform-role policy and audited role changes.

These rules operate on ``users.role`` only. Workspace/member permissions stay
on ``organization_members.role`` and are evaluated by the organization RBAC
matrix, so an organization admin does not become a platform administrator.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.services.audit import audit

PLATFORM_ROLES = tuple(role.value for role in UserRole)
_ASSIGNABLE_BY_ADMIN = frozenset({UserRole.manager, UserRole.user})
_ASSIGNABLE_BY_SUPER_ADMIN = frozenset(
    {UserRole.admin, UserRole.manager, UserRole.user}
)


def can_change_platform_role(
    actor: UserRole, target: UserRole, new_role: UserRole
) -> bool:
    """Return whether the separately authorized actor may perform this change."""
    if target == UserRole.super_admin or new_role == UserRole.super_admin:
        return False
    if actor == UserRole.super_admin:
        return new_role in _ASSIGNABLE_BY_SUPER_ADMIN
    if actor == UserRole.admin:
        return new_role in _ASSIGNABLE_BY_ADMIN and target not in {
            UserRole.super_admin,
            UserRole.admin,
        }
    return False


def parse_platform_role(value: str) -> UserRole:
    try:
        return UserRole(value.strip().lower())
    except (AttributeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown platform role."
        ) from exc


async def change_platform_role(
    session: AsyncSession,
    *,
    actor: User,
    target_user_id,
    new_role: str,
) -> User:
    target = await session.get(User, target_user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if target.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own platform role.",
        )

    parsed = parse_platform_role(new_role)
    if not can_change_platform_role(actor.role, target.role, parsed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform role change is not permitted.",
        )

    before = target.role.value
    target.role = parsed
    audit(
        "platform.user.role_changed",
        resource="user",
        organization_id="",
        user_id=str(actor.id),
        resource_id=str(target.id),
        before={"role": before},
        after={"role": parsed.value},
        meta={
            "actor_cognito_sub": actor.cognito_sub,
            "target_cognito_sub": target.cognito_sub,
        },
    )
    await session.flush()
    return target
