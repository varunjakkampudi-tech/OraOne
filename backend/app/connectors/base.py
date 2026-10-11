"""BaseConnector — the uniform interface every provider implements.

Design goals
------------
* **Modular**: the sync service only ever talks to this interface.
* **Testable offline**: a connector can run in *mock* mode (deterministic
  demo documents) so the whole platform — connect → sync → chunk →
  embed → RAG — works locally without real OAuth secrets.
* **Degrade, don't crash**: ``health()`` and ``sync()`` raise typed
  :class:`ConnectorError` subclasses that the API maps to clean HTTP
  responses; one provider failing never affects another.

Lifecycle (called by the sync service / API):

    connect()        # exchange code / validate creds → tokens + account
    refresh_token()  # mint a new access token from the refresh token
    health()         # cheap "are we still authorised?" probe
    sync()           # list + fetch remote docs as RemoteDocument[]
    search(query)    # provider-side search (optional; used by chat tools)
    list()           # browse remote resources (folders/channels/repos)
    disconnect()     # best-effort token revocation
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.database.models.integration import Integration


class ConnectorError(Exception):
    """Base class for connector failures (mapped to HTTP 502 by the API)."""


class NotConnectedError(ConnectorError):
    """Raised when an operation needs a valid token the integration lacks."""


class OAuthError(ConnectorError):
    """OAuth handshake / token-refresh failure."""


@dataclass
class RemoteDocument:
    """A single document fetched from a provider, ready for the KB pipeline.

    ``external_id`` is the provider's stable id (used to upsert/prune).
    Either ``data`` (raw bytes) or ``text`` must be set; the sync service
    encodes ``text`` to bytes when ``data`` is absent.
    """

    external_id: str
    name: str
    mime_type: Optional[str] = None
    modified_at: Optional[datetime] = None
    data: Optional[bytes] = None
    text: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_bytes(self) -> bytes:
        if self.data is not None:
            return self.data
        return (self.text or "").encode("utf-8")

    def content_hash(self) -> str:
        """Stable hash of the content — lets the sync skip unchanged files."""
        return hashlib.sha256(self.as_bytes()).hexdigest()

    @property
    def filename(self) -> str:
        """A safe filename with an extension the KB chunker understands."""
        name = self.name or self.external_id
        if "." in name.split("/")[-1]:
            return name
        # Synthesize an extension from the mime type so extract_text routes
        # it to the right parser.
        ext = {
            "application/pdf": "pdf",
            "text/plain": "txt",
            "text/markdown": "md",
            "text/csv": "csv",
            "text/html": "txt",
        }.get((self.mime_type or "").lower(), "txt")
        return f"{name}.{ext}"


@dataclass
class ConnectResult:
    """Outcome of :meth:`BaseConnector.connect`."""

    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    external_account: Optional[str] = None
    config: dict[str, Any] = field(default_factory=dict)
    # When set, the API redirects the browser here to begin an OAuth flow
    # instead of completing the connection inline.
    authorize_url: Optional[str] = None


class BaseConnector:
    """Provider-agnostic base. Subclasses override the provider specifics.

    The default implementation runs in **mock** mode: it returns a small
    set of deterministic demo documents so the end-to-end pipeline is
    exercisable without real credentials. Real connectors override
    :meth:`sync` (and usually :meth:`connect` / :meth:`refresh_token`).
    """

    #: provider key, e.g. "google_drive" — set by subclass / registry.
    provider: str = "base"

    def __init__(self, integration: "Optional[Integration]" = None) -> None:
        self.integration = integration

    # ── auth ──
    def connect(self, *, code: Optional[str] = None, **kwargs: Any) -> ConnectResult:
        """Validate credentials / complete OAuth. Mock mode: instant connect."""
        return ConnectResult(
            access_token="mock-access-token",
            refresh_token="mock-refresh-token",
            external_account="demo@oraone.local",
            config={"mock": True},
        )

    def refresh_token(self) -> ConnectResult:
        """Refresh the access token. Mock mode: no-op success."""
        return ConnectResult(access_token="mock-access-token")

    def disconnect(self) -> None:
        """Best-effort token revocation. Mock mode: nothing to do."""
        return None

    # ── data ──
    def health(self) -> bool:
        """Return True if the integration looks authorised/usable."""
        return True

    def sync(self) -> list[RemoteDocument]:
        """Return the current set of remote documents for this integration."""
        return self._mock_documents()

    def search(self, query: str, *, limit: int = 5) -> list[RemoteDocument]:
        """Provider-side search (optional). Default: filter mock docs."""
        q = (query or "").lower()
        return [d for d in self._mock_documents() if q in (d.text or "").lower()][:limit]

    def list(self) -> list[dict[str, Any]]:
        """Browse remote containers (folders/channels/repos). Optional."""
        return []

    def browse(
        self,
        *,
        parent_id: Optional[str] = None,
        query: Optional[str] = None,
        recent: bool = False,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Return folders + files for the file-picker UI.

        Default implementation returns a deterministic demo tree so the
        selection UI is exercisable in mock mode.
        """
        return self._mock_browse(parent_id=parent_id, query=query, recent=recent)

    # ── helpers ──
    def _mock_browse(
        self,
        *,
        parent_id: Optional[str] = None,
        query: Optional[str] = None,
        recent: bool = False,
    ) -> dict[str, Any]:
        modified = datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()

        def folder(fid: str, name: str) -> dict[str, Any]:
            return {
                "external_id": fid, "name": name, "mime_type": "folder",
                "is_folder": True, "modified_at": modified, "size": None,
                "path": name,
            }

        def file(fid: str, name: str, mime: str, size: int) -> dict[str, Any]:
            return {
                "external_id": fid, "name": name, "mime_type": mime,
                "is_folder": False, "modified_at": modified, "size": size,
                "path": name,
            }

        recent_files = [
            file("mock-file-handbook", "Employee Handbook.pdf", "application/pdf", 248000),
            file("mock-file-leave", "Leave Policy.docx",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 38000),
            file("mock-file-arch", "Architecture.pdf", "application/pdf", 512000),
            file("mock-file-sprint", "Sprint Notes.docx",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 21000),
            file("mock-file-roadmap", "Roadmap.pdf", "application/pdf", 410000),
        ]
        top_folders = [
            folder("mock-folder-hr", "HR"),
            folder("mock-folder-eng", "Engineering"),
            folder("mock-folder-fin", "Finance"),
            folder("mock-folder-prod", "Product"),
            folder("mock-folder-sales", "Sales"),
        ]

        if recent:
            return {"parent_id": None, "items": recent_files}
        if query:
            ql = query.lower()
            pool = top_folders + recent_files
            return {"parent_id": None, "items": [i for i in pool if ql in i["name"].lower()]}
        if parent_id:  # inside a folder → a couple of demo files
            return {"parent_id": parent_id, "items": recent_files[:2]}
        return {"parent_id": None, "items": top_folders + recent_files}

    # ── helpers ──
    def _mock_documents(self) -> list[RemoteDocument]:
        """Deterministic demo corpus, namespaced per provider.

        Real connectors ignore this; it exists so local dev / the Phase 10
        audit can drive the full pipeline with zero external dependencies.
        The ``modified_at`` is a *stable* timestamp so a second sync of
        unchanged content is correctly skipped (idempotent re-sync).
        """
        modified = datetime(2024, 1, 1, tzinfo=timezone.utc)
        label = self.provider.replace("_", " ").title()
        return [
            RemoteDocument(
                external_id=f"{self.provider}-doc-1",
                name=f"{label} — Company Leave Policy",
                mime_type="text/markdown",
                modified_at=modified,
                text=(
                    f"# {label}: Leave Policy\n\n"
                    "Employees accrue 20 days of paid annual leave per year. "
                    "Leave requests must be submitted at least 5 working days "
                    "in advance through the HR portal and approved by a manager. "
                    "Unused leave carries over up to a maximum of 10 days."
                ),
                metadata={"folder": f"{label}/HR"},
            ),
            RemoteDocument(
                external_id=f"{self.provider}-doc-2",
                name=f"{label} — Expense Reimbursement",
                mime_type="text/markdown",
                modified_at=modified,
                text=(
                    f"# {label}: Expense Reimbursement\n\n"
                    "Submit expense reports within 30 days using the finance "
                    "portal. Receipts are required for any expense over $25. "
                    "Reimbursements are paid within two pay cycles after "
                    "manager approval."
                ),
                metadata={"folder": f"{label}/Finance"},
            ),
        ]
