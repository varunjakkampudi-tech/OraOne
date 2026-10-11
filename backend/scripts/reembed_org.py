"""Re-embed all chunks in an org with the CURRENT embedding provider.

Needed when switching embedding providers (e.g. hashing -> Titan): stored
vectors must live in the same space as query vectors or cosine search is
meaningless.

Usage (with tunnel up):
    ORG_ID=<org-uuid> python scripts/reembed_org.py
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ORG_ID = uuid.UUID(os.environ["ORG_ID"])
BATCH = int(os.environ.get("BATCH", "50"))


async def main() -> None:
    from sqlalchemy import select
    from app.database.session import init_engine
    init_engine()
    from app.database.session import AsyncSessionLocal
    from app.database.models.document import Document
    from app.database.models.document_chunk import DocumentChunk
    from app.providers.embeddings import get_embedding_provider

    provider = get_embedding_provider()
    print(f"Re-embedding org {ORG_ID} with provider={provider.name} (dim={provider.dim})")

    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(
                select(DocumentChunk)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.organization_id == ORG_ID)
                .order_by(DocumentChunk.id)
            )
        ).scalars().all()
        print(f"  {len(rows)} chunks to re-embed")

        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            vectors = provider.embed([c.content for c in batch])
            for chunk, vec in zip(batch, vectors):
                chunk.embedding = vec
            await s.commit()
            print(f"  embedded {min(i + BATCH, len(rows))}/{len(rows)}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
