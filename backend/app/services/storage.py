"""Object-storage service (Phase 6).

Abstracts S3 vs local-disk storage so the rest of the codebase doesn't
need to care which one is active. In production we expect S3 or any
S3-compatible store — MinIO, Cloudflare R2, Backblaze B2 — (``S3_BUCKET``
env var set, optionally ``S3_ENDPOINT_URL`` pointed at the non-AWS
endpoint); in dev / preview where none of that is wired up we fall back to
a local directory under ``UPLOAD_DIR`` (default ``/tmp/oraone-uploads``)
so the upload endpoint still works end-to-end.

The function ``put_object`` returns an ``s3_key``-style string the
caller persists into ``documents.s3_key``. For S3-compatible storage it's
just the key (no bucket prefix); for local mode it's ``local://<relative-path>``
so you can tell the modes apart at a glance in the DB.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

log = logging.getLogger("app.storage")


def _bucket() -> str | None:
    return os.environ.get("S3_BUCKET") or None


def _region() -> str:
    return os.environ.get("S3_REGION") or os.environ.get("AWS_REGION", "us-east-1")


def _endpoint_url() -> str | None:
    """Set to a MinIO/R2/B2 endpoint (e.g. ``http://minio:9000``) to use
    anything S3-API-compatible instead of real AWS S3. Unset = real AWS."""
    return os.environ.get("S3_ENDPOINT_URL") or None


def _local_root() -> Path:
    root = Path(os.environ.get("UPLOAD_DIR", "/tmp/oraone-uploads"))
    root.mkdir(parents=True, exist_ok=True)
    return root


_s3_client = None


def _client():
    global _s3_client
    if _s3_client is None:
        endpoint = _endpoint_url()
        kwargs: dict = {
            "config": Config(
                region_name=_region(),
                retries={"max_attempts": 3},
                # MinIO/R2 default to path-style addressing (bucket in the
                # URL path, not a subdomain) — real AWS S3 supports both.
                s3={"addressing_style": "path"} if endpoint else {},
            ),
        }
        if endpoint:
            kwargs["endpoint_url"] = endpoint
            kwargs["aws_access_key_id"] = os.environ.get("S3_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID")
            kwargs["aws_secret_access_key"] = os.environ.get("S3_SECRET_ACCESS_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY")
            log.info("object storage: S3-compatible endpoint (%s)", endpoint)
        else:
            log.info("object storage: AWS S3")
        _s3_client = boto3.client("s3", **kwargs)
    return _s3_client


def build_key(*, organization_id: str, knowledge_base_id: str, filename: str) -> str:
    """Compose the storage key for a freshly uploaded document.

    Path layout: ``org/<org-id>/kb/<kb-id>/<uuid>__<safe-filename>``.
    The leading UUID guarantees uniqueness even if the same file is
    re-uploaded; ``__<filename>`` preserves the original name for the UI.
    """
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)[:180]
    return f"org/{organization_id}/kb/{knowledge_base_id}/{uuid.uuid4()}__{safe}"


def _ensure_bucket(client, bucket: str) -> None:
    """Auto-create the bucket on first use — only meaningful for a fresh
    MinIO/local S3-compatible instance; real AWS S3 buckets are expected to
    already exist (this is a no-op there since head_bucket succeeds)."""
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        try:
            client.create_bucket(Bucket=bucket)
            log.info("object storage: created missing bucket %s", bucket)
        except (BotoCoreError, ClientError) as e:
            log.warning("object storage: could not auto-create bucket %s: %s", bucket, e)


def put_object(*, key: str, body: BinaryIO, content_type: str | None) -> str:
    """Upload to S3 (or a configured S3-compatible endpoint) if configured,
    else write to ``UPLOAD_DIR``.

    Returns the ``s3_key`` string to persist in ``documents.s3_key``.
    """
    bucket = _bucket()
    if bucket:
        client = _client()
        if _endpoint_url():
            _ensure_bucket(client, bucket)
        try:
            client.upload_fileobj(
                Fileobj=body,
                Bucket=bucket,
                Key=key,
                ExtraArgs={"ContentType": content_type} if content_type else None,
            )
            log.info("s3_upload ok bucket=%s key=%s", bucket, key)
            return key
        except (BotoCoreError, ClientError) as e:
            log.error("s3_upload_failed key=%s err=%s: %s", key, type(e).__name__, e)
            raise

    # Local fallback
    dest = _local_root() / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        while True:
            chunk = body.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
    log.info("local_upload ok path=%s", dest)
    return f"local://{key}"


def is_local_key(s3_key: str) -> bool:
    return s3_key.startswith("local://")


def presigned_url(key: str, *, expires: int = 3600) -> str | None:
    """Return a presigned GET URL for an S3 key, or None when S3 isn't configured."""
    bucket = _bucket()
    if not bucket:
        return None
    try:
        return _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires,
        )
    except (BotoCoreError, ClientError) as e:
        log.error("presign_failed key=%s err=%s: %s", key, type(e).__name__, e)
        return None


def get_object(key: str) -> tuple[bytes, str | None] | None:
    """Fetch an S3 object's bytes + content-type, or None when S3 isn't configured.

    Streaming the object back through our own backend keeps brand assets on a
    single same-origin URL, sidestepping S3 region/CORS/ORB issues that bite
    when the browser is redirected straight to a presigned S3 URL.
    """
    bucket = _bucket()
    if not bucket:
        return None
    try:
        obj = _client().get_object(Bucket=bucket, Key=key)
        return obj["Body"].read(), obj.get("ContentType")
    except (BotoCoreError, ClientError) as e:
        log.error("s3_get_failed key=%s err=%s: %s", key, type(e).__name__, e)
        return None


def local_path(s3_key: str) -> Path:
    """For ``local://`` keys, return the absolute filesystem path."""
    rel = s3_key.removeprefix("local://")
    return _local_root() / rel
