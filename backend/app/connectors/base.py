"""BaseConnector — the uniform interface every provider implements.

Design goals
------------
* **Modular**: the sync service only ever talks to this interface.
* **Testable offline**: isolated tests supply synthetic connector fixtures.
  Application code never supplies fake tokens, provider documents or folders.
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
from datetime import datetime
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
    """Connector interface. Missing implementations fail closed, never fabricate data."""

    provider: str = "base"

    def __init__(self, integration: "Optional[Integration]" = None) -> None:
        self.integration = integration

    def connect(self, *, code: Optional[str] = None, **kwargs: Any) -> ConnectResult:
        raise NotConnectedError(
            f"{self.provider} has no configured connector implementation."
        )

    def refresh_token(self) -> ConnectResult:
        raise NotConnectedError(
            f"{self.provider} cannot refresh an unconfigured connection."
        )

    def disconnect(self) -> None:
        """No credentials exist in an unimplemented connector."""
        return None

    def health(self) -> bool:
        return False

    def sync(self) -> list[RemoteDocument]:
        raise NotConnectedError(
            f"{self.provider} cannot sync without a real connector."
        )

    def search(self, query: str, *, limit: int = 5) -> list[RemoteDocument]:
        raise NotConnectedError(f"{self.provider} does not implement provider search.")

    def list(self) -> list[dict[str, Any]]:
        raise NotConnectedError(f"{self.provider} does not implement resource listing.")

    def browse(
        self,
        *,
        parent_id: Optional[str] = None,
        query: Optional[str] = None,
        recent: bool = False,
        page_size: int = 100,
    ) -> dict[str, Any]:
        raise NotConnectedError(
            f"{self.provider} cannot browse without a real connector."
        )
