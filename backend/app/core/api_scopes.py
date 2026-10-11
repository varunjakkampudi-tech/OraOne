"""API key scope registry (Phase 12, Module 9).

Scopes gate which external (``/api/v1/*``) endpoints a key may call. They
are intentionally coarse-grained and read-leaning; each maps onto an
internal RBAC permission so external access can never exceed what the
platform already enforces.
"""
from __future__ import annotations

from app.core.permissions import Permission

# scope -> (human label, backing internal permission)
API_SCOPES: dict[str, dict] = {
    "chat:read": {"label": "Read conversations & messages", "permission": Permission.CHAT_USE},
    "chat:write": {"label": "Send chat messages", "permission": Permission.CHAT_USE},
    "agents:read": {"label": "Read agents", "permission": Permission.AGENTS_READ},
    "agents:write": {"label": "Create & update agents", "permission": Permission.AGENTS_WRITE},
    "knowledge:read": {"label": "Read knowledge bases", "permission": Permission.KB_READ},
    "knowledge:write": {"label": "Create & update knowledge bases", "permission": Permission.KB_WRITE},
    "documents:read": {"label": "Read documents", "permission": Permission.KB_READ},
    "documents:write": {"label": "Upload & manage documents", "permission": Permission.KB_WRITE},
    "websites:read": {"label": "Read website crawlers", "permission": Permission.KB_READ},
    "websites:write": {"label": "Manage website crawlers", "permission": Permission.KB_WRITE},
    "search:read": {"label": "Search & RAG queries", "permission": Permission.KB_READ},
    "widgets:read": {"label": "Read website widgets", "permission": Permission.AGENTS_READ},
    "widgets:manage": {"label": "Manage website widgets", "permission": Permission.AGENTS_WRITE},
    "integrations:read": {"label": "Read integrations", "permission": Permission.INTEGRATIONS_READ},
    "integrations:manage": {"label": "Manage & sync integrations", "permission": Permission.INTEGRATIONS_MANAGE},
    "workflows:read": {"label": "Read workflows", "permission": Permission.WORKFLOW_READ},
    "workflows:execute": {"label": "Execute workflows", "permission": Permission.WORKFLOW_EXECUTE},
    "analytics:read": {"label": "Read analytics", "permission": Permission.ANALYTICS_READ},
    "usage:read": {"label": "Read usage & limits", "permission": Permission.BILLING_READ},
    "webhooks:manage": {"label": "Manage webhook endpoints", "permission": Permission.APIKEYS_MANAGE},
}

ALL_SCOPES = tuple(API_SCOPES.keys())


def is_valid_scope(scope: str) -> bool:
    return scope in API_SCOPES


def normalize_scopes(scopes: list[str]) -> list[str]:
    """Drop unknown/duplicate scopes, preserving registry order."""
    requested = {s for s in scopes if s in API_SCOPES}
    return [s for s in ALL_SCOPES if s in requested]


def scope_catalogue() -> list[dict]:
    return [
        {"scope": s, "label": meta["label"]}
        for s, meta in API_SCOPES.items()
    ]
