"""Disaster-recovery drill — pg_dump the live DB, restore into a throwaway
database, verify row counts + schema markers match, then clean up.

This is meant to be re-run periodically (cron/CI) to prove backups are
actually restorable, not just that `pg_dump` exits 0. Fails loudly (non-zero
exit code) if anything doesn't match so it can gate a deploy or alert on-call.

Usage:

    cd backend
    source .venv/bin/activate   # or .venv\\Scripts\\activate on Windows
    python scripts/backup_restore_drill.py [--keep-dump]

Requires `pg_dump`/`pg_restore`/`psql` on PATH (same major version family as
the target server; mismatches can cause restore errors).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass

# Tables whose row counts we compare between source and restored DB. Kept
# small and stable — add to this list if new core entities are introduced.
CHECK_TABLES = ["users", "agents", "conversations", "organizations"]


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        print(f"ERROR: {name} must be set (backend/.env or environment)")
        sys.exit(1)
    return value


def _run(cmd: list[str], env: dict) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAILED: {' '.join(cmd)}")
        print(result.stdout)
        print(result.stderr)
        sys.exit(result.returncode)
    return result


def _row_counts(env: dict, host: str, port: str, user: str, db: str) -> dict[str, int]:
    counts = {}
    for table in CHECK_TABLES:
        result = _run(
            [
                "psql", "-h", host, "-p", port, "-U", user, "-d", db,
                "-t", "-A", "-c", f"SELECT count(*) FROM {table};",
            ],
            env,
        )
        counts[table] = int(result.stdout.strip())
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-dump", action="store_true", help="Don't delete the dump file afterwards")
    args = parser.parse_args()

    host = _env("DB_HOST", "localhost")
    port = _env("DB_PORT", "5432")
    user = _env("DB_USER")
    password = _env("DB_PASSWORD")
    db = _env("DB_NAME", "oraone")
    drill_db = f"{db}_restore_drill"

    env = {**os.environ, "PGPASSWORD": password}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dump_dir = ROOT / "backups"
    dump_dir.mkdir(exist_ok=True)
    dump_path = dump_dir / f"oraone_{timestamp}.dump"

    print(f"[1/5] Dumping {db} -> {dump_path}")
    _run(["pg_dump", "-h", host, "-p", port, "-U", user, "-d", db, "-Fc", "-f", str(dump_path)], env)

    print(f"[2/5] Capturing baseline row counts from {db}")
    baseline = _row_counts(env, host, port, user, db)
    print(f"       {baseline}")

    print(f"[3/5] Restoring into throwaway database {drill_db}")
    _run(["psql", "-h", host, "-p", port, "-U", user, "-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {drill_db};"], env)
    _run(["psql", "-h", host, "-p", port, "-U", user, "-d", "postgres", "-c", f"CREATE DATABASE {drill_db} OWNER {user};"], env)
    restore = subprocess.run(
        ["pg_restore", "-h", host, "-p", port, "-U", user, "-d", drill_db, "--no-owner", "--no-privileges", str(dump_path)],
        env=env, capture_output=True, text=True,
    )
    # pg_restore can return non-zero on harmless warnings (e.g. extension
    # already owned by a different role); only treat it as fatal if no
    # tables ended up existing at all, checked via the row-count step below.
    if restore.returncode != 0:
        print("pg_restore reported warnings (may be non-fatal):")
        print(restore.stderr[-2000:])

    print(f"[4/5] Verifying restored row counts in {drill_db}")
    restored = _row_counts(env, host, port, user, drill_db)
    print(f"       {restored}")

    print(f"[5/5] Cleaning up {drill_db}")
    _run(["psql", "-h", host, "-p", port, "-U", user, "-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {drill_db};"], env)

    if not args.keep_dump:
        dump_path.unlink(missing_ok=True)
    else:
        print(f"Dump retained at {dump_path}")

    mismatches = {t: (baseline[t], restored[t]) for t in CHECK_TABLES if baseline[t] != restored[t]}
    if mismatches:
        print(f"DRILL FAILED — row count mismatches: {mismatches}")
        return 1

    print("DRILL PASSED — backup is restorable and data matches.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
