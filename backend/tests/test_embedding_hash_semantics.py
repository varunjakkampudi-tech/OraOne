"""Regression: local feature hashing is not a security hash."""

from app.providers import embeddings


def test_hash_vectorizer_explicitly_uses_non_security_hash(monkeypatch):
    original = embeddings.hashlib.md5
    uses = []

    def observed(data, **kwargs):
        uses.append(kwargs.get("usedforsecurity"))
        return original(data, **kwargs)

    monkeypatch.setattr(embeddings.hashlib, "md5", observed)
    vector = embeddings.HashingEmbeddings(dim=16).embed(["stable token"])[0]
    assert uses == [False, False]
    assert len(vector) == 16
    assert abs(sum(value * value for value in vector) - 1.0) < 1e-9
