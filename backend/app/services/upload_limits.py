"""Upload size and archive safety checks shared by file-upload routes.

Three layers, all enforced before a file is stored or parsed:

1. ``UploadSizeLimitMiddleware`` (app/middleware) rejects a request whose
   declared Content-Length exceeds the route cap, before any body is read.
2. ``read_capped`` reads the upload in fixed-size chunks and stops at the cap,
   so an undeclared or chunked body is never buffered whole.
3. ``assert_office_package_safe`` decompresses an OOXML package (.docx, .xlsx,
   .pptx are ZIP archives) under a total-size cap, so a small archive that
   expands into gigabytes (zip bomb) is refused.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import PurePath

from fastapi import HTTPException, UploadFile, status

READ_CHUNK_BYTES = 64 * 1024
OFFICE_EXTENSIONS = frozenset({".docx", ".xlsx", ".pptx"})
MAX_OFFICE_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_OFFICE_MEMBER_RATIO = 100


async def read_capped(
    file: UploadFile, max_bytes: int, *, detail: str | None = None
) -> bytes:
    """Read ``file`` in chunks and raise 413 as soon as it exceeds ``max_bytes``."""
    buf = io.BytesIO()
    total = 0
    while True:
        chunk = await file.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=detail or f"File exceeds {max_bytes} bytes.",
            )
        buf.write(chunk)
    return buf.getvalue()


def assert_office_package_safe(
    filename: str | None,
    body: bytes,
    *,
    max_uncompressed: int = MAX_OFFICE_UNCOMPRESSED_BYTES,
    max_ratio: int = MAX_OFFICE_MEMBER_RATIO,
) -> None:
    """Refuse OOXML packages whose real decompressed size is too large.

    Sizes are measured by decompressing each member under a running cap, not by
    trusting the archive's declared sizes. Non-Office filenames are ignored.
    """
    if PurePath(filename or "").suffix.lower() not in OFFICE_EXTENSIONS:
        return
    try:
        archive = zipfile.ZipFile(io.BytesIO(body))
    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The file is not a valid Office document.",
        ) from exc

    total = 0
    with archive:
        for info in archive.infolist():
            member_total = 0
            with archive.open(info) as member:
                while True:
                    chunk = member.read(READ_CHUNK_BYTES)
                    if not chunk:
                        break
                    member_total += len(chunk)
                    total += len(chunk)
                    too_big = total > max_uncompressed
                    too_squashed = member_total > 1024 * 1024 and (
                        member_total > max_ratio * max(info.compress_size, 1)
                    )
                    if too_big or too_squashed:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="The Office document expands to too much data.",
                        )
