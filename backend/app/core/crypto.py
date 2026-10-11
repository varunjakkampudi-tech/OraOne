"""At-rest encryption for integration secrets (Phase 10).

OAuth access/refresh tokens must never be stored in plaintext. This
module wraps Fernet (AES-128-CBC + HMAC, from the ``cryptography``
package that already ships transitively via ``python-jose[cryptography]``)
behind two tiny helpers: :func:`encrypt` and :func:`decrypt`.

Key resolution (first match wins):

1. ``INTEGRATIONS_ENCRYPTION_KEY`` — a urlsafe-base64 32-byte Fernet key.
2. Derived from ``SECRET_KEY`` (or ``JWT_SECRET_KEY`` as a last-resort
   dev fallback) via SHA-256 so local dev works without extra config.

Rotate by setting ``INTEGRATIONS_ENCRYPTION_KEY`` to a fresh
``Fernet.generate_key()`` value (old ciphertext becomes undecryptable —
re-connect the integration to mint new tokens).
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger("app.crypto")


def _derive_key_from_secret(secret: str) -> bytes:
    """Turn an arbitrary secret string into a valid 32-byte Fernet key."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    explicit = os.environ.get("INTEGRATIONS_ENCRYPTION_KEY")
    if explicit:
        try:
            return Fernet(explicit.encode("utf-8") if isinstance(explicit, str) else explicit)
        except (ValueError, TypeError) as e:  # malformed key
            log.warning("INTEGRATIONS_ENCRYPTION_KEY invalid (%s); deriving instead.", e)

    seed = os.environ.get("SECRET_KEY") or os.environ.get("JWT_SECRET_KEY")
    if not seed:
        raise RuntimeError(
            "Cannot derive integrations encryption key: set INTEGRATIONS_ENCRYPTION_KEY, "
            "SECRET_KEY, or JWT_SECRET_KEY. Refusing to use an insecure hardcoded fallback."
        )
    return Fernet(_derive_key_from_secret(seed))


def encrypt(plaintext: str | None) -> str | None:
    """Encrypt a string; ``None``/empty passes through unchanged."""
    if not plaintext:
        return plaintext
    token = _fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt(ciphertext: str | None) -> str | None:
    """Decrypt a string produced by :func:`encrypt`.

    Returns ``None`` if the value can't be decrypted (wrong key / not
    encrypted / corrupted) instead of raising, so a single bad row never
    takes down a sync. Callers treat ``None`` as "no usable token".
    """
    if not ciphertext:
        return ciphertext
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        log.warning("decrypt failed for an integration secret (wrong key or corrupt).")
        return None
