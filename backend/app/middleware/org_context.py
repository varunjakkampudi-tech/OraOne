"""Organization-context middleware (Phase 5).

This is the single source of truth for *which tenant* an authenticated
request is acting on. The frontend can never override this — we resolve
the org-id strictly from server-side state:

    Cognito access-token  →  users.cognito_sub  →  organization_members  →  organizations.id

The dependency is asynchronous and DB-backed; downstream business
endpoints get an `OrgContext` object holding the verified `user_id`,
`organization_id`, and `membership_role`. Repositories must scope every
query by `OrgContext.organization_id`.

This module is also where we will plug Postgres Row-Level Security in
Phase 6: the `apply_rls_on_session()` helper sets `app.org_id` /
`app.user_id` as session variables so RLS policies can read them. It is
called automatically by `get_current_organization()` for every request.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.organization import Organization
from app.database.models.organization_member import (
    MemberStatus,
    OrganizationMember,
)
from app.database.models.user import User
from app.database.session import get_db
from app.middleware.jwt_auth import get_current_user_claims

log = logging.getLogger("app.org_context")


@dataclass(frozen=True)
class OrgContext:
    """Verified tenant context for the current request.

    Attributes:
        user_id: The Postgres ``users.id`` for the caller (UUID).
        cognito_sub: The Cognito sub claim — handy for audit logs.
        organization_id: The org the request is acting on (UUID). All
            business-domain queries MUST be scoped by this value.
        membership_role: The caller's role inside ``organization_id``
            (``owner`` / ``admin`` / ``member`` / ``viewer``). Used for
            authorisation checks; repositories don't read it.
    """

    user_id: uuid.UUID
    cognito_sub: str
    organization_id: uuid.UUID
    membership_role: str


async def apply_rls_on_session(
    session: AsyncSession, ctx: OrgContext
) -> None:
    """Stamp the SQL session with the active tenant.

    Sets two ``SET LOCAL`` variables that future Row-Level Security
    policies will reference. Safe to call now even though no policies
    exist yet — Postgres treats unknown ``app.*`` settings as no-ops.

    Failure is non-fatal in Phase 5 (RLS isn't enforced yet) but is
    logged. Phase 6 will tighten this to a hard error.
    """
    try:
        await session.execute(
            text("SELECT set_config('app.org_id', :v, true)").bindparams(
                v=str(ctx.organization_id)
            )
        )
        await session.execute(
            text("SELECT set_config('app.user_id', :v, true)").bindparams(
                v=str(ctx.user_id)
            )
        )
    except Exception as e:  # pragma: no cover — non-fatal in Phase 5
        log.warning(
            "rls_session_stamp_failed org=%s user=%s err=%s: %s",
            ctx.organization_id, ctx.user_id, type(e).__name__, e,
        )


async def _resolve_org_from_db(
    session: AsyncSession, cognito_sub: str
) -> Optional[tuple[User, OrganizationMember, Organization]]:
    """Walk users → organization_members → organizations.

    Returns the user's *primary* (most recently joined, active) membership.
    Returns ``None`` if the user has no Postgres row yet, or no active
    membership.
    """
    user = await session.scalar(
        select(User).where(User.cognito_sub == cognito_sub)
    )
    if user is None:
        return None

    member = await session.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .where(OrganizationMember.status == MemberStatus.active)
        .order_by(OrganizationMember.joined_at.desc().nullslast())
        .limit(1)
    )
    if member is None:
        return None

    org = await session.scalar(
        select(Organization)
        .where(Organization.id == member.organization_id)
        .where(Organization.deleted_at.is_(None))
    )
    if org is None:
        return None

    return user, member, org


async def get_current_organization(
    request: Request,
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
) -> OrgContext:
    """FastAPI dependency that returns a verified ``OrgContext``.

    Trust model:
      - Caller's identity comes from the Cognito access token (already
        cryptographically verified by ``get_current_user_claims``).
      - The org id is *resolved server-side* from membership data; any
        ``X-Org-Id`` / ``organization_id`` body field from the client is
        intentionally ignored to prevent IDOR / tenant-spoofing.
      - The session is stamped with ``app.org_id`` / ``app.user_id`` for
        forward-compat with Phase 6 RLS.
    """
    cognito_sub = claims.get("sub")
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims.",
        )

    found = await _resolve_org_from_db(session, cognito_sub)
    if not found:
        # The caller is authenticated but doesn't have a Postgres
        # identity yet. They must call GET /api/auth/identity first
        # (Phase 3 endpoint) to bootstrap their user + personal org.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No organization context for this user. Call "
                "GET /api/auth/identity to provision your workspace, "
                "then retry."
            ),
        )

    user, member, org = found
    ctx = OrgContext(
        user_id=user.id,
        cognito_sub=cognito_sub,
        organization_id=org.id,
        membership_role=member.role.value,
    )

    # Attach to the request for easy logging downstream (e.g. access logs).
    request.state.org_context = ctx
    await apply_rls_on_session(session, ctx)

    log.info(
        "org_context user=%s org=%s role=%s path=%s",
        ctx.user_id, ctx.organization_id, ctx.membership_role,
        request.url.path,
    )
    return ctx


async def get_current_organization_id(
    ctx: OrgContext = Depends(get_current_organization),
) -> uuid.UUID:
    """Convenience: just the org UUID, for endpoints that don't need role."""
    return ctx.organization_id


def require_role(*allowed: str):
    """Dependency factory: 403 unless caller's role is in ``allowed``.

    Usage:
        @router.delete("/agents/{id}",
                       dependencies=[Depends(require_role("owner", "admin"))])
    """
    allowed_set = {r.lower() for r in allowed}

    async def _checker(
        ctx: OrgContext = Depends(get_current_organization),
    ) -> OrgContext:
        if ctx.membership_role.lower() not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{ctx.membership_role}' is not permitted here "
                    f"(requires one of: {sorted(allowed_set)})."
                ),
            )
        return ctx

    return _checker
def require_permission(*needed: str):
    """Dependency factory: 403 unless the caller's role grants every
    permission in ``needed`` (Phase 12 RBAC).

    Preferred over ``require_role`` for new endpoints — it expresses the
    capability being guarded rather than hard-coding role names, so the
    permission matrix in ``app.core.permissions`` stays the single source
    of truth.

    Usage:
        @router.post("/agents",
                     dependencies=[Depends(require_permission("agents.write"))])
    """
    from app.core.permissions import has_permission

    required = tuple(needed)

    async def _checker(
        ctx: OrgContext = Depends(get_current_organization),
    ) -> OrgContext:
        missing = [p for p in required if not has_permission(ctx.membership_role, p)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{ctx.membership_role}' lacks required "
                    f"permission(s): {missing}."
                ),
            )
        return ctx

    return _checker

