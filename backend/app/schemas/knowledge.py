"""Pydantic schemas for the Knowledge Base / Documents API (Phase 6)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ──────────────── Knowledge Bases ────────────────

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, description="draft | active | archived")


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    description: Optional[str] = None
    status: Optional[str] = None


class KnowledgeBaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseListResponse(BaseModel):
    items: list[KnowledgeBaseRead]
    total: int
    limit: int
    offset: int


# ──────────────── Documents ────────────────

class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    organization_id: uuid.UUID
    filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    s3_key: str
    status: str
    chunk_count: int = 0
    embedded_count: int = 0
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_error: Optional[str] = None
    processing_time_ms: Optional[int] = None
    folder_id: Optional[uuid.UUID] = None
    checksum: Optional[str] = None
    version: int = 1
    summary: Optional[str] = None
    suggested_questions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    doc_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentRead]
    total: int
    limit: int
    offset: int


# ──────────────── Document organization (R2) ────────────────

class DocumentPatch(BaseModel):
    """Move to a folder, clear folder, or set tags."""
    folder_id: Optional[uuid.UUID] = None
    clear_folder: bool = False
    tags: Optional[list[str]] = None


class BulkAction(BaseModel):
    document_ids: list[uuid.UUID] = Field(..., min_length=1)
    action: str = Field(..., description="delete | move | tag | reprocess")
    folder_id: Optional[uuid.UUID] = None
    clear_folder: bool = False
    tags: Optional[list[str]] = None


class BulkResult(BaseModel):
    affected: int
    action: str


class DocumentPreview(BaseModel):
    id: uuid.UUID
    filename: str
    summary: Optional[str] = None
    suggested_questions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    doc_metadata: dict[str, Any] = Field(default_factory=dict)
    excerpt: str = ""


class DocumentVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    filename: Optional[str] = None
    checksum: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime


# ──────────────── Knowledge folders (R2) ────────────────

class KnowledgeFolderCreate(BaseModel):
    knowledge_base_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=160)
    parent_folder_id: Optional[uuid.UUID] = None
    color: Optional[str] = Field(default=None, max_length=9)


class KnowledgeFolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    parent_folder_id: Optional[uuid.UUID] = None
    color: Optional[str] = Field(default=None, max_length=9)


class KnowledgeFolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    parent_folder_id: Optional[uuid.UUID] = None
    name: str
    color: Optional[str] = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


# ──────────────── Knowledge search (R2) ────────────────

class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    knowledge_base_id: Optional[uuid.UUID] = None
    top_k: int = Field(default=8, ge=1, le=25)


class KnowledgeSearchHit(BaseModel):
    document_id: Optional[uuid.UUID] = None
    website_page_id: Optional[uuid.UUID] = None
    document: str
    url: Optional[str] = None
    source_type: str = "document"
    content: str
    page: Optional[int] = None
    section: Optional[str] = None
    score: Optional[float] = None


class KnowledgeSearchResponse(BaseModel):
    query: str
    hits: list[KnowledgeSearchHit] = Field(default_factory=list)


# ──────────────── Document Chunks (read-only for now) ────────────────

class ChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)


# ──────────────── Dashboard ────────────────

class KnowledgeStats(BaseModel):
    total_knowledge_bases: int
    total_documents: int
    total_chunks: int
    total_embeddings: int = 0
