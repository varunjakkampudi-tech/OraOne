"""Create the opt-in, unprivileged OraOne local QA account.

This script never runs at application startup. It deliberately refuses staging,
production, remote DB hosts, Cognito mode, or missing operator acknowledgement.
The fixture still uses the normal password + OTP login flow. It does not bypass
authentication, elevate roles, or introduce a static credential into the server.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.engine.url import make_url

from app.core.security import hash_password, verify_password
from app.database.models.user import User, UserRole, UserStatus
from app.database.session import session_scope

TEST_EMAIL = "test@oraone.in"
_ACK = "I_UNDERSTAND_THIS_IS_LOCAL_ONLY"
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def validate_local_environment() -> str:
    """Fail closed before opening a DB session or modifying any user."""
    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    provider = os.environ.get("AUTH_PROVIDER", "").strip().lower()
    if environment != "development" or provider != "self_hosted":
        raise RuntimeError(
            "Local fixture requires explicit ENVIRONMENT=development and "
            "AUTH_PROVIDER=self_hosted."
        )
    if os.environ.get("ORAONE_LOCAL_TEST_ACK") != _ACK:
        raise RuntimeError(
            "Set ORAONE_LOCAL_TEST_ACK=I_UNDERSTAND_THIS_IS_LOCAL_ONLY to opt in."
        )

    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if raw_url:
        try:
            hostname = make_url(raw_url).host
        except Exception as exc:
            raise RuntimeError("DATABASE_URL is malformed.") from exc
    else:
        hostname = os.environ.get("DB_HOST", "").strip()

    if hostname not in _LOCAL_HOSTS:
        raise RuntimeError(
            "Refusing local QA seed: database host must be an explicit "
            "localhost/loopback address. Remote or Docker-network hosts are forbidden."
        )

    password = os.environ.get("ORAONE_LOCAL_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set ORAONE_LOCAL_TEST_PASSWORD in your local environment.")
    if len(password) < 12:
        raise RuntimeError("Local test password must have at least 12 characters.")
    return password


async def seed() -> None:
    password = validate_local_environment()
    async with session_scope() as session:
        existing = await session.scalar(select(User).where(User.email == TEST_EMAIL))
        if existing is not None:
            if (
                existing.role != UserRole.user
                or existing.status != UserStatus.active
                or not existing.is_email_verified
                or not verify_password(password, existing.password_hash or "")
            ):
                raise RuntimeError(
                    "Account already exists with a different password, status, "
                    "verification state, or privilege. Refusing to modify it."
                )
            print("Local QA account already exists, credentials match; no changes made.")
            return

        session.add(
            User(
                cognito_sub=str(uuid.uuid4()),
                email=TEST_EMAIL,
                full_name="OraOne Local QA",
                password_hash=hash_password(password),
                is_email_verified=True,
                role=UserRole.user,
                status=UserStatus.active,
            )
        )
    print(
        "Created local QA account test@oraone.in (platform role: user). "
        "Use the existing password + OTP login flow."
    )


def main() -> int:
    asyncio.run(seed())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
