"""Embedding providers (Phase 9 — RAG).

Turns text into fixed-length float vectors so chunks can be stored in
pgvector and retrieved by cosine similarity.

Two concrete backends sit behind one :class:`EmbeddingProvider` contract:

* :class:`BedrockTitanEmbeddings` — Amazon Titan Text Embeddings v2
  (``amazon.titan-embed-text-v2:0``) via the boto3 ``bedrock-runtime``
  ``invoke_model`` API. This is the production path.
* :class:`HashingEmbeddings` — a dependency-free, deterministic hashing
  vectorizer. It captures lexical overlap (shared words → higher cosine)
  so retrieval is meaningful even when no managed embedding model is
  reachable (offline dev, CI, or an account without Titan access).

Both emit vectors of the same dimensionality (``EMBED_DIM``, default
1024) so the database column and HNSW index never have to change when you
swap providers.

Selection (``get_embedding_provider``)::

    EMBEDDING_PROVIDER = "bedrock" | "titan"  → BedrockTitanEmbeddings
    EMBEDDING_PROVIDER = "hash" | "local"     → HashingEmbeddings
    unset                                     → Bedrock if AWS creds look
                                                present, else hashing.

The result is cached for the process; tests can clear it via
``get_embedding_provider.cache_clear()``.
"""
from __future__ import annotations

import abc
import hashlib
import json
import logging
import math
import os
import re
from functools import lru_cache

log = logging.getLogger("app.embeddings")

#: Vector dimensionality. Must match the ``vector(N)`` DB column + HNSW index.
EMBED_DIM = int(os.environ.get("EMBED_DIM", "1024"))

#: Default Titan model id. Titan v2 supports 256 / 512 / 1024 dims.
TITAN_MODEL = os.environ.get("EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")


class EmbeddingError(Exception):
    """Raised when an embedding backend cannot produce vectors."""


class EmbeddingProvider(abc.ABC):
    """Vendor-neutral text→vector interface."""

    name: str = "base"
    dim: int = EMBED_DIM

    @abc.abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns one vector per input, in order."""

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


# ────────────────────────── hashing fallback ──────────────────────────

_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


class HashingEmbeddings(EmbeddingProvider):
    """Deterministic hashing vectorizer (a.k.a. "the hashing trick").

    Each token is hashed to a bucket in ``[0, dim)`` with a signed
    contribution; the per-document vector is L2-normalised so cosine
    similarity reduces to normalised term-overlap. No network, no model,
    fully reproducible — ideal as a safe default and for tests.
    """

    name = "hash"

    def __init__(self, dim: int = EMBED_DIM) -> None:
        self.dim = dim

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return _TOKEN_RE.findall((text or "").lower())

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in self._tokens(text):
            h = hashlib.md5(tok.encode("utf-8")).digest()
            idx = int.from_bytes(h[:4], "big") % self.dim
            sign = 1.0 if (h[4] & 1) else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


# ────────────────────────── Bedrock Titan ──────────────────────────

class BedrockTitanEmbeddings(EmbeddingProvider):
    """Amazon Titan Text Embeddings v2 via boto3 ``bedrock-runtime``.

    Requires AWS credentials with ``bedrock:InvokeModel`` on the Titan
    model and model access granted in the region. One request per text
    (Titan's embedding API embeds a single ``inputText`` at a time).
    """

    name = "bedrock-titan"

    def __init__(self, *, model_id: str = TITAN_MODEL, dim: int = EMBED_DIM, region: str | None = None) -> None:
        self.model_id = model_id
        self.dim = dim
        self._region = region or os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
        self._client = None  # lazy

    def _get_client(self):
        if self._client is None:
            import boto3  # imported lazily so the package import stays cheap

            self._client = boto3.client("bedrock-runtime", region_name=self._region)
        return self._client

    def _embed_one(self, text: str) -> list[float]:
        client = self._get_client()
        body = json.dumps(
            {"inputText": text or " ", "dimensions": self.dim, "normalize": True}
        )
        try:
            resp = client.invoke_model(
                modelId=self.model_id,
                accept="application/json",
                contentType="application/json",
                body=body,
            )
            payload = json.loads(resp["body"].read())
        except Exception as e:  # noqa: BLE001 — normalise to EmbeddingError
            raise EmbeddingError(f"Titan invoke_model failed: {e}") from e
        vec = payload.get("embedding")
        if not isinstance(vec, list) or len(vec) != self.dim:
            raise EmbeddingError(
                f"Titan returned an unexpected embedding shape: {type(vec)} len="
                f"{len(vec) if isinstance(vec, list) else 'n/a'}"
            )
        return [float(x) for x in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


# ────────────────────────── factory ──────────────────────────

def _looks_like_aws_configured() -> bool:
    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID")
        or os.environ.get("AWS_PROFILE")
        or os.environ.get("AWS_ROLE_ARN")
    )


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """Return the active embedding provider (process-cached)."""
    choice = os.environ.get("EMBEDDING_PROVIDER", "").strip().lower()

    if choice in ("hash", "local", "mock"):
        log.info("Embedding provider: hashing (dim=%d)", EMBED_DIM)
        return HashingEmbeddings()

    if choice in ("bedrock", "titan", "aws") or (not choice and _looks_like_aws_configured()):
        try:
            provider = BedrockTitanEmbeddings()
            log.info(
                "Embedding provider: bedrock-titan (model=%s, dim=%d, region=%s)",
                provider.model_id,
                provider.dim,
                provider._region,
            )
            return provider
        except Exception as e:  # pragma: no cover - defensive
            log.warning("Titan embeddings init failed (%s); falling back to hashing.", e)

    log.info("Embedding provider: hashing (dim=%d)", EMBED_DIM)
    return HashingEmbeddings()


__all__ = [
    "EMBED_DIM",
    "EmbeddingError",
    "EmbeddingProvider",
    "HashingEmbeddings",
    "BedrockTitanEmbeddings",
    "get_embedding_provider",
]
