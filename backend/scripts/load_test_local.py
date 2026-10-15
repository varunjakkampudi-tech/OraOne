"""Bounded local load/soak probe: latency percentiles and 5xx rate per endpoint.

Creates one synthetic workspace, then drives concurrent GETs against health,
public widget config and authenticated list endpoints. 429s are counted as
rate-limit enforcement, not errors. Loopback development only.
    python scripts/load_test_local.py --duration 60 --concurrency 40
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_product_local import cleanup, validate  # noqa: E402
from scripts.verify_security_local import Actor  # noqa: E402


async def worker(client, targets, stop, stats):
    i = 0
    while time.monotonic() < stop:
        name, path, headers = targets[i % len(targets)]
        i += 1
        t0 = time.perf_counter()
        try:
            r = await client.get(path, headers=headers)
            code = r.status_code
        except httpx.HTTPError:
            code = 0
        stats[name].append(((time.perf_counter() - t0) * 1000, code))


def pct(values, p):
    values = sorted(values)
    return (
        round(values[min(len(values) - 1, int(len(values) * p))], 1) if values else None
    )


async def drive(base, targets, duration, concurrency):
    stats = defaultdict(list)
    stop = time.monotonic() + duration
    limits = httpx.Limits(max_connections=concurrency)
    async with httpx.AsyncClient(base_url=base, timeout=30, limits=limits) as client:
        await asyncio.gather(
            *(worker(client, targets, stop, stats) for _ in range(concurrency))
        )
    report = {}
    for name, rows in stats.items():
        lat = [ms for ms, _ in rows]
        codes = defaultdict(int)
        for _, c in rows:
            codes[c] += 1
        report[name] = {
            "requests": len(rows),
            "rps": round(len(rows) / duration, 1),
            "p50_ms": pct(lat, 0.50),
            "p95_ms": pct(lat, 0.95),
            "p99_ms": pct(lat, 0.99),
            "mean_ms": round(statistics.fmean(lat), 1),
            "status": dict(codes),
            "errors_5xx_or_network": sum(
                v for k, v in codes.items() if k == 0 or k >= 500
            ),
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--concurrency", type=int, default=40)
    parser.add_argument("--label", default="load")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    validate(base)
    a = Actor(base, "load")
    try:
        a.signup()
        project = a.req("POST", "/api/projects", (201,), json={"name": "Load project"})
        auth = {
            "Authorization": a.s.headers["Authorization"],
            "X-Project-Id": project["id"],
        }
        targets = [
            ("health", "/api/health", {}),
            ("ready", "/api/health/ready", {}),
            ("agents_list", "/api/agents", auth),
            ("leads_list", "/api/leads", auth),
            ("analytics_overview", "/api/analytics/overview", auth),
        ]
        report = asyncio.run(drive(base, targets, args.duration, args.concurrency))
    finally:
        asyncio.run(cleanup(a.email))
    out = ROOT / "output" / f"local-{args.label}-test.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "duration_s": args.duration,
                "concurrency": args.concurrency,
                "endpoints": report,
            },
            indent=2,
        )
    )
    for name, r in report.items():
        print(name, json.dumps(r))
    errors = sum(r["errors_5xx_or_network"] for r in report.values())
    print(f"Total 5xx/network errors: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
