"""Enterprise RAG retrieval engine (Phase 9 → R4).

Given a natural-language query, find the most relevant ``document_chunks``
for a tenant and return enough metadata to cite the source. R4 upgrades
the original vector-only retrieval to **hybrid search**:

    embed query ─┐
                 ├─ vector search (pgvector cosine, HNSW)
    query text ──┤
                 ├─ full-text search (Postgres ``websearch_to_tsquery``)
                 └─ metadata filters (KB ids, source type)
                          │
                   Reciprocal-Rank Fusion
                          │
                   deterministic rerank
                          │
                  top-k context + citations + confidence

Sources are **multi-type**: a chunk may belong to an uploaded
:class:`Document` *or* a crawled :class:`WebsitePage` (R3). Citations
carry a document filename + page, or a website URL + title, accordingly.

Security
--------
**Every** query is scoped to a single ``organization_id`` (Phase 5
isolation) using the denormalised ``document_chunks.organization_id``
column. An optional ``knowledge_base_ids`` filter narrows further.
"""
from __future__ import annotations

import logging
import math
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.document import Document, DocumentStatus
from app.database.models.document_chunk import DocumentChunk
from app.database.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
from app.database.models.website_page import PageStatus, WebsitePage
from app.providers.embeddings import get_embedding_provider
from app.services import reranker as rerank_mod

log = logging.getLogger("app.rag")

DEFAULT_TOP_K = 5
CANDIDATE_K = 40          # per-strategy candidate pool before fusion
MAX_CANDIDATES = 60       # keyword fallback ceiling
RRF_K = 60                # Reciprocal-Rank-Fusion constant
RERANK_TOP_N = 24         # candidates re-scored by the cross-encoder
DEFAULT_RERANK_ENABLED = True

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "what", "how", "why",
    "are", "was", "you", "your", "from", "have", "has", "can", "will",
    "about", "into", "does", "did", "who", "when", "where", "which",
}


@dataclass
class RetrievedChunk:
    """One retrieved chunk plus its citation metadata (source-agnostic)."""

    content: str
    chunk_index: int
    document_id: Optional[uuid.UUID] = None
    document_name: Optional[str] = None
    website_page_id: Optional[uuid.UUID] = None
    url: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    source_type: str = "document"  # "document" | "website"
    score: Optional[float] = None  # fused relevance in [0, 1]
    components: dict = field(default_factory=dict)

    @property
    def title(self) -> str:
        if self.source_type == "website":
            return self.document_name or self.url or "Web page"
        return self.document_name or "Document"

    def source(self) -> dict:
        """Citation dict for API responses (backward compatible)."""
        return {
            "type": self.source_type,
            "document_id": str(self.document_id) if self.document_id else None,
            "website_page_id": str(self.website_page_id) if self.website_page_id else None,
            "document": self.title,  # legacy key still consumed by the chat UI
            "title": self.title,
            "url": self.url,
            "page": self.page,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "score": round(self.score, 4) if self.score is not None else None,
        }


def _keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9]{3,}", (text or "").lower())
    return [w for w in words if w not in _STOPWORDS][:24]


def _base_query(
    organization_id: uuid.UUID,
    kb_ids: Optional[list[uuid.UUID]],
    project_id: Optional[uuid.UUID] = None,
):
    """Source-agnostic, org-scoped candidate query.

    Filters on the denormalised ``document_chunks.organization_id`` so
    website chunks (no Document) are included. LEFT JOINs resolve the
    citation source and exclude soft-deleted / unprocessed sources.
    When ``project_id`` is given, also scopes to that project's namespace.
    """
    q = (
        select(
            DocumentChunk.id.label("chunk_id"),
            DocumentChunk.content.label("content"),
            DocumentChunk.chunk_index.label("chunk_index"),
            DocumentChunk.chunk_metadata.label("chunk_metadata"),
            DocumentChunk.document_id.label("document_id"),
            DocumentChunk.website_page_id.label("website_page_id"),
            Document.filename.label("document_name"),
            WebsitePage.url.label("page_url"),
            WebsitePage.title.label("page_title"),
        )
        .select_from(DocumentChunk)
        .join(KnowledgeBase, KnowledgeBase.id == DocumentChunk.knowledge_base_id)
        .outerjoin(Document, Document.id == DocumentChunk.document_id)
        .outerjoin(WebsitePage, WebsitePage.id == DocumentChunk.website_page_id)
        .where(DocumentChunk.organization_id == organization_id)  # tenant isolation
        .where(KnowledgeBase.deleted_at.is_(None))
        .where(KnowledgeBase.status == KnowledgeBaseStatus.active)
        .where(
            or_(
                Document.id.is_(None),
                and_(Document.deleted_at.is_(None), Document.status == DocumentStatus.processed),
            )
        )
        .where(or_(WebsitePage.id.is_(None), WebsitePage.status != PageStatus.deleted))
    )
    if kb_ids:
        q = q.where(DocumentChunk.knowledge_base_id.in_(kb_ids))
    if project_id is not None:
        q = q.where(DocumentChunk.project_id == project_id)  # project namespace
    return q


def _row_to_chunk(row, score: Optional[float] = None, components: Optional[dict] = None) -> RetrievedChunk:
    meta = row.chunk_metadata if isinstance(row.chunk_metadata, dict) else {}
    is_web = row.website_page_id is not None
    return RetrievedChunk(
        content=row.content,
        chunk_index=row.chunk_index,
        document_id=row.document_id,
        document_name=(row.page_title or row.page_url) if is_web else row.document_name,
        website_page_id=row.website_page_id,
        url=row.page_url if is_web else meta.get("url"),
        page=meta.get("page"),
        section=meta.get("section"),
        source_type="website" if is_web else "document",
        score=score,
        components=components or {},
    )


# ────────────────────────── hybrid retrieval ──────────────────────────

async def hybrid_search(
    session: AsyncSession,
    query: str,
    organization_id: uuid.UUID,
    *,
    knowledge_base_ids: Optional[list[uuid.UUID]] = None,
    top_k: int = DEFAULT_TOP_K,
    source_types: Optional[list[str]] = None,
    candidate_k: int = CANDIDATE_K,
    project_id: Optional[uuid.UUID] = None,
    rerank: Optional[bool] = None,
    reranker: Optional[str] = None,
    rerank_top_n: int = RERANK_TOP_N,
) -> list[RetrievedChunk]:
    """Hybrid retrieval: vector + full-text + BM25, fused with RRF and
    reordered by a cross-encoder reranker.

    ``rerank``/``reranker`` override the default cross-encoder behaviour
    (``reranker`` is one of ``none|heuristic|cohere|jina|local``). When the
    reranker is disabled or unavailable the deterministic fused order is
    used, so retrieval never hard-fails.
    """
    query = (query or "").strip()
    if not query or top_k <= 0:
        return []

    base = _base_query(organization_id, knowledge_base_ids, project_id)
    if source_types:
        if "website" in source_types and "document" not in source_types:
            base = base.where(DocumentChunk.website_page_id.is_not(None))
        elif "document" in source_types and "website" not in source_types:
            base = base.where(DocumentChunk.document_id.is_not(None))

    vector_rows = await _vector_candidates(session, base, query, candidate_k)
    fts_rows = await _fts_candidates(session, base, query, candidate_k)

    if not vector_rows and not fts_rows:
        return await _keyword_search(session, base, query, top_k)

    by_id: dict = {}
    vector_rank: list = []
    for row, sim in vector_rows:
        by_id[row.chunk_id] = {"row": row, "vector_sim": sim, "fts_rank": None}
        vector_rank.append(row.chunk_id)
    fts_rank: list = []
    for row, frank in fts_rows:
        entry = by_id.setdefault(row.chunk_id, {"row": row, "vector_sim": None, "fts_rank": None})
        entry["fts_rank"] = frank
        fts_rank.append(row.chunk_id)

    fused = _reciprocal_rank_fusion([vector_rank, fts_rank])

    # Real BM25 leg over the fused candidate pool (query-relative lexical).
    cand_ids = list(fused.keys())
    bm25_vals = rerank_mod.bm25_scores(query, [by_id[c]["row"].content or "" for c in cand_ids])
    bm25_by_id = {c: s for c, s in zip(cand_ids, bm25_vals)}

    kws = set(_keywords(query))
    base_scored: list[tuple[float, dict]] = []
    for cid, rrf in fused.items():
        entry = by_id[cid]
        row = entry["row"]
        vsim = entry.get("vector_sim")
        lexical = _lexical_overlap(row.content, kws)
        bm = bm25_by_id.get(cid, 0.0)
        rrf_norm = rrf / (2.0 / RRF_K)  # two lists → loose normalisation to ~[0..1]
        blended = (
            0.50 * (vsim if vsim is not None else 0.0)
            + 0.25 * min(rrf_norm, 1.0)
            + 0.15 * bm
            + 0.10 * lexical
        )
        base_scored.append(
            (blended, {"cid": cid, "entry": entry, "lexical": lexical,
                       "vsim": vsim, "rrf": rrf, "bm25": bm})
        )

    base_scored.sort(key=lambda t: t[0], reverse=True)

    # ── cross-encoder rerank of the strongest candidates ──
    use_rerank = DEFAULT_RERANK_ENABLED if rerank is None else rerank
    provider = (reranker or rerank_mod.DEFAULT_PROVIDER).lower()
    rerank_scores: dict = {}
    if use_rerank and provider != "none" and base_scored:
        head = base_scored[: max(top_k, min(rerank_top_n, len(base_scored)))]
        docs = [by_id[info["cid"]]["row"].content or "" for _, info in head]
        try:
            rr = await rerank_mod.rerank(query, docs, provider=provider)
        except Exception as e:  # noqa: BLE001 — never block retrieval
            log.warning("rerank failed (%s); keeping fused order.", e)
            rr = None
        if rr is not None:
            for (_, info), s in zip(head, rr):
                rerank_scores[info["cid"]] = float(s)

    final: list[tuple[float, dict]] = []
    for blended, info in base_scored:
        cid = info["cid"]
        if cid in rerank_scores:
            # cross-encoder relevance dominates; fused score breaks ties.
            score = 0.7 * rerank_scores[cid] + 0.3 * blended
        else:
            # demote candidates the reranker never saw (the long tail).
            score = blended * (0.85 if rerank_scores else 1.0)
        info["final"] = score
        info["rerank"] = rerank_scores.get(cid)
        final.append((score, info))

    final.sort(key=lambda t: t[0], reverse=True)
    out: list[RetrievedChunk] = []
    for score, info in final[:top_k]:
        row = info["entry"]["row"]
        out.append(
            _row_to_chunk(
                row,
                score=round(max(0.0, min(1.0, score)), 4),
                components={
                    "vector": round(info["vsim"], 4) if info["vsim"] is not None else None,
                    "bm25": round(info["bm25"], 4),
                    "lexical": round(info["lexical"], 4),
                    "rrf": round(info["rrf"], 6),
                    "rerank": round(info["rerank"], 4) if info.get("rerank") is not None else None,
                },
            )
        )
    return out


async def _vector_candidates(session, base, query, candidate_k) -> list[tuple]:
    try:
        query_vec = get_embedding_provider().embed_one(query)
    except Exception as e:  # noqa: BLE001 — degrade to FTS only
        log.warning("query embed failed (%s); skipping vector leg.", e)
        return []
    distance = DocumentChunk.embedding.cosine_distance(query_vec)
    q = (
        base.add_columns(distance.label("distance"))
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance.asc())
        .limit(candidate_k)
    )
    rows = (await session.execute(q)).all()
    out = []
    for row in rows:
        dist = float(row.distance) if row.distance is not None else None
        sim = (1.0 - dist) if dist is not None else None
        out.append((row, sim))
    return out


async def _fts_candidates(session, base, query, candidate_k) -> list[tuple]:
    tsv = func.to_tsvector("english", DocumentChunk.content)
    tsq = func.websearch_to_tsquery("english", query)
    rank = func.ts_rank(tsv, tsq)
    q = (
        base.add_columns(rank.label("ftsrank"))
        .where(tsv.op("@@")(tsq))
        .order_by(rank.desc())
        .limit(candidate_k)
    )
    try:
        rows = (await session.execute(q)).all()
    except Exception as e:  # noqa: BLE001 — FTS is best-effort
        log.warning("fts query failed (%s); skipping fts leg.", e)
        return []
    return [(row, float(row.ftsrank or 0.0)) for row in rows]


def _reciprocal_rank_fusion(rankings: list[list], k: int = RRF_K) -> dict:
    scores: dict = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return scores


def _lexical_overlap(text: str, kws: set[str]) -> float:
    if not kws:
        return 0.0
    low = (text or "").lower()
    hit = sum(1 for w in kws if w in low)
    return hit / len(kws)


async def _keyword_search(session, base, query, top_k) -> list[RetrievedChunk]:
    kw = _keywords(query)
    if not kw:
        return []
    ilikes = [DocumentChunk.content.ilike(f"%{w}%") for w in kw]
    q = base.where(or_(*ilikes)).limit(MAX_CANDIDATES)
    rows = (await session.execute(q)).all()
    if not rows:
        return []
    kset = set(kw)
    ranked = sorted(rows, key=lambda r: _lexical_overlap(r.content, kset), reverse=True)[:top_k]
    return [_row_to_chunk(r, score=round(_lexical_overlap(r.content, kset), 4)) for r in ranked]


# ────────────────────────── public API ──────────────────────────

async def search_chunks(
    session: AsyncSession,
    query: str,
    organization_id: uuid.UUID,
    *,
    knowledge_base_ids: Optional[list[uuid.UUID]] = None,
    top_k: int = DEFAULT_TOP_K,
    source_types: Optional[list[str]] = None,
    project_id: Optional[uuid.UUID] = None,
) -> list[RetrievedChunk]:
    """Return the ``top_k`` most relevant chunks for ``query``.

    Backward-compatible entry point (used by the agent runtime + workflow
    engine). Now powered by :func:`hybrid_search`.
    """
    return await hybrid_search(
        session,
        query,
        organization_id,
        knowledge_base_ids=knowledge_base_ids,
        top_k=top_k,
        source_types=source_types,
        project_id=project_id,
    )


def compute_confidence(chunks: list[RetrievedChunk], query: str) -> float:
    """Heuristic answer confidence in [0, 1].

    Blends the top chunk's relevance, the agreement of the top results,
    and how much of the query's vocabulary the retrieved context covers.
    Deterministic and provider-independent.
    """
    if not chunks:
        return 0.0
    top = chunks[0].score or 0.0
    head = [c.score or 0.0 for c in chunks[:3]]
    agreement = sum(head) / len(head)
    kws = set(_keywords(query))
    if kws:
        joined = " ".join(c.content.lower() for c in chunks[:5])
        coverage = sum(1 for w in kws if w in joined) / len(kws)
    else:
        coverage = 0.5
    conf = 0.45 * top + 0.30 * agreement + 0.25 * coverage
    conf = 1.0 / (1.0 + math.exp(-6.0 * (conf - 0.35)))  # squash to a friendlier range
    return round(max(0.0, min(1.0, conf)), 4)


def build_context(chunks: list[RetrievedChunk], *, max_chars: int = 4000) -> str:
    """Render retrieved chunks into a single CONTEXT block for the prompt.

    Each chunk is numbered and tagged with its source so the model can
    cite it. Total length is bounded to avoid prompt explosion.
    """
    parts: list[str] = []
    budget = max_chars
    for i, c in enumerate(chunks, start=1):
        src = c.title
        if c.url:
            src += f" — {c.url}"
        elif c.page is not None:
            src += f", p.{c.page}"
        piece = c.content.strip()
        if len(piece) > budget:
            piece = piece[:budget]
        parts.append(f"[{i}] (Source: {src})\n{piece}")
        budget -= len(piece)
        if budget <= 0:
            break
    return "\n\n".join(parts)


def dedupe_sources(chunks: list[RetrievedChunk]) -> list[dict]:
    """Collapse retrieved chunks to a unique, ordered list of citations."""
    seen: set[tuple] = set()
    out: list[dict] = []
    for c in chunks:
        key = (str(c.document_id or c.website_page_id), c.page, c.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(c.source())
    return out


__all__ = [
    "RetrievedChunk",
    "search_chunks",
    "hybrid_search",
    "compute_confidence",
    "build_context",
    "dedupe_sources",
    "DEFAULT_TOP_K",
]
