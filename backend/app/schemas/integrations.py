"""Pydantic schemas for the Integrations Platform API (Phase 10).

IMPORTANT: response models NEVER expose ``access_token`` /
``refresh_token`` — secrets stay encrypted at rest and server-side.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ──────────────── Catalog ────────────────


class ProviderCatalogItem(BaseModel):
    """A provider as shown in the integrations grid."""

    provider: str
    name: str
    category: str
    type: str
    auth: str
    icon: str
    color: str
    description: str
    available: bool
    # Provider data sync is implemented. False means sync is planned.
    sync_available: bool = False
    # Names only (never values) of the server settings OAuth needs.
    required_settings: list[str] = Field(default_factory=list)


# ──────────────── Integrations ────────────────


class IntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    provider: str
    category: Optional[str] = None
    type: str
    status: str
    connection_type: str
    external_account: Optional[str] = None
    knowledge_base_id: Optional[uuid.UUID] = None
    sync_schedule: str
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class IntegrationCatalogEntry(BaseModel):
    """Catalog item merged with the org's connection state (if any)."""

    catalog: ProviderCatalogItem
    integration: Optional[IntegrationRead] = None
    # connected | not_connected | requires_account_setup | planned
    setup_status: str = "planned"
    setup_message: str = ""


class IntegrationCatalogResponse(BaseModel):
    items: list[IntegrationCatalogEntry]
    total: int


class ConnectRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=60)
    # OAuth authorization code for the callback leg of a real flow.
    code: Optional[str] = None
    # Non-sensitive settings (e.g. selected Drive folder id).
    config: Optional[dict[str, Any]] = None
    # Explicitly request a mock; the API permits this only in local/test envs.
    mock: bool = False


class ConnectResponse(BaseModel):
    integration: Optional[IntegrationRead] = None
    # When set, the client must redirect the browser to begin OAuth.
    authorize_url: Optional[str] = None


class SyncJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    integration_id: uuid.UUID
    status: str
    trigger: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    documents_synced: int
    documents_deleted: int
    errors: int
    error_message: Optional[str] = None
    created_at: datetime


class SyncJobListResponse(BaseModel):
    items: list[SyncJobRead]
    total: int


class SyncLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    integration_id: uuid.UUID
    event: str
    level: str
    message: Optional[str] = None
    created_at: datetime


class SyncLogListResponse(BaseModel):
    items: list[SyncLogRead]
    total: int


# ──────────────── Browse & selection (selective sync) ────────────────


class BrowseItem(BaseModel):
    """A folder or file in the provider, shown in the file-picker."""

    external_id: str
    name: str
    mime_type: Optional[str] = None
    is_folder: bool = False
    modified_at: Optional[Any] = None
    size: Optional[int] = None
    path: Optional[str] = None


class BrowseResponse(BaseModel):
    parent_id: Optional[str] = None
    items: list[BrowseItem]


class SelectionRef(BaseModel):
    """A user-selected folder or file (id + display hints)."""

    external_id: str
    name: Optional[str] = None
    path: Optional[str] = None
    mime_type: Optional[str] = None


class SelectionOptions(BaseModel):
    """Advanced sync filters."""

    file_types: Optional[list[str]] = None  # e.g. ["pdf","gdoc","docx"]
    ignore_images: bool = True
    ignore_videos: bool = True
    max_size_mb: Optional[int] = 100
    ignore_trash: bool = True
    ignore_shared: bool = False
    recent_days: Optional[int] = None  # set by "Quick" mode


class SelectionPayload(BaseModel):
    """The user's sync scope — stored in ``integration.config['selection']``."""

    mode: str = Field(default="folder")  # quick | folder | full | selection
    folders: list[SelectionRef] = Field(default_factory=list)
    files: list[SelectionRef] = Field(default_factory=list)
    options: SelectionOptions = Field(default_factory=SelectionOptions)


class SyncedItemRead(BaseModel):
    """A row from the resolved ``integration_documents`` manifest."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: str
    name: str
    mime_type: Optional[str] = None
    path: Optional[str] = None
    is_folder: bool
    selected: bool
    status: str
    size_bytes: Optional[int] = None
    last_synced: Optional[datetime] = None
    document_id: Optional[uuid.UUID] = None


class SyncedItemsResponse(BaseModel):
    items: list[SyncedItemRead]
    total: int
    selection: Optional[SelectionPayload] = None


# ──────────────── Health & analytics (R5) ────────────────


class IntegrationHealth(BaseModel):
    """A cheap connectivity/credential probe result for one integration."""

    provider: str
    status: str  # connected | syncing | disconnected | error | token_expired
    healthy: bool
    token_expires_at: Optional[datetime] = None
    token_expired: bool = False
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = None
    detail: Optional[str] = None


class IntegrationAnalytics(BaseModel):
    """Aggregate metrics for one integration's sync history."""

    provider: str
    status: str
    documents_imported: int = 0
    total_sync_jobs: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0
    documents_synced_total: int = 0
    documents_deleted_total: int = 0
    errors_total: int = 0
    last_synced_at: Optional[datetime] = None
    avg_sync_seconds: Optional[float] = None
    recent_jobs: list[SyncJobRead] = Field(default_factory=list)
