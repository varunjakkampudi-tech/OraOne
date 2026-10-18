"""Self-hosted authentication service.

OraOne signs users in with a one-time code sent by email (passwordless). A
password sign-in exists only for local development, behind an explicit
environment flag, so that seeded development accounts can be used without
mail delivery. It is refused in every production-like environment.

Responsibilities:
    * email-code sign-in (request a code, verify it, issue tokens)
    * development-only password sign-in
    * refresh-token rotation, logout and logout-all

Routes stay thin (see ``app/api/auth/routes.py``); this module holds the rules.
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import generate_numeric_code, hash_password, verify_password
from app.database.models.user import User
from app.database.repositories.user_repository import UserRepository
from app.schemas.auth import (
    EmailCodeRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokensResponse,
    VerifyLoginOtpRequest,
)
from app.services import token_service
from app.services.cache import get_shared_cache

log = logging.getLogger("app.auth.service")

#: How long an emailed sign-in code stays valid.
_LOGIN_CODE_TTL_SECONDS = 10 * 60
_CODE_CACHE_NAMESPACE = "auth"
_GUARD_CACHE_NAMESPACE = "auth-guard"

#: Failed code checks allowed per email before the pending code is invalidated.
MAX_CODE_ATTEMPTS = 5
#: Sign-in codes that may be emailed to one address per window.
MAX_CODE_SENDS = 5
#: Fixed window for both counters above.
_LIMIT_WINDOW_SECONDS = 15 * 60

_AUTH_UNAVAILABLE = "Sign-in is temporarily unavailable. Please try again shortly."


def _cache():
    """Shared cache used for short-lived sign-in codes."""
    return get_shared_cache(_CODE_CACHE_NAMESPACE)


def _code_key(email: str) -> str:
    """Cache key for the pending sign-in code of ``email``."""
    return f"login_otp:{email.strip().lower()}"


def _window_bucket() -> int:
    return int(time.time() // _LIMIT_WINDOW_SECONDS)


def _attempt_key(email: str) -> str:
    return f"otp_attempts:{email.strip().lower()}:{_window_bucket()}"


def _send_key(email: str) -> str:
    return f"otp_sends:{email.strip().lower()}:{_window_bucket()}"


@contextmanager
def _guard_store():
    """Yield the shared store used for attempt and send counters.

    Fails closed: if the store cannot be reached, or production has no shared
    backend (the in-process fallback is per worker and cannot enforce limits
    across workers), the request is refused with a retryable 503.
    """
    try:
        cache = get_shared_cache(_GUARD_CACHE_NAMESPACE)
        if cache.name == "inprocess" and settings.is_production:
            raise RuntimeError("shared guard store required in production")
        yield cache
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - any store failure must fail closed
        log.error("auth_guard_store_unavailable err=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_AUTH_UNAVAILABLE
        ) from exc


def _to_tokens_response(pair: token_service.TokenPair) -> TokensResponse:
    """Map an internal token pair to the public response schema."""
    return TokensResponse(
        access_token=pair.access_token,
        id_token=pair.access_token,  # single-token model; kept for API compatibility
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
    )


class EmailDeliveryError(RuntimeError):
    """The sign-in code could not be delivered, so no code was issued."""


async def request_email_code(session: AsyncSession, data: EmailCodeRequest) -> None:
    """Start a passwordless sign-in by emailing a one-time code.

    Unknown addresses get a new account with an unusable random password, so
    the emailed code is the only way in. Callers receive the same response
    whether or not the address has an account. The one exception is delivery
    failure: that is an outage of the mail service, not of the account, and
    raises EmailDeliveryError with the stored code removed.
    """
    from app.services.email_service import send_login_otp

    email = data.email.strip().lower()
    with _guard_store() as guard:
        sends = guard.increment(_send_key(email), ttl_seconds=_LIMIT_WINDOW_SECONDS)
    if sends > MAX_CODE_SENDS:
        # Same silent response as every other request, so the limit does not
        # reveal whether the address has an account.
        log.info("email_code_send_limited")
        return

    users = UserRepository(session)
    user = await users.get_by_email(email)
    if user is None:
        display_name = (data.name or "").strip() or email.split("@", 1)[0]
        user = User(
            auth_subject=str(uuid.uuid4()),
            email=email,
            full_name=display_name[:120],
            password_hash=hash_password(secrets.token_urlsafe(48)),
            is_email_verified=False,
        )
        subject = user.auth_subject
        session.add(user)
        await session.commit()
    else:
        subject = user.auth_subject
        if user.status.value != "active":
            log.info("email_code_skipped_inactive user=%s", subject)
            return

    code = generate_numeric_code()
    with _guard_store():
        _cache().set(_code_key(email), code, ttl_seconds=_LOGIN_CODE_TTL_SECONDS)
    if not send_login_otp(email, code=code):
        # Never report a code as issued when no email left the server.
        with _guard_store():
            _cache().delete(_code_key(email))
        log.error("email_code_not_delivered user=%s", subject)
        raise EmailDeliveryError("sign-in code could not be delivered")
    log.info("email_code_sent user=%s", subject)


async def verify_email_code(
    session: AsyncSession, data: VerifyLoginOtpRequest
) -> TokensResponse:
    """Check the emailed code, mark the address verified and issue tokens.

    Every check counts as an attempt, reserved atomically before the code is
    compared. After ``MAX_CODE_ATTEMPTS`` attempts in a window the pending code
    is invalidated and further attempts are refused. A code is single-use: it
    is deleted as soon as it is accepted.
    """
    email = data.email.strip().lower()
    with _guard_store() as guard:
        attempt = guard.increment(
            _attempt_key(email), ttl_seconds=_LIMIT_WINDOW_SECONDS
        )
        if attempt > MAX_CODE_ATTEMPTS:
            _cache().delete(_code_key(email))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many incorrect attempts. Request a new code later.",
            )

        stored = _cache().get(_code_key(email))
        if stored and hmac.compare_digest(str(stored), str(data.code)):
            _cache().delete(_code_key(email))
            guard.delete(_attempt_key(email))
        else:
            if attempt >= MAX_CODE_ATTEMPTS:
                _cache().delete(_code_key(email))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect or expired code.",
            )

    users = UserRepository(session)
    user = await users.get_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with this email.",
        )
    user.is_email_verified = True
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()
    return _issue_tokens(user)


async def dev_password_login(
    session: AsyncSession, data: LoginRequest
) -> TokensResponse:
    """Sign in with a password, for local development only.

    Refused unless ``ENVIRONMENT=development`` and ``ALLOW_DEV_PASSWORD_LOGIN=true``.
    The endpoint responds with 404 in every other case, so it is not discoverable.
    """
    if not _dev_password_login_allowed():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    users = UserRepository(session)
    user = await users.get_by_email(data.email)
    if user is None or not verify_password(data.password, user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled.",
        )
    user.last_login_at = datetime.now(timezone.utc)
    await session.commit()
    log.warning("dev_password_login user=%s", user.auth_subject)
    return _issue_tokens(user)


def _dev_password_login_allowed() -> bool:
    """Development password sign-in is opt-in and never allowed in production."""
    return (
        settings.environment == "development"
        and os.environ.get("ALLOW_DEV_PASSWORD_LOGIN", "false").strip().lower()
        == "true"
    )


def _issue_tokens(user: User) -> TokensResponse:
    """Issue a token pair for ``user``; the subject is their auth subject."""
    try:
        pair = token_service.issue_token_pair(
            user_id=user.auth_subject, email=user.email, name=user.full_name
        )
    except Exception as exc:  # noqa: BLE001 - never leak internals to the client
        log.error("token_issue_failed user=%s err=%s", user.auth_subject, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-in is temporarily unavailable. Please try again shortly.",
        )
    return _to_tokens_response(pair)


async def refresh_tokens(data: RefreshTokenRequest) -> TokensResponse:
    """Rotate a refresh token and return a new token pair."""
    try:
        pair = token_service.rotate(data.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
        )
    except Exception as exc:  # noqa: BLE001 - the token store is unreachable
        log.error("token_refresh_failed err=%s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session refresh is temporarily unavailable. Please try again shortly.",
        )
    return _to_tokens_response(pair)


def logout(refresh_token: str | None) -> None:
    """Revoke the presented refresh token. Logout always succeeds for the caller."""
    if refresh_token:
        try:
            token_service.revoke(refresh_token)
        except Exception:  # noqa: BLE001 - best effort
            pass


def logout_all(user_id: str) -> None:
    """Revoke every refresh token for ``user_id`` on every device."""
    try:
        token_service.revoke_all_for_user(user_id)
    except Exception:  # noqa: BLE001 - best effort
        pass
