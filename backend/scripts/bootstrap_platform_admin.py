"""Promote an existing user to the initial platform admin.

This command never creates a user or password. It requires an operator to
provide the exact auth subject and an out-of-band approval environment
variable, making the promotion an explicit platform-owner process.

Required environment variables:
  DATABASE_URL (or DB_* variables)
  PLATFORM_BOOTSTRAP_APPROVED_SUBJECT=<same auth subject passed on the command line>
  PLATFORM_BOOTSTRAP_CONFIRM=PROMOTE_TO_SUPER_ADMIN

Usage:
  python scripts/bootstrap_platform_admin.py --auth-subject <verified-subject>
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.database.models.user import User, UserRole
from app.database.session import session_scope
from app.services.audit import audit


async def promote(auth_subject: str) -> int:
    approved = os.environ.get("PLATFORM_BOOTSTRAP_APPROVED_SUBJECT", "").strip()
    if not approved or approved != auth_subject:
        raise SystemExit(
            "PLATFORM_BOOTSTRAP_APPROVED_SUBJECT must exactly match --auth-subject."
        )
    if os.environ.get("PLATFORM_BOOTSTRAP_CONFIRM") != "PROMOTE_TO_SUPER_ADMIN":
        raise SystemExit(
            "Set PLATFORM_BOOTSTRAP_CONFIRM=PROMOTE_TO_SUPER_ADMIN to authorize this one-time action."
        )

    async with session_scope() as session:
        user = await session.scalar(
            select(User).where(User.auth_subject == auth_subject)
        )
        if user is None:
            raise SystemExit(
                "No existing user found for this auth subject; sign in and hydrate identity first."
            )
        if user.role == UserRole.super_admin:
            print(f"Already super_admin: {user.email}")
            return 0
        before = user.role.value
        user.role = UserRole.super_admin
        audit(
            "platform.user.bootstrap_super_admin",
            resource="user",
            organization_id="",
            user_id=str(user.id),
            resource_id=str(user.id),
            before={"role": before},
            after={"role": UserRole.super_admin.value},
            meta={"auth_subject": auth_subject, "operator_approved": True},
        )
        print(f"Promoted {user.email} from {before} to super_admin")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-subject", required=True)
    args = parser.parse_args()
    return asyncio.run(promote(args.auth_subject))


if __name__ == "__main__":
    raise SystemExit(main())
