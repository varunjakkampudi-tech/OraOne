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

import asyncio
import hashlib
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
from app.core.log_redaction import redact_email
from app.core.security import generate_numeric_code, hash_password, verify_password
from app.database.models.user import User
from app.database.models.signup_consent import SignupConsent
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

#: How long an emailed sign-in code stays valid (5 minutes). Single use.
_LOGIN_CODE_TTL_SECONDS = 5 * 60
#: Minimum gap between two codes for the same address (resend cooldown).
RESEND_COOLDOWN_SECONDS = 60
_CODE_CACHE_NAMESPACE = "auth"
_GUARD_CACHE_NAMESPACE = "auth-guard"
_LOGIN_OTP_DIGEST_CONTEXT = b"oraone-login-otp-v1\x00"

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


def _cooldown_key(email: str) -> str:
    return f"otp_cooldown:{email.strip().lower()}"


def _guard_cache():
    return get_shared_cache(_GUARD_CACHE_NAMESPACE)


def _digest(email: str, code: str) -> str:
    """Keyed digest of a sign-in code. Only this digest is stored, never the code.

    HMAC-SHA256 with a key derived from the server secret, so a leaked cache
    cannot be replayed offline into valid codes. The address is part of the
    message, so a digest for one address does not match another.
    """
    secret = settings.jwt_secret_key
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is required to hash sign-in codes")
    key = hashlib.sha256(_LOGIN_OTP_DIGEST_CONTEXT + secret.encode("utf-8")).digest()
    message = f"{email}\x1f{code}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


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

    The response is the same whatever the address is: the same work runs for an
    existing account, a new address and an inactive account (one read, one code,
    one stored digest, one email). Accounts are created when a correct code is
    entered, not when a code is requested, so a request never writes a row.
    Requests held back by the cooldown or the send limit are silent too.

    The one exception is delivery failure. That is an outage of the mail
    service, not of any account, so it is reported and the stored code removed.
    """
    from app.services.email_service import send_login_otp

    email = data.email.strip().lower()
    with _guard_store() as guard:
        # Cooldown: at most one code per address per RESEND_COOLDOWN_SECONDS.
        if not guard.set_if_not_exists(
            _cooldown_key(email), 1, ttl_seconds=RESEND_COOLDOWN_SECONDS
        ):
            log.info("email_code_cooldown")
            return
        sends = guard.increment(_send_key(email), ttl_seconds=_LIMIT_WINDOW_SECONDS)
    if sends > MAX_CODE_SENDS:
        log.info("email_code_send_limited")
        return

    # The same read for every address, so a request costs the same database work
    # whether or not an account exists.
    await UserRepository(session).get_by_email(email)

    code = generate_numeric_code()  # six digits from the OS CSPRNG
    pending = {
        "digest": _digest(email, code),
        "name": (data.name or "").strip()[:120] or None,
    }
    with _guard_store():
        _cache().set(_code_key(email), pending, ttl_seconds=_LOGIN_CODE_TTL_SECONDS)
    try:
        delivered = await asyncio.to_thread(send_login_otp, email, code=code)
    except Exception as exc:  # noqa: BLE001 - any sender failure means no code left the server
        log.error(
            "email_code_send_error email=%s err=%s",
            redact_email(email),
            type(exc).__name__,
        )
        delivered = False
    if not delivered:
        # Never report a code as issued when no email left the server. Clear the
        # code and the cooldown so the user can ask again straight away.
        with _guard_store():
            _cache().delete(_code_key(email))
            _guard_cache().delete(_cooldown_key(email))
        log.error("email_code_not_delivered email=%s", redact_email(email))
        raise EmailDeliveryError("sign-in code could not be delivered")
    log.info("email_code_sent email=%s", redact_email(email))


def _require_signup_acceptance(data: VerifyLoginOtpRequest) -> None:
    """Refuse to create an account unless the signup legal terms were accepted as shown.

    Runs after the code matched and before it is spent, so a missing tick box does not
    burn a valid code. The client must send the exact versions it displayed.
    """
    if settings.is_production and not settings.legal_versions_approved:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-up is temporarily unavailable. Please try again later.",
        )
    if not (data.terms_accepted and data.privacy_accepted):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accept the Terms of Service and the Privacy Policy to create an account.",
        )
    if (
        data.terms_version != settings.legal_terms_version
        or data.privacy_version != settings.legal_privacy_version
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The legal documents have changed. Review them again and continue.",
        )


async def verify_email_code(
    session: AsyncSession, data: VerifyLoginOtpRequest
) -> TokensResponse:
    """Check the emailed code, then sign the address in.

    Every check counts as an attempt, reserved atomically before the code is
    compared. After ``MAX_CODE_ATTEMPTS`` attempts in a window the pending code
    is invalidated and further attempts are refused. A code is single use: it is
    spent with an atomic consume, so two concurrent requests with the right code
    cannot both sign in. A stored value that is not a digest (for example a plain
    code written before this change) never matches.

    A new address gets its account here, in the same transaction as its signup
    consent records, and only after the required acceptances were sent as shown.
    Existing active accounts sign in exactly as before. Disabled accounts get the
    same generic error as a wrong code.
    """
    email = data.email.strip().lower()
    with _guard_store() as guard:
        attempt = guard.increment(
            _attempt_key(email), ttl_seconds=_LIMIT_WINDOW_SECONDS
        )
        if attempt > MAX_CODE_ATTEMPTS:
            _cache().delete(_code_key(email))
            log.warning("email_code_locked email=%s", redact_email(email))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many incorrect attempts. Request a new code later.",
            )

        pending = _cache().get(_code_key(email))
        matched = isinstance(pending, dict) and hmac.compare_digest(
            str(pending.get("digest", "")), _digest(email, str(data.code))
        )
        if not matched:
            if attempt >= MAX_CODE_ATTEMPTS:
                _cache().delete(_code_key(email))
            log.info("email_code_rejected attempt=%d", attempt)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect or expired code.",
            )
        name = pending.get("name")

    users = UserRepository(session)
    user = await users.get_by_email(email)
    if user is None:
        _require_signup_acceptance(data)

    with _guard_store() as guard:
        # Atomic spend: only one request can take the pending code.
        if _cache().consume(_code_key(email)) is None:
            log.info("email_code_already_used")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect or expired code.",
            )
        guard.delete(_attempt_key(email))

    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            auth_subject=str(uuid.uuid4()),
            email=email,
            full_name=(name or email.split("@", 1)[0])[:120],
            password_hash=hash_password(secrets.token_urlsafe(48)),
            is_email_verified=True,
        )
        session.add(user)
        await session.flush()  # the consent rows need the new user id
        for document, version, granted in (
            ("terms", settings.legal_terms_version, True),
            ("privacy", settings.legal_privacy_version, True),
            (
                "marketing",
                settings.legal_marketing_version,
                bool(data.marketing_consent),
            ),
        ):
            session.add(
                SignupConsent(
                    user_id=user.id,
                    document=document,
                    version=version,
                    granted=granted,
                    recorded_at=now,
                )
            )
        log.info("signup_recorded user=%s", user.auth_subject)
    elif user.status.value != "active":
        log.info("email_code_refused_inactive email=%s", redact_email(email))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect or expired code.",
        )
    user.is_email_verified = True
    user.last_login_at = now
    await session.commit()
    log.info("email_code_verified user=%s", user.auth_subject)
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
