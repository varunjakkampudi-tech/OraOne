"""Provider connector classes (Phase 10).

Google Drive is fully implemented in ``google_drive.py``. The remaining
providers from the build order are registered here as connector classes
that inherit the mock-capable :class:`BaseConnector` behaviour, so the
whole platform (connect → sync → chunk → embed → RAG → chat) works for
every provider in *mock* mode today. Each class is the single seam where
a real API implementation drops in later — no other layer changes.
"""
from __future__ import annotations

from app.connectors.base import BaseConnector


class GmailConnector(BaseConnector):
    provider = "gmail"


class OutlookConnector(BaseConnector):
    provider = "outlook"


class SlackConnector(BaseConnector):
    provider = "slack"


class TeamsConnector(BaseConnector):
    provider = "ms_teams"


class OneDriveConnector(BaseConnector):
    provider = "onedrive"


class SharepointConnector(BaseConnector):
    provider = "sharepoint"


class DropboxConnector(BaseConnector):
    provider = "dropbox"


class NotionConnector(BaseConnector):
    provider = "notion"


class ConfluenceConnector(BaseConnector):
    provider = "confluence"


class GitbookConnector(BaseConnector):
    provider = "gitbook"


class GithubConnector(BaseConnector):
    provider = "github"


class GitlabConnector(BaseConnector):
    provider = "gitlab"


class JiraConnector(BaseConnector):
    provider = "jira"


class AzureDevopsConnector(BaseConnector):
    provider = "azure_devops"


class SalesforceConnector(BaseConnector):
    provider = "salesforce"


class HubspotConnector(BaseConnector):
    provider = "hubspot"


class ZendeskConnector(BaseConnector):
    provider = "zendesk"
