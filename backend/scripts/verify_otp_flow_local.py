"""One-off local verification script (not part of the test suite):
signup -> verify-email -> login -> otp -> verify-otp -> /me, for two dummy
users, then delete them from the DB. Talks to the real running backend on
:8001 over HTTP, exactly like the frontend would.
"""
import asyncio
import os
import secrets
import sys
import uuid
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8001"
# Ephemeral password for throwaway dummy users — never hardcode a secret.
PASSWORD = os.environ.get("OTP_TEST_PASSWORD") or ("Aa1!" + secrets.token_urlsafe(12))


def run_user(n: int):
    email = f"dummy-otp-{n}-{uuid.uuid4().hex[:8]}@example.com"
    print(f"\n=== user {n}: {email} ===")

    r = requests.post(f"{BASE}/api/auth/signup", json={"email": email, "password": PASSWORD, "name": f"Dummy {n}"})
    print("signup:", r.status_code, r.json())
    assert r.status_code == 200

    # Fetch the email-verification code the same way the real inbox would show it
    from app.services import auth_service
    verify_code = auth_service._cache().get(auth_service._verify_code_key(email))
    assert verify_code, "verification code missing from cache"
    r = requests.post(f"{BASE}/api/auth/verify", json={"email": email, "code": verify_code})
    print("verify:", r.status_code, r.json())
    assert r.status_code == 200

    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": PASSWORD})
    print("login (expect otp_required):", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json().get("otp_required") is True

    otp_code = auth_service._cache().get(auth_service._login_otp_key(email))
    assert otp_code, "login OTP missing from cache (email OTP was not generated!)"
    print("login OTP retrieved from cache:", otp_code)

    r = requests.post(f"{BASE}/api/auth/login/verify-otp", json={"email": email, "code": otp_code})
    print("verify-otp:", r.status_code)
    assert r.status_code == 200
    tokens = r.json()
    assert tokens.get("access_token"), "no access token returned after OTP verification"

    r = requests.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    print("me:", r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["email"] == email

    print(f"user {n}: FULL OTP LOGIN FLOW OK")
    return email


async def cleanup():
    """Delete every dummy-otp-* test user, including any left over from a
    previously interrupted run of this script."""
    from sqlalchemy import select

    from app.database import session as db_session_module
    from app.database.models.user import User

    db_session_module.init_engine()
    async with db_session_module.AsyncSessionLocal() as s:
        rows = (await s.scalars(select(User).where(User.email.like("dummy-otp-%")))).all()
        for u in rows:
            await s.delete(u)
        await s.commit()
    print(f"\ncleanup: deleted {len(rows)} dummy user(s)")


if __name__ == "__main__":
    run_user(1)
    run_user(2)
    asyncio.run(cleanup())
