"""Self-hosted authentication service (Argon2 + JWT).

Replaces AWS Cognito. Responsibility split (SOLID):

    AuthService (this module — orchestrates the use-cases below)
        -> PasswordService  (app.core.security: hash/verify)
        -> TokenService     (app.services.token_service: issue/rotate/revoke)
        -> UserRepository   (app.database.repositories.user_repository)

Routes stay thin (app/api/auth/routes.py): they only call these functions
and translate results to HTTP responses.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    generate_numeric_code,
    hash_password,
    verify_password,
)
from app.database.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ConfirmForgotPasswordRequest,
    ConfirmSignUpRequest,
    ForgotPasswordRequest,
    LoginOtpRequiredResponse,
    LoginRequest,
    RefreshTokenRequest,
    ResendConfirmationRequest,
    SignUpRequest,
    TokensResponse,
    VerifyLoginOtpRequest,
)
from app.services import token_service
from app.services.cache import get_shared_cache

log = logging.getLogger("app.auth.service")

_VERIFY_CODE_TTL_SECONDS = 24 * 3600
_RESET_CODE_TTL_SECONDS = 3600
_LOGIN_OTP_TTL_SECONDS = 10 * 60


def _cache():
    return get_shared_cache("auth")


def _verify_code_key(email: str) -> str:
    return f"verify:{email.strip().lower()}"


def _reset_code_key(email: str) -> str:
    return f"reset:{email.strip().lower()}"


def _login_otp_key(email: str) -> str:
    return f"login_otp:{email.strip().lower()}"


def _frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _to_tokens_response(pair: token_service.TokenPair) -> TokensResponse:
    return TokensResponse(
        access_token=pair.access_token,
        id_token=pair.access_token,  # single-token model; id_token kept for API compatibility
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


# ─────────────────────────────────────────────────────────────
# Registration / email verification
# ─────────────────────────────────────────────────────────────

async def sign_up(session: AsyncSession, data: SignUpRequest) -> dict:
    from app.services.email_service import send_verify_email

    users = UserRepository(session)
    existing = await users.get_by_email(data.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    from app.database.models.user import User

    user = User(
        cognito_sub=str(uuid.uuid4()),
        email=data.email.strip().lower(),
        full_name=data.name.strip(),
        password_hash=hash_password(data.password),
        is_email_verified=False,
    )
    session.add(user)
    await session.flush()
    await session.commit()

    code = generate_numeric_code()
    _cache().set(_verify_code_key(data.email), code, ttl_seconds=_VERIFY_CODE_TTL_SECONDS)
    sent = send_verify_email(
        data.email,
        verify_url=f"{_frontend_url()}/verify-email?email={data.email}",
        code=code,
    )
    log.info("signup email=%s verification_sent=%s", data.email, sent)
    return {"user_confirmed": False}


async def confirm_sign_up(session: AsyncSession, data: ConfirmSignUpRequest) -> None:
    stored = _cache().get(_verify_code_key(data.email))
    if not stored or stored != data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect or expired verification code.",
        )
    users = UserRepository(session)
    user = await users.get_by_email(data.email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found with this email.")
    user.is_email_verified = True
    await session.commit()
    _cache().delete(_verify_code_key(data.email))


async def resend_confirmation_code(session: AsyncSession, data: ResendConfirmationRequest) -> dict:
    from app.services.email_service import send_verify_email

    users = UserRepository(session)
    user = await users.get_by_email(data.email)
    if user is None or user.is_email_verified:
        # Don't leak account existence/verification state.
        return {"delivery": {}}
    code = generate_numeric_code()
    _cache().set(_verify_code_key(data.email), code, ttl_seconds=_VERIFY_CODE_TTL_SECONDS)
    send_verify_email(data.email, verify_url=f"{_frontend_url()}/verify-email?email={data.email}", code=code)
    return {"delivery": {}}


# ─────────────────────────────────────────────────────────────
# Login / refresh / logout
# ─────────────────────────────────────────────────────────────

async def login(session: AsyncSession, data: LoginRequest) -> LoginOtpRequiredResponse:
    """Verify credentials and email a one-time code — tokens are issued by
    verify_login_otp() once that code is confirmed (see routes.py).
    """
    from app.services.email_service import send_login_otp

    users = UserRepository(session)
    user = await users.get_by_email(data.email)
    if user is None or not verify_password(data.password, user.password_hash or ""):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    if user.status.value != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account has been disabled.")

    require_verified = bool(
        os.environ.get("SMTP_HOST") or os.environ.get("EMAIL_FROM") or os.environ.get("SES_FROM_EMAIL")
    )
    if require_verified and not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email first.",
        )

    code = generate_numeric_code()
    _cache().set(_login_otp_key(data.email), code, ttl_seconds=_LOGIN_OTP_TTL_SECONDS)
    send_login_otp(data.email, code=code)
    log.info("login_otp_sent email=%s", data.email)
    return LoginOtpRequiredResponse(email=data.email)


async def verify_login_otp(session: AsyncSession, data: VerifyLoginOtpRequest) -> TokensResponse:
    stored = _cache().get(_login_otp_key(data.email))
    if not stored or stored != data.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect or expired code.")
    _cache().delete(_login_otp_key(data.email))

    users = UserRepository(session)
    user = await users.get_by_email(data.email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found with this email.")

    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    try:
        pair = token_service.issue_token_pair(user_id=user.cognito_sub, email=user.email, name=user.full_name)
    except Exception as e:  # noqa: BLE001 — fail safely: no session store, no tokens, clear retryable error
        log.error("token_issue_failed user=%s err=%s", user.cognito_sub, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-in is temporarily unavailable. Please try again shortly.",
        )
    return _to_tokens_response(pair)


async def refresh_tokens(data: RefreshTokenRequest) -> TokensResponse:
    try:
        pair = token_service.rotate(data.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
        )
    except Exception as e:  # noqa: BLE001 — fail safely: token store unreachable, not "invalid token"
        log.error("token_refresh_failed err=%s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session refresh is temporarily unavailable. Please try again shortly.",
        )
    return _to_tokens_response(pair)


def logout(refresh_token: str | None) -> None:
    """Revoke the presented refresh token (best-effort — logout must always succeed)."""
    if refresh_token:
        try:
            token_service.revoke(refresh_token)
        except Exception:  # noqa: BLE001
            pass


def logout_all(user_id: str) -> None:
    """Revoke every refresh token for this user, on every device."""
    try:
        token_service.revoke_all_for_user(user_id)
    except Exception:  # noqa: BLE001
        pass


# ─────────────────────────────────────────────────────────────
# Password reset
# ─────────────────────────────────────────────────────────────

async def forgot_password(session: AsyncSession, data: ForgotPasswordRequest) -> dict:
    from app.services.email_service import send_password_reset

    users = UserRepository(session)
    user = await users.get_by_email(data.email)
    if user is None:
        # Behave like success to avoid email enumeration.
        return {"delivery": {}}
    code = generate_numeric_code()
    _cache().set(_reset_code_key(data.email), code, ttl_seconds=_RESET_CODE_TTL_SECONDS)
    send_password_reset(data.email, reset_url=f"{_frontend_url()}/reset-password?email={data.email}", code=code)
    return {"delivery": {}}


async def confirm_forgot_password(session: AsyncSession, data: ConfirmForgotPasswordRequest) -> None:
    stored = _cache().get(_reset_code_key(data.email))
    if not stored or stored != data.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect or expired reset code.")
    users = UserRepository(session)
    user = await users.get_by_email(data.email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found with this email.")
    user.password_hash = hash_password(data.new_password)
    await session.commit()
    _cache().delete(_reset_code_key(data.email))
    # Force re-login on every device — the old password (and any tokens
    # issued under it) should no longer be trusted.
    token_service.revoke_all_for_user(user.cognito_sub)


async def change_password(session: AsyncSession, user_id: str, *, current_password: str, new_password: str) -> None:
    """Change the caller's password while logged in (Settings page)."""
    users = UserRepository(session)
    user = await users.get_by_cognito_sub(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    if not user.password_hash or not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")
    user.password_hash = hash_password(new_password)
    await session.commit()
