"""One-time bootstrap — `CREATE DATABASE oraone` on the RDS instance.

`CREATE DATABASE` cannot run inside a transaction, so we connect to the
default `postgres` maintenance database with autocommit isolation and
create our target DB if it doesn't already exist. Safe to re-run.

Usage:

    cd backend
    source .venv/bin/activate
    python scripts/bootstrap_db.py        # then: alembic upgrade head
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Load backend/.env so DB_* / DATABASE_URL are available.
ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass


def main() -> int:
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    target_db = os.environ.get("DB_NAME", "oraone")

    if not all([host, user, password]):
        print("ERROR: DB_HOST / DB_USER / DB_PASSWORD must be set in backend/.env")
        return 2

    # Connect to the default 'postgres' maintenance DB.
    conn = psycopg2.connect(
        host=host, port=port, user=user, password=password,
        dbname="postgres", connect_timeout=10,
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        if cur.fetchone():
            print(f"ok: database '{target_db}' already exists.")
            conn.close()
            return 0

        print(f"creating database '{target_db}' ...")
        # Identifier interpolation — target_db comes from env, validate it.
        if not target_db.replace("_", "").isalnum():
            print(f"ERROR: refusing to create DB with unsafe name: {target_db!r}")
            conn.close()
            return 3
        cur.execute(
            f'CREATE DATABASE "{target_db}" '
            f"WITH ENCODING = 'UTF8' TEMPLATE = template0"
        )

    conn.close()
    print(f"ok: database '{target_db}' created. Now run: alembic upgrade head")
    return 0


if __name__ == "__main__":
    sys.exit(main())
