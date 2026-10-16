"""Embedding providers for retrieval-augmented generation (RAG).

Text is turned into fixed-length vectors that are stored in pgvector and
searched by cosine similarity. Two providers share one contract:

* :class:`OpenRouterEmbeddings` calls the OpenAI-compatible ``/embeddings``
  endpoint of OpenRouter. This is the production path.
* :class:`HashingEmbeddings` is a deterministic, dependency-free fallback. It
  keeps retrieval meaningful (shared words give higher similarity) when no API
  key is configured, for example in local development and CI.

Both produce vectors of the same size (``EMBED_DIM``) so the database column and
its index never change when the provider does.

Selection (see :func:`get_embedding_provider`):

* ``OPENROUTER_API_KEY`` is set → :class:`OpenRouterEmbeddings`
* otherwise                     → :class:`HashingEmbeddings`
"""

from __future__ import annotations

import abc
import hashlib
import logging
import math
import os
import re
from functools import lru_cache

import httpx

log = logging.getLogger("app.embeddings")

#: Vector dimensionality. Must match the ``vector(N)`` column and its index.
EMBED_DIM = int(os.environ.get("EMBED_DIM", "1024"))

#: Embedding model used through OpenRouter (overridable via ``EMBEDDING_MODEL``).
DEFAULT_EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "openai/text-embedding-3-small"
)

_OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
).rstrip("/")
_EMBED_TIMEOUT_SECONDS = float(os.environ.get("EMBEDDING_TIMEOUT", "30"))
_MAX_BATCH = 96


class EmbeddingError(Exception):
    """Raised when an embedding backend cannot produce vectors."""


class EmbeddingProvider(abc.ABC):
    """Common interface for every text-to-vector backend."""

    name: str = "base"
    dim: int = EMBED_DIM

    @abc.abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts and return one vector per input, in order."""

    def embed_one(self, text: str) -> list[float]:
        """Embed a single text."""
        return self.embed([text])[0]


_TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


class HashingEmbeddings(EmbeddingProvider):
    """Deterministic hashing vectorizer, used when no embedding API is configured.

    Each token maps to a bucket with a signed contribution. Vectors are
    L2-normalised, so cosine similarity reflects term overlap. There is no
    network call, and the output is reproducible.
    """

    name = "hash"

    def __init__(self, dim: int = EMBED_DIM) -> None:
        self.dim = dim

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return _TOKEN_RE.findall((text or "").lower())

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in self._tokens(text):
            # Bucket selection, not security: MD5 is used only to spread tokens.
            digest = hashlib.md5(token.encode("utf-8"), usedforsecurity=False).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if (digest[4] & 1) else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(value * value for value in vec))
        if norm > 0.0:
            vec = [value / norm for value in vec]
        return vec

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]


class OpenRouterEmbeddings(EmbeddingProvider):
    """Embeddings from OpenRouter's OpenAI-compatible ``/embeddings`` endpoint."""

    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_EMBEDDING_MODEL,
        dim: int = EMBED_DIM,
        base_url: str = _OPENROUTER_BASE_URL,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self.dim = dim
        self._base_url = base_url

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed ``texts`` in batches, returning vectors in the same order."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _MAX_BATCH):
            batch = [text or " " for text in texts[start : start + _MAX_BATCH]]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        """Call the endpoint once and validate the returned shape."""
        try:
            response = httpx.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self.model, "input": batch, "dimensions": self.dim},
                timeout=_EMBED_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            rows = response.json()["data"]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise EmbeddingError(
                f"OpenRouter embeddings request failed: {exc}"
            ) from exc

        ordered = sorted(rows, key=lambda row: row.get("index", 0))
        vectors = [[float(value) for value in row["embedding"]] for row in ordered]
        if len(vectors) != len(batch) or any(len(v) != self.dim for v in vectors):
            raise EmbeddingError("OpenRouter returned an unexpected embedding shape.")
        return vectors


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """Return the active embedding provider. The result is cached per process."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if api_key:
        log.info(
            "Embedding provider: openrouter (model=%s, dim=%d)",
            DEFAULT_EMBEDDING_MODEL,
            EMBED_DIM,
        )
        return OpenRouterEmbeddings(api_key)
    log.info(
        "Embedding provider: hashing (dim=%d); set OPENROUTER_API_KEY for semantic embeddings",
        EMBED_DIM,
    )
    return HashingEmbeddings()


__all__ = [
    "EMBED_DIM",
    "EmbeddingError",
    "EmbeddingProvider",
    "HashingEmbeddings",
    "OpenRouterEmbeddings",
    "get_embedding_provider",
]
