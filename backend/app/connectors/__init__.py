"""Connector framework (Phase 10).

Every external provider (Google Drive, Gmail, Slack, Notion, GitHub…)
implements the same :class:`BaseConnector` interface so the sync service,
API, and UI stay provider-agnostic. Adding a new integration = adding one
connector class + one registry entry.
"""
from app.connectors.base import (
    BaseConnector,
    ConnectorError,
    NotConnectedError,
    RemoteDocument,
)
from app.connectors.registry import (
    PROVIDER_CATALOG,
    ProviderSpec,
    get_connector,
    get_spec,
    list_specs,
)

__all__ = [
    "BaseConnector",
    "ConnectorError",
    "NotConnectedError",
    "RemoteDocument",
    "PROVIDER_CATALOG",
    "ProviderSpec",
    "get_connector",
    "get_spec",
    "list_specs",
]
