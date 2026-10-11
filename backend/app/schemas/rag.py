"""Pydantic schemas for the RAG query/search API (R4)."""
from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class RagSource(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = "document"
    document_id: Optional[str] = None
    website_page_id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_index: Optional[int] = None
    score: Optional[float] = None


class RagQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    knowledge_base_ids: Optional[list[uuid.UUID]] = None
    top_k: int = Field(default=5, ge=1, le=20)
    source_types: Optional[list[str]] = Field(
        default=None, description="Subset of ['document', 'website']"
    )


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[RagSource] = Field(default_factory=list)
    confidence: float = 0.0
    related_questions: list[str] = Field(default_factory=list)
    context_chunks: int = 0
    grounded: bool = False
    model: Optional[str] = None


class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    knowledge_base_ids: Optional[list[uuid.UUID]] = None
    top_k: int = Field(default=8, ge=1, le=50)
    source_types: Optional[list[str]] = None


class RagSearchHit(BaseModel):
    content: str
    score: Optional[float] = None
    source_type: str = "document"
    title: Optional[str] = None
    url: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_index: int = 0
    components: dict[str, Any] = Field(default_factory=dict)


class RagSearchResponse(BaseModel):
    hits: list[RagSearchHit] = Field(default_factory=list)
    count: int = 0


class RagSourcesResponse(BaseModel):
    documents: int
    websites: int
    chunks: int
    knowledge_bases: int
