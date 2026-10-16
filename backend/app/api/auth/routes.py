"""Authentication API.

Endpoints:
    POST /api/auth/email-code/request   email a one-time sign-in code
    POST /api/auth/email-code/verify    exchange the code for a session
    POST /api/auth/dev-login            development-only password sign-in
    POST /api/auth/refresh              rotate the session
    POST /api/auth/logout               end this session
    POST /api/auth/logout-all           end every session for the caller
    GET  /api/auth/me                   profile of the signed-in user
    PATCH /api/auth/profile             update the display name
    GET  /api/auth/identity             provision and read the account identity

Routes stay thin: the rules live in :mod:`app.services.auth_service`.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import REFRESH_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.database.session import get_db
from app.middleware.jwt_auth import get_current_user_claims
from app.schemas.auth import (
    EmailCodeRequest,
    IdentityMembership,
    IdentityOrganization,
    IdentityResponse,
    IdentityUser,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    TokensResponse,
    UpdateProfileRequest,
    UserProfile,
    VerifyLoginOtpRequest,
)
from app.services import IdentityService, auth_service, user_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

log = logging.getLogger("app.auth.identity")


def _degraded_identity_response(
    *, sub: str, email: str, full_name: Optional[str]
) -> IdentityResponse:
    """Return a minimal identity when the database is briefly unavailable.

    Keeps the signed-in experience usable during a short outage. The ids are
    deterministic per subject, so the client keeps a stable workspace context.
    """
    now = datetime.now(timezone.utc)
    org_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"oraone:org:{sub}"))
    membership_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"oraone:membership:{sub}"))
    slug = f"workspace-{sub.replace('-', '')[:8]}"

    return IdentityResponse(
        user=IdentityUser(
            id=sub,
            auth_subject=sub,
            email=email,
            full_name=full_name,
            avatar_url=None,
            role="user",
            platform_role="user",
            status="active",
            created_at=now,
            last_login_at=now,
        ),
        organization=IdentityOrganization(
            id=org_id,
            name=(full_name or "Personal") + "'s Workspace",
            slug=slug,
            plan="free",
            owner_user_id=sub,
            created_at=now,
        ),
        membership=IdentityMembership(
            id=membership_id,
            organization_id=org_id,
            user_id=sub,
            role="owner",
            status="active",
            joined_at=now,
        ),
        is_new_user=False,
    )


# ── Passwordless sign-in ──────────────────────────────────────────────────


@router.post("/email-code/request", response_model=MessageResponse)
async def email_code_request(
    payload: EmailCodeRequest, session: AsyncSession = Depends(get_db)
):
    """Email a one-time sign-in code. Creates the account when the address is new."""
    await auth_service.request_email_code(session, payload)
    return MessageResponse(
        message="If this address can receive sign-in codes, a code is on its way."
    )


@router.post("/email-code/verify", response_model=TokensResponse)
async def email_code_verify(
    payload: VerifyLoginOtpRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    """Exchange the emailed code for an httpOnly session cookie and tokens."""
    tokens = await auth_service.verify_email_code(session, payload)
    set_auth_cookies(
        response, access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )
    return tokens


@router.post("/dev-login", response_model=TokensResponse)
async def dev_login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    """Development-only password sign-in. Returns 404 unless explicitly enabled."""
    tokens = await auth_service.dev_password_login(session, payload)
    set_auth_cookies(
        response, access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )
    return tokens


# ── Session management ────────────────────────────────────────────────────


@router.post("/refresh", response_model=TokensResponse)
async def refresh(
    request: Request, response: Response, payload: Optional[RefreshTokenRequest] = None
):
    """Rotate the session. Accepts the refresh token in the body or the cookie."""
    token = (payload.refresh_token if payload else None) or request.cookies.get(
        REFRESH_COOKIE_NAME
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token."
        )
    tokens = await auth_service.refresh_tokens(RefreshTokenRequest(refresh_token=token))
    set_auth_cookies(
        response, access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )
    return tokens


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request, response: Response, payload: Optional[RefreshTokenRequest] = None
):
    """End this session and clear the session cookies."""
    token = (payload.refresh_token if payload else None) or request.cookies.get(
        REFRESH_COOKIE_NAME
    )
    auth_service.logout(token)
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out.")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    response: Response, claims: dict = Depends(get_current_user_claims)
):
    """Revoke every refresh token for the caller, signing out every device."""
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims."
        )
    auth_service.logout_all(user_id)
    clear_auth_cookies(response)
    return MessageResponse(message="Signed out of all devices.")


# ── Profile ───────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserProfile)
async def me(
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    """Return the signed-in user's profile."""
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims."
        )

    profile = await user_service.get_user_profile(session, user_id)
    if profile:
        return profile
    # The token is valid but the row is momentarily unreadable: build the profile
    # from the claims rather than failing the whole request.
    email = claims.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Please sign in again.",
        )
    return UserProfile(
        userId=user_id,
        email=email,
        name=claims.get("name") or "",
        role="user",
        platform_role="user",
        plan="free",
        status="active",
        createdAt=datetime.now(timezone.utc),
        lastLogin=datetime.now(timezone.utc),
    )


@router.patch("/profile", response_model=UserProfile)
async def update_profile(
    payload: UpdateProfileRequest,
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    """Update the signed-in user's display name."""
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims."
        )
    profile = await user_service.update_profile(
        session, user_id, full_name=payload.full_name
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found."
        )
    return profile


# ── Identity provisioning ─────────────────────────────────────────────────


@router.get("/identity", response_model=IdentityResponse)
async def identity(
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
) -> IdentityResponse:
    """Create or read the caller's user, personal organization and default project.

    Idempotent: the first call provisions the records in one transaction, and
    later calls return the existing ones.
    """
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims."
        )

    email = claims.get("email")
    full_name = claims.get("name") or None
    given_name = claims.get("given_name") or None
    avatar_url = claims.get("picture") or None
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account has no email address.",
        )

    log.info("identity_resolve sub=%s email=%s", sub, email)

    svc = IdentityService(session)
    try:
        result = await svc.upsert_identity(
            auth_subject=sub,
            email=email,
            full_name=full_name,
            given_name=given_name,
            avatar_url=avatar_url,
        )
        await session.commit()

        user, org, member = result.user, result.organization, result.membership
        return IdentityResponse(
            user=IdentityUser(
                id=str(user.id),
                auth_subject=user.auth_subject,
                email=user.email,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                role=user.role.value,
                platform_role=user.role.value,
                status=user.status.value,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
            ),
            organization=IdentityOrganization(
                id=str(org.id),
                name=org.name,
                slug=org.slug,
                plan=org.plan.value,
                owner_user_id=str(org.owner_user_id),
                created_at=org.created_at,
            ),
            membership=IdentityMembership(
                id=str(member.id),
                organization_id=str(member.organization_id),
                user_id=str(member.user_id),
                role=member.role.value,
                status=member.status.value,
                joined_at=member.joined_at,
            ),
            is_new_user=result.is_new_user,
        )
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001 - keep sign-in working through a DB blip
        await session.rollback()
        log.warning(
            "identity_degraded_fallback sub=%s reason=%s: %s",
            sub,
            type(exc).__name__,
            exc,
        )
        return _degraded_identity_response(sub=sub, email=email, full_name=full_name)
