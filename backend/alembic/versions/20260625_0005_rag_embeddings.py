"""RAG vector store (Phase 9 — Retrieval Augmented Generation).

Turns ``document_chunks`` into a searchable vector store:

1. ``CREATE EXTENSION IF NOT EXISTS vector`` — enable pgvector.
2. Add ``document_chunks.embedding vector(1024)`` (nullable; existing
   chunks are back-filled lazily when a document is re-processed).
3. Build an HNSW index with ``vector_cosine_ops`` for fast approximate
   nearest-neighbour search.

Idempotent / safe: the embedding column and index are created with
``IF NOT EXISTS`` guards so the migration tolerates partially-applied
state. Dimensionality (1024) matches Amazon Titan Text Embeddings v2 and
the hashing fallback (see ``app/providers/embeddings.py``).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0005_rag_embeddings"
down_revision: Union[str, None] = "0004_chat_runtime"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBED_DIM = 1024


def upgrade() -> None:
    # 1. pgvector extension (RDS/Postgres 15+ ships it; CREATE is a no-op
    #    if already present).
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. embedding column on document_chunks.
    op.execute(
        f"ALTER TABLE document_chunks "
        f"ADD COLUMN IF NOT EXISTS embedding vector({EMBED_DIM})"
    )

    # 3. HNSW index for cosine similarity. m / ef_construction are the
    #    pgvector defaults spelled out for clarity.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_embedding")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    # Intentionally leave the `vector` extension installed — other objects
    # may depend on it and dropping an extension is rarely desirable.
