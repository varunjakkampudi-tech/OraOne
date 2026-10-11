"""Auth API routes (self-hosted — Argon2 + JWT, no AWS Cognito).

POST /api/auth/signup
POST /api/auth/verify
POST /api/auth/resend
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/forgot-password
POST /api/auth/reset-password
POST /api/auth/logout
GET  /api/auth/me
GET  /api/auth/identity

Routes stay thin: all business logic lives in app.services.auth_service.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import REFRESH_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.database.session import get_db
from app.middleware.jwt_auth import get_current_access_token, get_current_user_claims
from app.schemas.auth import (
    ChangePasswordRequest,
    ConfirmForgotPasswordRequest,
    ConfirmSignUpRequest,
    ForgotPasswordRequest,
    IdentityMembership,
    IdentityOrganization,
    IdentityResponse,
    IdentityUser,
    LoginOtpRequiredResponse,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResendConfirmationRequest,
    SignUpRequest,
    TokensResponse,
    UpdateProfileRequest,
    UserProfile,
    VerifyLoginOtpRequest,
)
from app.services import IdentityService, auth_service, user_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

log = logging.getLogger("app.auth.identity")


def _degraded_identity_response(*, sub: str, email: str, full_name: Optional[str]) -> IdentityResponse:
    """Return a minimal identity payload when Postgres is temporarily unavailable.

    This keeps auth/login usable during transient DB outages. The payload is
    deterministic per user so the frontend can keep a stable workspace context.
    """
    import uuid as _uuid

    now = datetime.now(timezone.utc)
    org_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"oraone:org:{sub}"))
    membership_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"oraone:membership:{sub}"))
    slug = f"workspace-{sub.replace('-', '')[:8]}"

    return IdentityResponse(
        user=IdentityUser(
            id=sub,
            cognito_sub=sub,
            email=email,
            full_name=full_name,
            avatar_url=None,
            role="user",
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


@router.post("/signup", response_model=MessageResponse)
async def signup(payload: SignUpRequest, session: AsyncSession = Depends(get_db)):
    await auth_service.sign_up(session, payload)
    return MessageResponse(message="Verification code sent to your email.")


@router.post("/verify", response_model=MessageResponse)
async def verify(payload: ConfirmSignUpRequest, session: AsyncSession = Depends(get_db)):
    await auth_service.confirm_sign_up(session, payload)
    return MessageResponse(message="Email verified. You can now log in.")


@router.post("/resend", response_model=MessageResponse)
async def resend(payload: ResendConfirmationRequest, session: AsyncSession = Depends(get_db)):
    await auth_service.resend_confirmation_code(session, payload)
    return MessageResponse(message="If an account exists for this email, a new code has been sent.")


@router.post("/login", response_model=LoginOtpRequiredResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db)):
    """Verify credentials and email a one-time code. Call /login/verify-otp
    with that code to receive tokens."""
    return await auth_service.login(session, payload)


@router.post("/login/verify-otp", response_model=TokensResponse)
async def login_verify_otp(payload: VerifyLoginOtpRequest, response: Response, session: AsyncSession = Depends(get_db)):
    tokens = await auth_service.verify_login_otp(session, payload)
    set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)
    return tokens


@router.post("/refresh", response_model=TokensResponse)
async def refresh(request: Request, response: Response, payload: Optional[RefreshTokenRequest] = None):
    # Browser sessions may rely solely on the httpOnly refresh cookie; API/
    # bearer clients still pass it in the JSON body.
    token = (payload.refresh_token if payload else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token.")
    tokens = await auth_service.refresh_tokens(RefreshTokenRequest(refresh_token=token))
    set_auth_cookies(response, access_token=tokens.access_token, refresh_token=tokens.refresh_token)
    return tokens


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, session: AsyncSession = Depends(get_db)):
    await auth_service.forgot_password(session, payload)
    return MessageResponse(message="If an account exists for this email, a reset code has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ConfirmForgotPasswordRequest, session: AsyncSession = Depends(get_db)):
    await auth_service.confirm_forgot_password(session, payload)
    return MessageResponse(message="Password reset successful. You can now log in.")


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, response: Response, payload: Optional[RefreshTokenRequest] = None):
    token = (payload.refresh_token if payload else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    auth_service.logout(token)
    clear_auth_cookies(response)
    return MessageResponse(message="Logged out.")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(response: Response, claims: dict = Depends(get_current_user_claims)):
    """Revoke every refresh token for this account — signs out every device."""
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims.")
    auth_service.logout_all(user_id)
    clear_auth_cookies(response)
    return MessageResponse(message="Signed out of all devices.")


@router.get("/me", response_model=UserProfile)
async def me(
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims.")

    profile = await user_service.get_user_profile(session, user_id)
    if not profile:
        # Token is valid but the DB row is momentarily unreachable — derive a
        # minimal profile from claims rather than fail the whole request.
        email = claims.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found. Try logging in again.",
            )
        profile = UserProfile(
            userId=user_id,
            email=email,
            name=claims.get("name") or "",
            role="user",
            plan="free",
            status="active",
            createdAt=datetime.now(timezone.utc),
            lastLogin=datetime.now(timezone.utc),
        )
    return profile


@router.patch("/profile", response_model=UserProfile)
async def update_profile(
    payload: UpdateProfileRequest,
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims.")
    profile = await user_service.update_profile(session, user_id, full_name=payload.full_name)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found.")
    return profile


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims.")
    await auth_service.change_password(
        session, user_id, current_password=payload.current_password, new_password=payload.new_password
    )
    return MessageResponse(message="Password updated.")


# ──────────────────────────────────────────────────────────────────
# Postgres identity (find-or-create user + personal org, idempotent)
# ──────────────────────────────────────────────────────────────────

@router.get("/identity", response_model=IdentityResponse)
async def identity(
    claims: dict = Depends(get_current_user_claims),
    access_token: str = Depends(get_current_access_token),
    session: AsyncSession = Depends(get_db),
) -> IdentityResponse:
    """Hydrate the caller's Postgres identity from their access token.

    First call for a user creates `users` + a personal `organizations` row +
    an Owner `organization_members` row (+ a default `projects` row), all in
    one transaction. Subsequent calls reuse those records (idempotent).
    """
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims.")

    email = claims.get("email")
    full_name = claims.get("name") or None
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token is missing an email claim.",
        )

    log.info("identity_resolve sub=%s email=%s", sub, email)

    svc = IdentityService(session)
    try:
        result = await svc.upsert_from_cognito(
            cognito_sub=sub,
            email=email,
            full_name=full_name,
            given_name=None,
        )
        await session.commit()

        user, org, member = result.user, result.organization, result.membership
        return IdentityResponse(
            user=IdentityUser(
                id=str(user.id),
                cognito_sub=user.cognito_sub,
                email=user.email,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                role=user.role.value,
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
    except Exception as exc:  # keep auth resilient when DB is transiently unavailable
        await session.rollback()
        log.warning("identity_degraded_fallback sub=%s reason=%s: %s", sub, type(exc).__name__, exc)
        return _degraded_identity_response(sub=sub, email=email, full_name=full_name)
