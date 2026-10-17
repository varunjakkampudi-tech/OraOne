"""Provider registry & catalog (Phase 10).

Single source of truth mapping a ``provider`` key to:

* its UI metadata (display name, category, auth type, icon, accent),
* whether it's wired for real OAuth yet (``available``), and
* the :class:`BaseConnector` subclass that implements it.

The API exposes :data:`PROVIDER_CATALOG` to render the integrations grid,
and the sync service uses :func:`get_connector` to instantiate the right
connector for a stored integration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Type

from app.connectors.base import BaseConnector
from app.connectors.google_drive import GoogleDriveConnector
from app.connectors.providers import (
    GenericWebhookConnector,
    GmailConnector,
    GoogleCalendarConnector,
    GoogleSheetsConnector,
    HubspotConnector,
    MakeConnector,
    NotionConnector,
    SalesforceConnector,
    SlackConnector,
    ZapierConnector,
)
from app.database.models.integration import IntegrationType

if TYPE_CHECKING:
    from app.database.models.integration import Integration


# Five integration categories from the spec.
CATEGORY_COMMUNICATION = "communication"
CATEGORY_DOCUMENTS = "documents"
CATEGORY_DOCUMENTATION = "documentation"
CATEGORY_DEVELOPMENT = "development"
CATEGORY_CRM = "crm"


@dataclass(frozen=True)
class ProviderSpec:
    provider: str
    name: str
    category: str
    type: IntegrationType
    connector_cls: Type[BaseConnector]
    auth: str = "oauth"  # oauth | api_key | webhook
    icon: str = "Plug"  # lucide-react icon name for the UI
    color: str = "#2563EB"
    description: str = ""
    # ``available`` = real connector is implemented for provider auth/sync;
    # other providers are catalog-only. Explicit mock connections exist only
    # for isolated local/test workflows and never represent a real connection.
    available: bool = False
    # ``sync_available`` = provider data sync is implemented. OAuth can be real
    # while sync stays planned (for example Slack, HubSpot, Notion, Calendar).
    sync_available: bool = False


def _spec(**kw) -> ProviderSpec:
    return ProviderSpec(**kw)


PROVIDER_CATALOG: dict[str, ProviderSpec] = {
    # ── 1. Communication ──
    "gmail": _spec(
        provider="gmail",
        name="Gmail",
        category=CATEGORY_COMMUNICATION,
        type=IntegrationType.email,
        connector_cls=GmailConnector,
        icon="Mail",
        color="#EA4335",
        description="Read, search and summarize email; draft AI replies.",
    ),
    "slack": _spec(
        provider="slack",
        name="Slack",
        category=CATEGORY_COMMUNICATION,
        type=IntegrationType.other,
        connector_cls=SlackConnector,
        icon="MessageSquare",
        color="#4A154B",
        available=True,
        description="Send workspace notifications to a channel (OAuth).",
    ),
    # ── 2. Document platforms ──
    "google_drive": _spec(
        provider="google_drive",
        name="Google Drive",
        category=CATEGORY_DOCUMENTS,
        type=IntegrationType.storage,
        connector_cls=GoogleDriveConnector,
        icon="Cloud",
        color="#1A73E8",
        available=True,
        sync_available=True,
        description="Auto-sync Drive folders into your Knowledge Base.",
    ),
    "google_calendar": _spec(
        provider="google_calendar",
        name="Google Calendar",
        category=CATEGORY_COMMUNICATION,
        type=IntegrationType.calendar,
        connector_cls=GoogleCalendarConnector,
        icon="Calendar",
        color="#1A73E8",
        available=True,
        description="Create and update calendar events (OAuth, calendar.events scope).",
    ),
    "google_sheets": _spec(
        provider="google_sheets",
        name="Google Sheets",
        category=CATEGORY_DOCUMENTS,
        type=IntegrationType.storage,
        connector_cls=GoogleSheetsConnector,
        icon="Table",
        color="#0F9D58",
        available=True,
        description="Export captured leads to a spreadsheet (OAuth).",
    ),
    "zapier": _spec(
        provider="zapier",
        name="Zapier",
        category=CATEGORY_DEVELOPMENT,
        type=IntegrationType.other,
        connector_cls=ZapierConnector,
        auth="webhook",
        icon="Zap",
        color="#FF4F00",
        description="Inbound and outbound Zaps via webhooks (no OAuth).",
    ),
    "make": _spec(
        provider="make",
        name="Make",
        category=CATEGORY_DEVELOPMENT,
        type=IntegrationType.other,
        connector_cls=MakeConnector,
        auth="webhook",
        icon="Workflow",
        color="#6D00CC",
        description="Inbound and outbound scenarios via webhooks (no OAuth).",
    ),
    "generic_webhook": _spec(
        provider="generic_webhook",
        name="Signed webhook",
        category=CATEGORY_DEVELOPMENT,
        type=IntegrationType.other,
        connector_cls=GenericWebhookConnector,
        auth="webhook",
        icon="Send",
        color="#334155",
        description="Send signed JSON events to your HTTPS endpoint.",
    ),
    # ── 3. Documentation systems ──
    "notion": _spec(
        provider="notion",
        name="Notion",
        category=CATEGORY_DOCUMENTATION,
        type=IntegrationType.other,
        connector_cls=NotionConnector,
        icon="BookOpen",
        color="#000000",
        available=True,
        description="Link Notion pages (OAuth).",
    ),
    # ── 4. CRM / business ──
    "salesforce": _spec(
        provider="salesforce",
        name="Salesforce",
        category=CATEGORY_CRM,
        type=IntegrationType.crm,
        connector_cls=SalesforceConnector,
        icon="Cloud",
        color="#00A1E0",
        description="Leads, opportunities and accounts.",
    ),
    "hubspot": _spec(
        provider="hubspot",
        name="HubSpot",
        category=CATEGORY_CRM,
        type=IntegrationType.crm,
        connector_cls=HubspotConnector,
        icon="Database",
        color="#FF7A59",
        available=True,
        description="Contacts sync (OAuth, contacts read and write scopes).",
    ),
}


# Setup states shown in the integrations catalog. These are derived from real
# state only: a provider is "connected" only when this org has a live row.
SETUP_CONNECTED = "connected"
SETUP_NOT_CONNECTED = "not_connected"
SETUP_REQUIRES_ACCOUNT_SETUP = "requires_account_setup"
SETUP_PLANNED = "planned"


def provider_setup_status(
    spec: ProviderSpec, *, connected: bool, oauth_configured: bool
) -> str:
    """Plain status for one catalog entry. Never reports a fake connection."""
    if connected:
        return SETUP_CONNECTED
    if not spec.available:
        return SETUP_PLANNED
    if spec.auth == "oauth" and not oauth_configured:
        return SETUP_REQUIRES_ACCOUNT_SETUP
    return SETUP_NOT_CONNECTED


def list_specs() -> list[ProviderSpec]:
    return list(PROVIDER_CATALOG.values())


def get_spec(provider: str) -> Optional[ProviderSpec]:
    return PROVIDER_CATALOG.get(provider)


def get_connector(integration: "Integration") -> BaseConnector:
    """Instantiate the connector bound to a stored integration row."""
    spec = PROVIDER_CATALOG.get(integration.provider)
    if spec is None:
        raise KeyError(f"Unknown integration provider: {integration.provider!r}")
    return spec.connector_cls(integration=integration)


def get_connector_for_provider(provider: str) -> BaseConnector:
    """Instantiate a connector with no bound row (used during connect)."""
    spec = PROVIDER_CATALOG.get(provider)
    if spec is None:
        raise KeyError(f"Unknown integration provider: {provider!r}")
    return spec.connector_cls(integration=None)
