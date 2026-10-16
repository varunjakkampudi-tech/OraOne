"""Exercise every documented safe (GET/HEAD) API route against a live server."""

from __future__ import annotations

import argparse
import sys
import time
from urllib.parse import urljoin

import requests


def _probe_path(path: str) -> str:
    replacements = {
        "user_id": "00000000-0000-0000-0000-000000000000",
        "organization_id": "00000000-0000-0000-0000-000000000000",
        "agent_id": "00000000-0000-0000-0000-000000000000",
        "id": "00000000-0000-0000-0000-000000000000",
    }
    while "{" in path:
        start = path.index("{")
        end = path.index("}", start)
        name = path[start + 1 : end]
        path = path[:start] + replacements.get(name, "test") + path[end + 1 :]
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument(
        "--delay",
        type=float,
        default=0.6,
        help="Seconds between probes to respect shared rate limits",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/") + "/"
    openapi = requests.get(urljoin(base, "openapi.json"), timeout=args.timeout)
    openapi.raise_for_status()
    paths = openapi.json().get("paths", {})
    probes = [
        (method.upper(), path)
        for path, operations in paths.items()
        for method in operations
        if method.lower() in {"get", "head"}
    ]
    if not probes:
        print("No safe API routes were found in OpenAPI", file=sys.stderr)
        return 1

    failures: list[str] = []
    counts: dict[int, int] = {}
    for method, path in sorted(probes):
        response = requests.request(
            method,
            urljoin(base, _probe_path(path).lstrip("/")),
            timeout=args.timeout,
        )
        if response.status_code == 429:
            wait = min(60, max(1, int(response.headers.get("Retry-After", "60"))))
            time.sleep(wait)
            response = requests.request(
                method,
                urljoin(base, _probe_path(path).lstrip("/")),
                timeout=args.timeout,
            )
        counts[response.status_code] = counts.get(response.status_code, 0) + 1
        if response.status_code >= 500 or response.status_code == 429:
            failures.append(f"{method} {path} -> {response.status_code}")
        time.sleep(max(0, args.delay))

    print(f"Probed {len(probes)} safe API routes; statuses={counts}")
    if failures:
        print("Unexpected server errors:", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
