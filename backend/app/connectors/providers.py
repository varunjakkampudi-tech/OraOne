"""Provider connectors.

Gmail and Salesforce are catalog-only and fail closed until their connectors
are implemented. Slack, HubSpot, Notion, Google Calendar and Google Sheets
implement only the OAuth connect/refresh shape; their sync and data calls are
planned and raise :class:`NotConnectedError`. Zapier, Make and the generic
signed webhook have no OAuth and no data calls.
"""

from typing import Any, Optional

from app.connectors.base import BaseConnector, ConnectResult, NotConnectedError
from app.core import crypto
from app.services import oauth_service


class _OAuthOnlyConnector(BaseConnector):
    """OAuth connect/refresh only. Sync and data calls stay planned."""

    def connect(self, *, code: Optional[str] = None, **kwargs: Any) -> ConnectResult:
        return oauth_service.complete_connect(self.provider, code=code, **kwargs)

    def refresh_token(self) -> ConnectResult:
        if self.integration is None:
            raise NotConnectedError("No integration bound to connector.")
        refresh = crypto.decrypt(self.integration.refresh_token)
        if not refresh:
            raise NotConnectedError("No refresh token available.")
        return oauth_service.refresh(self.provider, refresh_token=refresh)

    def sync(self):
        raise NotConnectedError(
            f"{self.provider} sync is planned and not available yet."
        )


class _WebhookOnlyConnector(BaseConnector):
    """No OAuth and no provider calls. Nothing can be linked through this connector."""

    def connect(self, *, code: Optional[str] = None, **kwargs: Any) -> ConnectResult:
        raise NotConnectedError(
            f"{self.provider} is not connected through OAuth. Use the Webhooks page."
        )


class GmailConnector(BaseConnector):
    provider = "gmail"


class SlackConnector(_OAuthOnlyConnector):
    provider = "slack"


class NotionConnector(_OAuthOnlyConnector):
    provider = "notion"


class SalesforceConnector(BaseConnector):
    provider = "salesforce"


class HubspotConnector(_OAuthOnlyConnector):
    provider = "hubspot"


class GoogleCalendarConnector(_OAuthOnlyConnector):
    provider = "google_calendar"


class GoogleSheetsConnector(_OAuthOnlyConnector):
    provider = "google_sheets"


class ZapierConnector(_WebhookOnlyConnector):
    provider = "zapier"


class MakeConnector(_WebhookOnlyConnector):
    provider = "make"


class GenericWebhookConnector(_WebhookOnlyConnector):
    provider = "generic_webhook"


__all__ = [
    "GmailConnector",
    "SlackConnector",
    "NotionConnector",
    "SalesforceConnector",
    "HubspotConnector",
    "GoogleCalendarConnector",
    "GoogleSheetsConnector",
    "ZapierConnector",
    "MakeConnector",
    "GenericWebhookConnector",
]
