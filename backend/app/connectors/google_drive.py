"""Google Drive connector (Phase 10 — first real integration).

Syncs documents from a user's Google Drive into a Knowledge Base so they
become searchable in chat. Supports:

* Real mode — OAuth2 + Drive v3 REST (via ``httpx``). Lists files in the
  selected folder, exports Google Docs to text, downloads PDFs/TXT/MD/CSV.
* Mock mode — deterministic demo documents (no secrets needed) so the
  platform is testable locally and in CI.

Mode is chosen by ``integration.connection_type``: ``oauth`` → real,
``mock`` → demo corpus. Real mode also auto-falls back to mock if no
usable access token is present, so the UI never hard-fails in dev.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from app.connectors.base import (
    BaseConnector,
    ConnectorError,
    NotConnectedError,
    RemoteDocument,
)
from app.core import crypto
from app.database.models.integration import ConnectionType
from app.services import oauth_service

log = logging.getLogger("app.connectors.google_drive")

DRIVE_API = "https://www.googleapis.com/drive/v3"

_FOLDER_MIME = "application/vnd.google-apps.folder"

# Google Docs editor MIME types we export to plain text/markdown.
_GOOGLE_EXPORT = {
    "application/vnd.google-apps.document": ("text/plain", "txt"),
    "application/vnd.google-apps.presentation": ("text/plain", "txt"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", "csv"),
}
# Binary/text MIME types we download directly and can chunk.
_DOWNLOADABLE = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class GoogleDriveConnector(BaseConnector):
    provider = "google_drive"

    # ── auth ──
    def connect(self, *, code: Optional[str] = None, **kwargs: Any):
        return oauth_service.complete_connect("google_drive", code=code, **kwargs)

    def refresh_token(self):
        if self.integration is None:
            raise NotConnectedError("No integration bound to connector.")
        refresh = crypto.decrypt(self.integration.refresh_token)
        if not refresh:
            raise NotConnectedError("No refresh token available.")
        return oauth_service.refresh("google_drive", refresh_token=refresh)

    def disconnect(self) -> None:
        token = self._access_token()
        if token:
            try:
                httpx.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": token},
                    timeout=10,
                )
            except httpx.HTTPError as e:  # best effort
                log.info("google_drive revoke failed (non-fatal): %s", e)

    # ── data ──
    def health(self) -> bool:
        if self._is_mock():
            return True
        token = self._access_token()
        if not token:
            return False
        try:
            r = httpx.get(
                f"{DRIVE_API}/about",
                params={"fields": "user(emailAddress)"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    def sync(self) -> list[RemoteDocument]:
        if self._is_mock():
            return self._mock_documents()

        token = self._access_token()
        if not token:
            log.warning("google_drive: no access token; falling back to mock corpus.")
            return self._mock_documents()

        config = self.integration.config or {} if self.integration else {}
        selection = config.get("selection") or {}
        mode = selection.get("mode", "full")
        try:
            # Selective sync: only the folders/files the user picked.
            if mode in ("folder", "quick", "selection") and (
                selection.get("folders") or selection.get("files")
            ):
                return self._fetch_selection(token, selection)
            # Full sync (optionally scoped to a single legacy folder_id).
            folder_id = config.get("folder_id")
            return self._fetch_drive(token, folder_id, options=selection.get("options"))
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code in (401, 403):
                raise NotConnectedError(
                    "Google Drive authorization expired — reconnect required."
                ) from e
            raise ConnectorError(f"Google Drive sync failed: {e}") from e
        except httpx.HTTPError as e:
            raise ConnectorError(f"Google Drive request failed: {e}") from e

    def browse(
        self,
        *,
        parent_id: Optional[str] = None,
        query: Optional[str] = None,
        recent: bool = False,
        page_size: int = 100,
    ) -> dict[str, Any]:
        if self._is_mock():
            return self._mock_browse(parent_id=parent_id, query=query, recent=recent)
        token = self._access_token()
        if not token:
            return self._mock_browse(parent_id=parent_id, query=query, recent=recent)
        try:
            return self._browse_drive(
                token,
                parent_id=parent_id,
                query=query,
                recent=recent,
                page_size=page_size,
            )
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code in (401, 403):
                raise NotConnectedError(
                    "Google Drive authorization expired — reconnect required."
                ) from e
            raise ConnectorError(f"Google Drive browse failed: {e}") from e
        except httpx.HTTPError as e:
            raise ConnectorError(f"Google Drive browse request failed: {e}") from e

    # ── internals ──
    def _is_mock(self) -> bool:
        return (
            self.integration is not None
            and self.integration.connection_type == ConnectionType.mock
        )

    def _access_token(self) -> Optional[str]:
        if self.integration is None:
            return None
        return crypto.decrypt(self.integration.access_token)

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    # ── listing ──
    _LIST_FIELDS = (
        "nextPageToken, files(id,name,mimeType,modifiedTime,size,"
        "md5Checksum,parents,ownedByMe)"
    )

    def _drive_list(
        self,
        token: str,
        *,
        q: str,
        order_by: Optional[str] = None,
        page_size: int = 100,
        all_pages: bool = True,
        max_items: int = 5000,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token: Optional[str] = None
        while True:
            params: dict[str, str] = {
                "q": q,
                "fields": self._LIST_FIELDS,
                "pageSize": str(min(page_size, 1000)),
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if order_by:
                params["orderBy"] = order_by
            if page_token:
                params["pageToken"] = page_token
            r = httpx.get(
                f"{DRIVE_API}/files",
                params=params,
                headers=self._headers(token),
                timeout=30,
            )
            r.raise_for_status()
            body = r.json()
            items.extend(body.get("files", []))
            page_token = body.get("nextPageToken")
            if not page_token or not all_pages or len(items) >= max_items:
                break
        return items

    def _browse_drive(
        self,
        token: str,
        *,
        parent_id: Optional[str],
        query: Optional[str],
        recent: bool,
        page_size: int,
    ) -> dict[str, Any]:
        if recent:
            q = "trashed = false and mimeType != 'application/vnd.google-apps.folder'"
            order_by = "modifiedTime desc"
        elif query:
            safe = query.replace("\\", "\\\\").replace("'", "\\'")
            q = f"trashed = false and name contains '{safe}'"
            order_by = "folder,name"
        else:
            parent = parent_id or "root"
            q = f"'{parent}' in parents and trashed = false"
            order_by = "folder,name"
        files = self._drive_list(
            token, q=q, order_by=order_by, page_size=page_size, all_pages=False
        )
        items = [
            {
                "external_id": f["id"],
                "name": f.get("name", f["id"]),
                "mime_type": f.get("mimeType"),
                "is_folder": f.get("mimeType") == _FOLDER_MIME,
                "modified_at": f.get("modifiedTime"),
                "size": int(f["size"]) if f.get("size") else None,
            }
            for f in files
        ]
        return {"parent_id": parent_id, "items": items}

    # ── sync resolution ──
    def _fetch_drive(
        self, token: str, folder_id: Optional[str], options: Optional[dict] = None
    ) -> list[RemoteDocument]:
        q_parts = ["trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        files = self._drive_list(token, q=" and ".join(q_parts), page_size=100)
        docs: list[RemoteDocument] = []
        for f in files:
            if f.get("mimeType") == _FOLDER_MIME:
                continue
            if not _passes_options(f, options):
                continue
            doc = self._to_remote(token, f, path=f.get("name", f.get("id", "")))
            if doc is not None:
                docs.append(doc)
        return docs

    def _fetch_selection(self, token: str, selection: dict) -> list[RemoteDocument]:
        options = selection.get("options")
        out: dict[str, RemoteDocument] = {}

        for folder in selection.get("folders") or []:
            fid, fname = _ext_id(folder)
            if fid:
                self._walk_folder(
                    token, fid, fname or "", options, out, depth=0, visited=set()
                )

        for fileref in selection.get("files") or []:
            fid, _ = _ext_id(fileref)
            if not fid or fid in out:
                continue
            meta = self._file_meta(token, fid)
            if meta is None or meta.get("mimeType") == _FOLDER_MIME:
                continue
            if not _passes_options(meta, options):
                continue
            doc = self._to_remote(token, meta, path=meta.get("name", fid))
            if doc is not None:
                out[fid] = doc

        return list(out.values())

    def _walk_folder(
        self,
        token: str,
        folder_id: str,
        base_path: str,
        options: Optional[dict],
        out: dict[str, RemoteDocument],
        *,
        depth: int,
        visited: set,
    ) -> None:
        if depth > 12 or folder_id in visited:
            return
        visited.add(folder_id)
        children = self._drive_list(
            token, q=f"'{folder_id}' in parents and trashed = false", page_size=100
        )
        for f in children:
            name = f.get("name", f.get("id", ""))
            path = f"{base_path}/{name}" if base_path else name
            if f.get("mimeType") == _FOLDER_MIME:
                self._walk_folder(
                    token, f["id"], path, options, out, depth=depth + 1, visited=visited
                )
                continue
            if f["id"] in out or not _passes_options(f, options):
                continue
            doc = self._to_remote(token, f, path=path)
            if doc is not None:
                out[f["id"]] = doc

    def _file_meta(self, token: str, file_id: str) -> Optional[dict]:
        r = httpx.get(
            f"{DRIVE_API}/files/{file_id}",
            params={
                "fields": "id,name,mimeType,modifiedTime,size,md5Checksum,parents,ownedByMe",
                "supportsAllDrives": "true",
            },
            headers=self._headers(token),
            timeout=30,
        )
        if r.status_code != 200:
            log.info("drive file_meta skip id=%s status=%s", file_id, r.status_code)
            return None
        return r.json()

    def _to_remote(self, token: str, f: dict, *, path: str) -> Optional[RemoteDocument]:
        mime = f.get("mimeType", "")
        if mime in _GOOGLE_EXPORT:
            export_mime, _ext = _GOOGLE_EXPORT[mime]
            data = self._export(token, f["id"], export_mime)
            effective_mime = export_mime
        elif mime in _DOWNLOADABLE:
            data = self._download(token, f["id"])
            effective_mime = mime
        else:
            return None  # unsupported (image/video/binary)
        if data is None:
            return None
        return RemoteDocument(
            external_id=f["id"],
            name=f.get("name", f["id"]),
            mime_type=effective_mime,
            modified_at=_parse_ts(f.get("modifiedTime")),
            data=data,
            metadata={
                "drive_mime": mime,
                "size": f.get("size"),
                "path": path,
                "md5": f.get("md5Checksum"),
            },
        )

    def _export(self, token: str, file_id: str, export_mime: str) -> Optional[bytes]:
        r = httpx.get(
            f"{DRIVE_API}/files/{file_id}/export",
            params={"mimeType": export_mime},
            headers=self._headers(token),
            timeout=60,
        )
        if r.status_code != 200:
            log.info("drive export skip id=%s status=%s", file_id, r.status_code)
            return None
        return r.content

    def _download(self, token: str, file_id: str) -> Optional[bytes]:
        r = httpx.get(
            f"{DRIVE_API}/files/{file_id}",
            params={"alt": "media", "supportsAllDrives": "true"},
            headers=self._headers(token),
            timeout=60,
        )
        if r.status_code != 200:
            log.info("drive download skip id=%s status=%s", file_id, r.status_code)
            return None
        return r.content


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _ext_id(ref: Any) -> tuple[Optional[str], Optional[str]]:
    """Normalize a folder/file ref (str id or {id|external_id, name, path})."""
    if isinstance(ref, str):
        return ref, None
    if isinstance(ref, dict):
        fid = ref.get("external_id") or ref.get("id")
        name = ref.get("path") or ref.get("name")
        return fid, name
    return None, None


# Map a Drive MIME type to a coarse "file type" token used by user filters.
def _mime_token(mime: str) -> str:
    mime = (mime or "").lower()
    if mime == "application/pdf":
        return "pdf"
    if mime == "application/vnd.google-apps.document":
        return "gdoc"
    if mime == "application/vnd.google-apps.spreadsheet":
        return "gsheet"
    if mime == "application/vnd.google-apps.presentation":
        return "gslides"
    if mime.endswith("wordprocessingml.document"):
        return "docx"
    if mime in ("text/markdown",):
        return "md"
    if mime in ("text/csv",):
        return "csv"
    if mime.startswith("text/"):
        return "txt"
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    return "other"


def _passes_options(f: dict, options: Optional[dict]) -> bool:
    """Apply the user's advanced sync filters to a Drive file dict."""
    if not options:
        return True
    mime = f.get("mimeType", "")
    token = _mime_token(mime)

    if options.get("ignore_images") and token == "image":
        return False
    if options.get("ignore_videos") and token == "video":
        return False

    file_types = options.get("file_types")
    if file_types and token not in set(file_types):
        return False

    max_mb = options.get("max_size_mb")
    if max_mb:
        try:
            size = int(f.get("size") or 0)
            if size > int(max_mb) * 1024 * 1024:
                return False
        except (TypeError, ValueError):
            pass

    if options.get("ignore_shared") and f.get("ownedByMe") is False:
        return False

    recent_days = options.get("recent_days")
    if recent_days:
        modified = _parse_ts(f.get("modifiedTime"))
        if modified is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=int(recent_days))
            if modified < cutoff:
                return False

    return True
