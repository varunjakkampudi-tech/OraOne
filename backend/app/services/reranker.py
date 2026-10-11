"""Cross-encoder reranking + BM25 lexical scoring (R5 hybrid retrieval).

The base retriever (:mod:`app.services.rag_service`) fuses a vector leg
(pgvector cosine) and a Postgres full-text leg with Reciprocal-Rank
Fusion. That gives a strong *candidate pool*, but the ordering inside the
pool is still bag-of-features. A **cross-encoder reranker** re-scores each
``(query, passage)`` pair jointly and almost always lifts answer quality,
especially for multi-fact questions.

This module provides:

* :func:`bm25_scores` — a dependency-free Okapi BM25 over a small candidate
  pool (the real "BM25" leg of the hybrid retriever).
* :func:`rerank` — a provider-pluggable cross-encoder. Providers degrade
  gracefully so retrieval never hard-fails:

  ``cohere``  → Cohere Rerank API   (needs ``COHERE_API_KEY``)
  ``jina``    → Jina Reranker API   (needs ``JINA_API_KEY``)
  ``local``   → sentence-transformers ``BAAI/bge-reranker-base`` (if installed)
  ``heuristic`` → in-process BM25 + lexical cross scoring (always available)
  ``none``    → disabled (caller keeps the fused order)

The default provider is ``heuristic`` so the feature works offline and
with zero extra infra; setting ``RERANKER_PROVIDER`` or the org policy to
``cohere`` / ``jina`` / ``local`` swaps in a true neural cross-encoder.
"""
from __future__ import annotations

import asyncio
import logging
import math
import os
import re
from collections import Counter
from typing import Optional

log = logging.getLogger("app.rag.rerank")

VALID_PROVIDERS = ("none", "heuristic", "cohere", "jina", "local")
DEFAULT_PROVIDER = (os.getenv("RERANKER_PROVIDER") or "heuristic").lower()

_COHERE_MODEL = os.getenv("COHERE_RERANK_MODEL", "rerank-english-v3.0")
_JINA_MODEL = os.getenv("JINA_RERANK_MODEL", "jina-reranker-v2-base-multilingual")
_LOCAL_MODEL = os.getenv("BGE_RERANK_MODEL", "BAAI/bge-reranker-base")
_HTTP_TIMEOUT = float(os.getenv("RERANK_HTTP_TIMEOUT", "8.0"))

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "what", "how", "why",
    "are", "was", "you", "your", "from", "have", "has", "can", "will",
    "about", "into", "does", "did", "who", "when", "where", "which", "a",
    "an", "of", "to", "in", "on", "is", "it", "as", "by", "or", "be",
}

# Lazily-instantiated local cross-encoder (heavy; only when provider="local").
_local_model = None
_local_failed = False


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{2,}", (text or "").lower())
    return [w for w in words if w not in _STOPWORDS]


# ───────────────────────────── BM25 ─────────────────────────────

def bm25_scores(query: str, docs: list[str], *, k1: float = 1.5, b: float = 0.75) -> list[float]:
    """Okapi BM25 score per doc against ``query``, normalised to ``[0, 1]``.

    Computed over the *candidate pool only* (typically ≤60 passages), which
    is exactly what we want for reranking: a query-relative lexical signal
    that complements the dense vector leg. Returns a list aligned to
    ``docs`` (``0.0`` when there is nothing to score).
    """
    n = len(docs)
    if n == 0:
        return []
    q_terms = set(_tokenize(query))
    if not q_terms:
        return [0.0] * n

    doc_tokens = [_tokenize(d) for d in docs]
    doc_len = [len(t) for t in doc_tokens]
    avgdl = (sum(doc_len) / n) or 1.0

    # document frequency per term (over the candidate pool)
    df: Counter = Counter()
    for toks in doc_tokens:
        for term in set(toks):
            if term in q_terms:
                df[term] += 1

    idf: dict[str, float] = {}
    for term in q_terms:
        d = df.get(term, 0)
        # BM25+ idf with the +1 to stay non-negative for common terms
        idf[term] = math.log(1.0 + (n - d + 0.5) / (d + 0.5))

    raw: list[float] = []
    for toks, dl in zip(doc_tokens, doc_len):
        tf = Counter(toks)
        score = 0.0
        for term in q_terms:
            f = tf.get(term, 0)
            if not f:
                continue
            denom = f + k1 * (1.0 - b + b * (dl / avgdl))
            score += idf[term] * (f * (k1 + 1.0)) / (denom or 1.0)
        raw.append(score)

    top = max(raw) if raw else 0.0
    if top <= 0.0:
        return [0.0] * n
    return [r / top for r in raw]


# ─────────────────────── heuristic cross-encoder ───────────────────────

def _heuristic_scores(query: str, docs: list[str]) -> list[float]:
    """A deterministic cross-encoder approximation.

    Blends BM25 (lexical importance), Jaccard term overlap (coverage), and
    an exact phrase-containment bonus. No model, no network — always on.
    """
    bm = bm25_scores(query, docs)
    q_terms = set(_tokenize(query))
    q_lower = (query or "").lower().strip()
    out: list[float] = []
    for doc, bm_s in zip(docs, bm):
        d_terms = set(_tokenize(doc))
        jacc = (len(q_terms & d_terms) / len(q_terms | d_terms)) if (q_terms or d_terms) else 0.0
        phrase = 1.0 if q_lower and len(q_lower) >= 6 and q_lower in (doc or "").lower() else 0.0
        score = 0.6 * bm_s + 0.3 * jacc + 0.1 * phrase
        out.append(round(max(0.0, min(1.0, score)), 6))
    return out


# ───────────────────────── remote providers ─────────────────────────

async def _cohere_scores(query: str, docs: list[str]) -> Optional[list[float]]:
    key = os.getenv("COHERE_API_KEY")
    if not key:
        return None
    import httpx

    payload = {"model": _COHERE_MODEL, "query": query, "documents": docs, "top_n": len(docs)}
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.post(
                "https://api.cohere.com/v2/rerank",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:  # noqa: BLE001 — degrade to local
        log.warning("cohere rerank failed (%s); falling back.", e)
        return None
    scores = [0.0] * len(docs)
    for item in data.get("results", []):
        idx = item.get("index")
        if isinstance(idx, int) and 0 <= idx < len(docs):
            scores[idx] = float(item.get("relevance_score", 0.0) or 0.0)
    return scores


async def _jina_scores(query: str, docs: list[str]) -> Optional[list[float]]:
    key = os.getenv("JINA_API_KEY")
    if not key:
        return None
    import httpx

    payload = {"model": _JINA_MODEL, "query": query, "documents": docs, "top_n": len(docs)}
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.post(
                "https://api.jina.ai/v1/rerank",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:  # noqa: BLE001 — degrade to local
        log.warning("jina rerank failed (%s); falling back.", e)
        return None
    scores = [0.0] * len(docs)
    for item in data.get("results", []):
        idx = item.get("index")
        if isinstance(idx, int) and 0 <= idx < len(docs):
            rel = item.get("relevance_score")
            if rel is None:
                rel = item.get("score", 0.0)
            scores[idx] = float(rel or 0.0)
    return scores


def _local_scores_sync(query: str, docs: list[str]) -> Optional[list[float]]:
    global _local_model, _local_failed
    if _local_failed:
        return None
    if _local_model is None:
        try:
            from sentence_transformers import CrossEncoder  # type: ignore

            _local_model = CrossEncoder(_LOCAL_MODEL)
        except Exception as e:  # noqa: BLE001 — not installed / no weights
            log.info("local reranker unavailable (%s); using heuristic.", e)
            _local_failed = True
            return None
    try:
        raw = _local_model.predict([(query, d) for d in docs])
    except Exception as e:  # noqa: BLE001
        log.warning("local rerank predict failed (%s).", e)
        return None
    vals = [float(x) for x in raw]
    # logistic squash → [0, 1] (BGE reranker emits raw logits)
    return [1.0 / (1.0 + math.exp(-v)) for v in vals]


# ───────────────────────────── public ─────────────────────────────

async def rerank(
    query: str,
    docs: list[str],
    *,
    provider: Optional[str] = None,
) -> Optional[list[float]]:
    """Return a relevance score in ``[0, 1]`` per doc, aligned to ``docs``.

    ``None`` means "reranking disabled / unavailable — keep the existing
    order". Any remote/local provider that errors degrades to the
    in-process heuristic so retrieval is never blocked.
    """
    provider = (provider or DEFAULT_PROVIDER).lower()
    if provider not in VALID_PROVIDERS:
        provider = "heuristic"
    if provider == "none" or not docs:
        return None

    if provider == "cohere":
        scores = await _cohere_scores(query, docs)
        if scores is not None:
            return scores
        return _heuristic_scores(query, docs)

    if provider == "jina":
        scores = await _jina_scores(query, docs)
        if scores is not None:
            return scores
        return _heuristic_scores(query, docs)

    if provider == "local":
        scores = await asyncio.to_thread(_local_scores_sync, query, docs)
        if scores is not None:
            return scores
        return _heuristic_scores(query, docs)

    return _heuristic_scores(query, docs)


__all__ = ["bm25_scores", "rerank", "VALID_PROVIDERS", "DEFAULT_PROVIDER"]
