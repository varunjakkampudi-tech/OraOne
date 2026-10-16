"""OpenRouter embeddings: request shape, ordering and error handling."""

from __future__ import annotations

import httpx
import pytest

from app.providers import embeddings
from app.providers.embeddings import (
    EmbeddingError,
    HashingEmbeddings,
    OpenRouterEmbeddings,
)


def _response(rows, status=200):
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/embeddings")
    return httpx.Response(status, json={"data": rows}, request=request)


def test_openrouter_embeddings_return_vectors_in_input_order(monkeypatch):
    dim = 3
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["auth"] = headers["Authorization"]
        # Return rows out of order to prove the client restores input order.
        return _response(
            [
                {"index": 1, "embedding": [0.0, 1.0, 0.0]},
                {"index": 0, "embedding": [1.0, 0.0, 0.0]},
            ]
        )

    monkeypatch.setattr(embeddings.httpx, "post", fake_post)
    provider = OpenRouterEmbeddings("sk-or-test", dim=dim)
    vectors = provider.embed(["first", "second"])

    assert vectors == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    assert captured["url"].endswith("/embeddings")
    assert captured["auth"] == "Bearer sk-or-test"
    assert captured["json"]["input"] == ["first", "second"]
    assert captured["json"]["dimensions"] == dim


def test_openrouter_embeddings_reject_wrong_dimension(monkeypatch):
    monkeypatch.setattr(
        embeddings.httpx,
        "post",
        lambda *a, **k: _response([{"index": 0, "embedding": [0.1, 0.2]}]),
    )
    provider = OpenRouterEmbeddings("sk-or-test", dim=3)
    with pytest.raises(EmbeddingError, match="unexpected embedding shape"):
        provider.embed(["text"])


def test_openrouter_embeddings_wrap_http_failures(monkeypatch):
    monkeypatch.setattr(
        embeddings.httpx,
        "post",
        lambda *a, **k: _response([], status=500),
    )
    provider = OpenRouterEmbeddings("sk-or-test", dim=3)
    with pytest.raises(EmbeddingError, match="request failed"):
        provider.embed(["text"])


def test_hashing_embeddings_are_normalised_and_deterministic():
    provider = HashingEmbeddings(dim=64)
    first = provider.embed_one("delivery times for hyderabad")
    second = provider.embed_one("delivery times for hyderabad")
    assert first == second
    assert abs(sum(v * v for v in first) - 1.0) < 1e-9 or all(v == 0 for v in first)
