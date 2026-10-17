"""Console-managed configuration overrides.

Values saved from the admin configuration console are stored encrypted in
``admin_config_overrides`` (one row per environment and key). They are applied
to ``os.environ`` in two places:

  * at process start, from :mod:`app.core.config` before any setting is read,
    so modules that read the environment at import time also see the values;
  * on an explicit reload from the console, which affects only the process
    that handled the request.

Only keys marked ``console_managed`` in :mod:`app.core.config_registry` can be
overridden. Keys that are removed from the table revert to the value they had
before the first override in this process.

This module never logs values. Loader errors are logged by exception type only.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional

from app.core.config_registry import BY_NAME, runtime_environment

log = logging.getLogger("app.config_overrides")

TABLE_NAME = "admin_config_overrides"

# Used to decide whether a stored change is newer than the running process.
PROCESS_STARTED_AT: datetime = datetime.now(timezone.utc)

# Value each managed key had before the console first overrode it.
_BASELINE: dict[str, Optional[str]] = {}
# Keys currently overridden by this process.
_APPLIED: set[str] = set()


def _sync_dsn(url: str) -> str:
    """psycopg2 needs a plain postgresql:// URL, not an asyncpg driver URL."""
    return re.sub(r"^postgresql(\+[a-z0-9_]+)?://", "postgresql://", url)


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "").strip()


def read_stored_overrides(
    url: str, environment: str, *, connect_timeout: int = 3
) -> dict[str, str]:
    """Return decrypted console values for one environment (synchronous).

    Rows for other environments are never read. Rows for keys that are not
    console-managed, or not applicable to the environment, are ignored.
    """
    import psycopg2  # local import keeps config import cheap when no DB is set

    from app.core.crypto import decrypt

    conn = psycopg2.connect(_sync_dsn(url), connect_timeout=connect_timeout)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT name, value_encrypted FROM {TABLE_NAME} "
                "WHERE environment = %s",
                (environment,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    values: dict[str, str] = {}
    for name, encrypted in rows:
        key = BY_NAME.get(name)
        if key is None or not key.console_managed:
            continue
        if environment not in key.environments:
            continue
        value = decrypt(encrypted)
        if value:
            values[name] = value
    return values


def apply_overrides(values: dict[str, str]) -> list[str]:
    """Expose console values through ``os.environ``. Returns the changed names."""
    changed: list[str] = []
    for key in BY_NAME.values():
        if not key.console_managed:
            continue
        name = key.name
        if name in values:
            if name not in _BASELINE:
                _BASELINE[name] = os.environ.get(name)
            if os.environ.get(name) != values[name]:
                os.environ[name] = values[name]
                changed.append(name)
            _APPLIED.add(name)
        elif name in _APPLIED:
            baseline = _BASELINE.get(name)
            if baseline is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = baseline
            _APPLIED.discard(name)
            changed.append(name)
    return changed


def apply_stored_overrides_at_startup() -> list[str]:
    """Load and apply stored overrides for this process's environment.

    Does nothing without ``DATABASE_URL``. A missing table (before the
    migration has run) or an unreachable database leaves the environment as
    it is, so the application still starts.
    """
    url = database_url()
    if not url:
        return []
    environment = runtime_environment(os.environ.get("ENVIRONMENT"))
    try:
        values = read_stored_overrides(url, environment)
    except Exception as exc:  # never block startup on the console store
        log.warning(
            "Console configuration overrides not loaded (%s).", type(exc).__name__
        )
        return []
    return apply_overrides(values)


async def reload_stored_overrides() -> list[str]:
    """Re-read stored overrides into this process. Raises on database errors."""
    url = database_url()
    if not url:
        return []
    environment = runtime_environment(os.environ.get("ENVIRONMENT"))
    values = await asyncio.to_thread(read_stored_overrides, url, environment)
    return apply_overrides(values)
