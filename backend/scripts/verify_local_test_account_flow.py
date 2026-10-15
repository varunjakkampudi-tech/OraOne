"""Exercise the real password + OTP session lifecycle for the local QA account.

Reads the OTP from the local backend cache (development only), so it must run
on the same machine as the API. Usage:
    ORAONE_LOCAL_TEST_PASSWORD=... python scripts/verify_local_test_account_flow.py --base-url http://127.0.0.1:8001
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import httpx  # noqa: E402

from scripts.seed_local_test_account import TEST_EMAIL, validate_local_environment  # noqa: E402


def check(label: str, ok: bool) -> None:
    print(f"{'PASS' if ok else 'FAIL'} {label}")
    if not ok:
        raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    base = parser.parse_args().base_url.rstrip("/")
    password = validate_local_environment()
    from app.services import auth_service

    with httpx.Client(base_url=base, timeout=20) as c:
        bad = c.post(
            "/api/auth/login",
            json={"email": TEST_EMAIL, "password": "wrong-password-123"},
        )
        check("wrong password rejected", bad.status_code in (400, 401))

        r = c.post("/api/auth/login", json={"email": TEST_EMAIL, "password": password})
        check(
            "password step requires OTP (no tokens issued)",
            r.status_code == 200 and "access_token" not in r.text,
        )

        wrong = c.post(
            "/api/auth/login/verify-otp", json={"email": TEST_EMAIL, "code": "000000"}
        )
        check("wrong OTP rejected", wrong.status_code in (400, 401))
        # A wrong attempt may invalidate the code; request a fresh one.
        c.post("/api/auth/login", json={"email": TEST_EMAIL, "password": password})
        code = auth_service._cache().get(auth_service._login_otp_key(TEST_EMAIL))
        check("OTP present in local cache", bool(code))

        v = c.post(
            "/api/auth/login/verify-otp", json={"email": TEST_EMAIL, "code": code}
        )
        check("OTP verification issues session", v.status_code == 200)
        replay = c.post(
            "/api/auth/login/verify-otp", json={"email": TEST_EMAIL, "code": code}
        )
        check("OTP is single-use", replay.status_code in (400, 401))

        tokens = v.json()
        auth = {"Authorization": f"Bearer {tokens['access_token']}"}
        c.cookies.clear()
        me = c.get("/api/auth/me", headers=auth)
        body = me.json() if me.status_code == 200 else {}
        check(
            "/api/auth/me authenticated",
            me.status_code == 200 and body.get("email") == TEST_EMAIL,
        )
        check("platform role is user (not admin)", body.get("role") == "user")
        check("unauthenticated /me rejected", c.get("/api/auth/me").status_code == 401)

        admin = c.get("/api/admin/stats", headers=auth)
        check("platform admin API denied", admin.status_code in (401, 403, 404))

        old_refresh = tokens["refresh_token"]
        rf = c.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        check("refresh rotates session", rf.status_code == 200)
        new_refresh = rf.json()["refresh_token"]
        c.cookies.clear()
        rr = c.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        check("rotated refresh token cannot be reused", rr.status_code in (400, 401))

        lo = c.post("/api/auth/logout", json={"refresh_token": new_refresh})
        check("logout succeeds", lo.status_code == 200)
        c.cookies.clear()
        after = c.post("/api/auth/refresh", json={"refresh_token": new_refresh})
        check("refresh rejected after logout", after.status_code in (400, 401))
    print("Local QA account lifecycle verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
