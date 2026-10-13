"""Safely smoke-test local email/password + verification/login OTP auth.

This script only targets a loopback OraOne API, refuses configured email
delivery, creates unique synthetic users, keeps OTPs/tokens out of output, and
deletes only those exact users when finished. It does not verify real inbox
delivery or Cognito.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / ".env", override=False)

from app.core.config import settings  # noqa: E402
from app.services import auth_service  # noqa: E402

EMAIL_DELIVERY_KEYS = ("SMTP_HOST", "EMAIL_FROM", "SES_FROM_EMAIL")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Loopback URL for the local OraOne API (default: %(default)s)",
    )
    parser.add_argument("--timeout", type=float, default=10)
    return parser.parse_args()


def _validate_local_only(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise SystemExit("Refusing auth smoke test: --base-url must be loopback HTTP.")
    if settings.auth_provider != "self_hosted":
        raise SystemExit(
            "Refusing auth smoke test: the backend must use local self_hosted auth."
        )
    configured_delivery = [key for key in EMAIL_DELIVERY_KEYS if os.environ.get(key)]
    if configured_delivery:
        raise SystemExit(
            "Refusing auth smoke test because real email delivery is configured: "
            + ", ".join(configured_delivery)
        )
    return base_url.rstrip("/")


def _require_status(response: requests.Response, expected: int, operation: str) -> None:
    if response.status_code != expected:
        raise RuntimeError(f"{operation} failed with HTTP {response.status_code}.")


def run_user(base_url: str, timeout: float, created_emails: list[str]) -> None:
    email = f"oraone-local-otp-{uuid.uuid4().hex}@example.com"
    password = "Aa1!" + secrets.token_urlsafe(18)
    created_emails.append(email)

    signup = requests.post(
        f"{base_url}/api/auth/signup",
        json={"email": email, "password": password, "name": "Local Auth Smoke"},
        timeout=timeout,
    )
    _require_status(signup, 200, "Signup")
    verify_code = auth_service._cache().get(auth_service._verify_code_key(email))
    if not verify_code:
        raise RuntimeError("Signup did not create a verification code in shared cache.")

    verification = requests.post(
        f"{base_url}/api/auth/verify",
        json={"email": email, "code": verify_code},
        timeout=timeout,
    )
    _require_status(verification, 200, "Email verification")

    login = requests.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=timeout,
    )
    _require_status(login, 200, "Password login")
    if not login.json().get("otp_required"):
        raise RuntimeError("Password login did not require the expected OTP step.")

    login_code = auth_service._cache().get(auth_service._login_otp_key(email))
    if not login_code:
        raise RuntimeError("Login did not create an OTP in shared cache.")

    verified_login = requests.post(
        f"{base_url}/api/auth/login/verify-otp",
        json={"email": email, "code": login_code},
        timeout=timeout,
    )
    _require_status(verified_login, 200, "Login OTP verification")
    tokens = verified_login.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not access_token or not refresh_token:
        raise RuntimeError("OTP verification did not issue the expected session.")

    profile = requests.get(
        f"{base_url}/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=timeout,
    )
    _require_status(profile, 200, "Authenticated profile")
    if profile.json().get("email") != email:
        raise RuntimeError("Authenticated profile did not match the synthetic user.")

    logout = requests.post(
        f"{base_url}/api/auth/logout",
        json={"refresh_token": refresh_token},
        timeout=timeout,
    )
    _require_status(logout, 200, "Logout")


async def cleanup_exact_users(emails: list[str]) -> int:
    if not emails:
        return 0

    from sqlalchemy import select

    from app.database import session as db_session_module
    from app.database.models.user import User

    db_session_module.init_engine()
    deleted = 0
    async with db_session_module.AsyncSessionLocal() as session:
        rows = (await session.scalars(select(User).where(User.email.in_(emails)))).all()
        for user in rows:
            await session.delete(user)
            deleted += 1
        await session.commit()
    for email in emails:
        auth_service._cache().delete(auth_service._verify_code_key(email))
        auth_service._cache().delete(auth_service._login_otp_key(email))
        auth_service._cache().delete(auth_service._reset_code_key(email))
    return deleted


def main() -> int:
    args = _parse_args()
    base_url = _validate_local_only(args.base_url)
    created_emails: list[str] = []
    succeeded = False
    try:
        run_user(base_url, args.timeout, created_emails)
        succeeded = True
        print(
            "Local email/password + verification OTP + login OTP + profile + logout: PASS"
        )
        return 0
    finally:
        deleted = asyncio.run(cleanup_exact_users(created_emails))
        print(f"Synthetic accounts created={len(created_emails)} cleaned={deleted}")
        if succeeded and deleted != len(created_emails):
            raise RuntimeError("Cleanup did not remove every synthetic test account.")


if __name__ == "__main__":
    raise SystemExit(main())
