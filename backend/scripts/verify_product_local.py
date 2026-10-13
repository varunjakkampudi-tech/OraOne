"""Test a real development API with synthetic data and free OpenRouter inference.

Run the API and this script with AI_FORCE_MODEL=openrouter/free. Only loopback
development databases are permitted. OTPs are read from local Redis; this does
not test inbox delivery. Credentials and model answers are never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import secrets
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=False)

from app.core.config import settings  # noqa: E402
from app.services import auth_service  # noqa: E402


def validate(base: str) -> None:
    target = urlsplit(base)
    db_host = urlsplit(os.getenv("DATABASE_URL", "")).hostname or os.getenv("DB_HOST")
    if target.scheme != "http" or target.hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Only loopback HTTP is permitted.")
    if (
        db_host not in {"localhost", "127.0.0.1"}
        or settings.environment != "development"
    ):
        raise RuntimeError("Only a local development database is permitted.")
    if os.getenv("S3_BUCKET") and urlsplit(
        os.getenv("S3_ENDPOINT_URL", "")
    ).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Object storage must be a local MinIO endpoint.")
    if settings.auth_provider != "self_hosted":
        raise RuntimeError("This test requires self-hosted local auth.")
    if any(os.getenv(k) for k in ("SMTP_HOST", "EMAIL_FROM", "SES_FROM_EMAIL")):
        raise RuntimeError("Synthetic tests require email delivery to be disabled.")
    if os.getenv("AI_FORCE_MODEL") != "openrouter/free":
        raise RuntimeError(
            "Start both API and test with AI_FORCE_MODEL=openrouter/free."
        )
    catalog = requests.get("https://openrouter.ai/api/v1/models", timeout=20)
    catalog.raise_for_status()
    entry = next(
        (m for m in catalog.json()["data"] if m["id"] == "openrouter/free"), None
    )
    if not entry or any(
        float(entry["pricing"][k]) != 0 for k in ("prompt", "completion")
    ):
        raise RuntimeError("The test model does not currently have zero token pricing.")


async def cleanup(email: str) -> None:
    from sqlalchemy import delete, select
    from app.database import session as db
    from app.database.models.organization import Organization
    from app.database.models.user import User
    from app.database.models.document import Document
    from app.services import storage

    if settings.environment != "development" or urlsplit(
        os.getenv("DATABASE_URL", "")
    ).hostname not in {"localhost", "127.0.0.1"}:
        raise RuntimeError("Cleanup requires the local development database.")

    if not email.startswith("oraone-local-e2e-") or not email.endswith("@example.com"):
        raise RuntimeError("Cleanup refused a non-synthetic account.")
    db.init_engine()
    async with db.AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user:
            org_ids = list(
                await session.scalars(
                    select(Organization.id).where(Organization.owner_user_id == user.id)
                )
            )
            docs = await session.scalars(
                select(Document).where(Document.organization_id.in_(org_ids))
            )
            for doc in docs:
                key = doc.s3_key.removeprefix("local://")
                if not any(key.startswith(f"org/{org_id}/kb/") for org_id in org_ids):
                    raise RuntimeError(
                        "Storage cleanup refused an unexpected object key."
                    )
                if storage.is_local_key(doc.s3_key):
                    storage.local_path(doc.s3_key).unlink(missing_ok=True)
                else:
                    storage._client().delete_object(Bucket=storage._bucket(), Key=key)
            await session.execute(
                delete(Organization).where(Organization.owner_user_id == user.id)
            )
            await session.execute(delete(User).where(User.id == user.id))
            await session.commit()
    for key in (
        auth_service._verify_code_key,
        auth_service._login_otp_key,
        auth_service._reset_code_key,
    ):
        auth_service._cache().delete(key(email))
    await db.dispose_engine()


def run(base: str, email: str, results: list[dict], *, skip_ai: bool = False) -> None:
    client = requests.Session()

    def check(method, path, expected=(200,), **kwargs):
        response = client.request(method, base + path, timeout=90, **kwargs)
        passed = response.status_code in expected
        results.append(
            {
                "method": method,
                "path": path,
                "status": response.status_code,
                "passed": passed,
            }
        )
        if not passed:
            raise RuntimeError(
                f"{method} {path}: unexpected HTTP {response.status_code}"
            )
        return response.json() if response.content else None

    password = "Aa1!" + secrets.token_urlsafe(24)
    check(
        "POST",
        "/api/auth/signup",
        json={"email": email, "password": password, "name": "Local integration test"},
    )
    code = auth_service._cache().get(auth_service._verify_code_key(email))
    if not code:
        raise RuntimeError("Verification code missing from shared Redis.")
    check("POST", "/api/auth/verify", json={"email": email, "code": code})
    login = check(
        "POST", "/api/auth/login", json={"email": email, "password": password}
    )
    if not login.get("otp_required"):
        raise RuntimeError("Login did not require OTP.")
    code = auth_service._cache().get(auth_service._login_otp_key(email))
    tokens = check(
        "POST", "/api/auth/login/verify-otp", json={"email": email, "code": code}
    )
    client.headers["Authorization"] = "Bearer " + tokens["access_token"]
    profile = check("GET", "/api/auth/me")
    if profile.get("role") != "user":
        raise RuntimeError("New signup did not default to the user role.")
    check("GET", "/api/auth/identity")
    check("GET", "/api/super-admin/me", expected=(403,))
    project = check(
        "POST",
        "/api/projects",
        expected=(201,),
        json={"name": "Local integration project"},
    )
    client.headers["X-Project-Id"] = project["id"]
    kb = check(
        "POST",
        "/api/knowledge-bases",
        expected=(201,),
        json={"name": "Local integration knowledge", "status": "active"},
    )
    doc = check(
        "POST",
        "/api/documents/upload",
        expected=(201,),
        data={"knowledge_base_id": kb["id"]},
        files={
            "file": (
                "local-facts.txt",
                b"The secret verification phrase is PINEAPPLE-42. OraOne local test knowledge.",
                "text/plain",
            )
        },
    )
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        processed = check("GET", f"/api/documents/{doc['id']}")
        if processed["status"] == "processed":
            if not processed.get("chunk_count") or not processed.get("embedded_count"):
                raise RuntimeError("Document completed without indexed embeddings.")
            break
        if processed["status"] == "failed":
            raise RuntimeError("Document processing failed.")
        time.sleep(1)
    else:
        raise RuntimeError("Document indexing exceeded 45 seconds.")
    agent = check(
        "POST",
        "/api/agents",
        expected=(201,),
        json={
            "name": "Local integration agent",
            "type": "chat",
            "model": "openrouter/free",
            "max_tokens": 256,
            "system_prompt": "Answer using supplied context in one sentence.",
            "knowledge_base_ids": [kb["id"]],
        },
    )
    check("PUT", f"/api/agents/{agent['id']}", json={"status": "active"})
    saved_agent = check("GET", f"/api/agents/{agent['id']}")
    assert saved_agent["knowledge_base_ids"] == [kb["id"]]
    analytics = check(
        "GET", "/api/analytics/agents", params={"agent_id": agent["id"], "days": 30}
    )
    assert [row["agent_id"] for row in analytics["agents"]] == [agent["id"]]
    check("GET", f"/api/agents/{agent['id']}/channels")
    check("GET", f"/api/agents/{agent['id']}/deploy")
    widget = check(
        "POST",
        "/api/widgets",
        expected=(201,),
        json={
            "name": "Local integration widget",
            "agent_id": agent["id"],
            "knowledge_base_id": kb["id"],
            "domains": ["localhost", "127.0.0.1"],
        },
    )
    check("POST", f"/api/widgets/{widget['id']}/publish", params={"publish": "true"})
    check(
        "POST",
        "/api/widget/chat",
        expected=(403,),
        headers={"Origin": "https://unauthorized.example"},
        json={
            "public_key": widget["public_key"],
            "visitor_id": "denied-test",
            "message": "Hello",
        },
    )
    if not skip_ai:
        answer = check(
            "POST",
            "/api/widget/chat",
            headers={"Origin": "http://localhost:3001"},
            json={
                "public_key": widget["public_key"],
                "visitor_id": "v_" + uuid.uuid4().hex,
                "message": "What is the secret verification phrase?",
            },
        )
        results.append(
            {
                "operation": "real_free_openrouter_grounded_answer",
                "grounded": bool(answer.get("grounded")),
                "model": answer.get("model"),
                "expected_phrase_present": "PINEAPPLE-42" in answer.get("answer", ""),
                "passed": bool(
                    answer.get("grounded")
                    and "PINEAPPLE-42" in answer.get("answer", "")
                ),
            }
        )
    lead = check(
        "POST",
        "/api/leads",
        expected=(200, 201),
        json={"name": "Synthetic local lead", "email": email},
    )
    check(
        "PATCH",
        f"/api/leads/{lead['id']}",
        json={"status": "qualified", "notes": "Local integration check"},
    )
    check("GET", f"/api/leads/{lead['id']}")
    workflow = check(
        "POST",
        "/api/workflows",
        expected=(201,),
        json={"name": "Local integration workflow", "trigger_type": "manual"},
    )
    check("GET", f"/api/workflows/{workflow['id']}")
    check(
        "POST",
        "/api/webhooks",
        expected=(422,),
        json={"url": "http://127.0.0.1:9000", "events": []},
    )
    for path in (
        "/api/analytics/overview",
        "/api/usage",
        "/api/team/members",
        "/api/integrations",
        "/api/api-keys",
        "/api/ai/models",
    ):
        check("GET", path)
    check("DELETE", f"/api/documents/{doc['id']}", expected=(200, 204))
    check("POST", "/api/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    check(
        "POST",
        "/api/auth/refresh",
        expected=(401,),
        json={"refresh_token": tokens["refresh_token"]},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Run independent workflows without an external generation request",
    )
    args = parser.parse_args()
    validate(args.base_url)
    email = "oraone-local-e2e-" + uuid.uuid4().hex + "@example.com"
    results = []
    try:
        run(args.base_url.rstrip("/"), email, results, skip_ai=args.skip_ai)
        failures = sum(not result["passed"] for result in results)
        print(
            f"Real local Product 1 checks: {len(results)}; failures={failures}; AI skipped={args.skip_ai}"
        )
        return 1 if failures else 0
    finally:
        asyncio.run(cleanup(email))
        report_name = (
            "local-product-verification-no-ai.json"
            if args.skip_ai
            else "local-product-verification.json"
        )
        output = ROOT / "output" / report_name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps({"ai_skipped": args.skip_ai, "checks": results}, indent=2),
            encoding="utf-8",
        )
        print("Synthetic workspace removed; sanitized evidence saved.")


if __name__ == "__main__":
    raise SystemExit(main())
