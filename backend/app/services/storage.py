"""Local file storage for uploaded documents and brand assets.

Uploads are written under ``UPLOAD_DIR`` (default ``/tmp/oraone-uploads``).
The directory must be owned by the application user and must not be a
symbolic link. Stored keys use the ``local://`` prefix so that the database
column always states where the bytes live.

Object storage in the cloud is intentionally not supported in this build:
OraOne runs on the platform's own infrastructure, so files stay on the
configured volume.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import BinaryIO

log = logging.getLogger("app.storage")

LOCAL_PREFIX = "local://"
_CHUNK_SIZE = 64 * 1024


def _local_root() -> Path:
    """Return the upload root, creating it with owner-only permissions."""
    root = Path(os.environ.get("UPLOAD_DIR", "/tmp/oraone-uploads"))
    if root.is_symlink():
        raise RuntimeError("Local upload root must not be a symbolic link.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == "posix":
        if root.stat().st_uid != os.getuid():
            raise RuntimeError(
                "Local upload root must be owned by the application user."
            )
        root.chmod(0o700)
    return root


def build_key(*, organization_id: str, knowledge_base_id: str, filename: str) -> str:
    """Build the relative storage key for a new document.

    Layout: ``org/<org-id>/kb/<kb-id>/<uuid>__<safe-filename>``. The UUID keeps
    re-uploads of the same file unique; the sanitized filename keeps it readable.
    """
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)[:180]
    return f"org/{organization_id}/kb/{knowledge_base_id}/{uuid.uuid4()}__{safe}"


def put_object(*, key: str, body: BinaryIO, content_type: str | None) -> str:
    """Write ``body`` under ``key`` and return the ``local://`` storage key.

    ``content_type`` is accepted for API symmetry; local files are served
    by the backend, which sets the response type itself.
    """
    del content_type  # not persisted for local files
    dest = _local_root() / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as handle:
        while True:
            chunk = body.read(_CHUNK_SIZE)
            if not chunk:
                break
            handle.write(chunk)
    log.info("local_upload ok path=%s", dest)
    return f"{LOCAL_PREFIX}{key}"


def is_local_key(storage_key: str) -> bool:
    """True when ``storage_key`` points at a file in the local upload root."""
    return storage_key.startswith(LOCAL_PREFIX)


def local_path(storage_key: str) -> Path:
    """Return the absolute filesystem path for a ``local://`` storage key."""
    relative = storage_key.removeprefix(LOCAL_PREFIX)
    return _local_root() / relative
