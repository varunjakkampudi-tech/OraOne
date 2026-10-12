"""Create an encrypted PostgreSQL backup for an external weekly scheduler.

The script intentionally writes outside the checkout and requires an explicit
GPG passphrase file. It does not upload or delete remote backups; operators
should place the output on separately managed encrypted storage.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def main() -> int:
    backup_dir = Path(required("ORAONE_BACKUP_DIR")).resolve()
    passphrase_file = Path(required("ORAONE_BACKUP_PASSPHRASE_FILE")).resolve()
    if not passphrase_file.is_file():
        raise SystemExit("ORAONE_BACKUP_PASSPHRASE_FILE must point to a file")
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = backup_dir / f"oraone_{timestamp}.dump.gpg"
    env = {**os.environ, "PGPASSWORD": required("DB_PASSWORD")}
    database = required("DB_NAME")
    connection = [
        "--host",
        required("DB_HOST"),
        "--port",
        required("DB_PORT"),
        "--username",
        required("DB_USER"),
    ]

    dump = subprocess.Popen(
        [
            "pg_dump",
            *connection,
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file=-",
            database,
        ],
        env=env,
        stdout=subprocess.PIPE,
    )
    encrypt = subprocess.run(
        [
            "gpg",
            "--batch",
            "--yes",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "--pinentry-mode",
            "loopback",
            "--passphrase-file",
            str(passphrase_file),
            "--output",
            str(output),
        ],
        stdin=dump.stdout,
        check=False,
    )
    dump.stdout.close()  # type: ignore[union-attr]
    dump_rc = dump.wait()
    if dump_rc != 0 or encrypt.returncode != 0:
        output.unlink(missing_ok=True)
        return 1
    output.chmod(0o600)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
