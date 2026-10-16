"""Catalog-only providers fail closed until their real connector is implemented."""

from app.connectors.base import BaseConnector


class GmailConnector(BaseConnector):
    provider = "gmail"


class SlackConnector(BaseConnector):
    provider = "slack"


class NotionConnector(BaseConnector):
    provider = "notion"


class SalesforceConnector(BaseConnector):
    provider = "salesforce"


class HubspotConnector(BaseConnector):
    provider = "hubspot"
