"""Prove uploaded knowledge survives an object-store + API restart.

Uploads a synthetic document, waits for indexing, runs the operator-supplied
restart command (e.g. restarting MinIO and the API), then re-reads the stored
object through the API and re-runs retrieval. Loopback development only.
    python scripts/verify_storage_recovery_local.py --restart-cmd "sh restart.sh"
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_product_local import cleanup, validate  # noqa: E402
from scripts.verify_security_local import Actor, results, wait_processed  # noqa: E402

PHRASE = b"OraOne storage recovery marker KIWI-5150."


def wait_ready(base: str) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            if requests.get(base + "/api/health/ready", timeout=5).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise RuntimeError("API did not become ready after restart.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--restart-cmd", required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    validate(base)
    a = Actor(base, "A")
    try:
        a.signup()
        project = a.req("POST", "/api/projects", (201,), json={"name": "Storage drill"})
        a.s.headers["X-Project-Id"] = project["id"]
        kb = a.req(
            "POST",
            "/api/knowledge-bases",
            (201,),
            json={"name": "Drill KB", "status": "active"},
        )
        doc = a.req(
            "POST",
            "/api/documents/upload",
            (201,),
            data={"knowledge_base_id": kb["id"]},
            files={"file": ("recovery.txt", PHRASE, "text/plain")},
        )
        wait_processed(a, doc["id"])
        subprocess.run(args.restart_cmd, shell=True, check=True)
        wait_ready(base)
        a.req(
            "POST",
            f"/api/documents/{doc['id']}/process",
            (200, 202),
            name="re-process reads object from storage",
        )
        time.sleep(2)
        wait_processed(a, doc["id"])
        preview = a.req(
            "GET",
            f"/api/documents/{doc['id']}/preview",
            name="re-extracted text readable",
        )
        ok = "KIWI-5150" in str(preview)
        results.append({"check": "stored bytes intact after restart", "passed": ok})
        print(("PASS" if ok else "FAIL") + " stored bytes intact after restart")
        hits = a.req(
            "POST",
            "/api/knowledge/search",
            json={"query": "storage recovery marker", "knowledge_base_ids": [kb["id"]]},
            name="retrieval after restart",
        )
        ok = "KIWI-5150" in str(hits)
        results.append({"check": "vector retrieval after restart", "passed": ok})
        print(("PASS" if ok else "FAIL") + " vector retrieval after restart")
    finally:
        asyncio.run(cleanup(a.email))
    failed = [r for r in results if not r["passed"]]
    print(f"Storage recovery checks: {len(results)}; failures={len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
