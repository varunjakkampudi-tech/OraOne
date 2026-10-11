"""Phase 12 Module 4 — Role-Based Access Control (RBAC).

A declarative permission matrix layered on top of the existing
``MemberRole`` enum (``owner`` / ``admin`` / ``member`` / ``viewer``).

Rather than scatter ``require_role("owner", "admin")`` checks across the
codebase, callers can express *intent* via fine-grained permissions
(e.g. ``agents.write``) and let the matrix decide which roles satisfy
them. The frontend consumes the same matrix (via ``/api/rbac/me``) to
gate UI affordances, so backend and client never drift.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, List


class Permission:
    """String constants for every guarded capability in the platform."""

    # Agents
    AGENTS_READ = "agents.read"
    AGENTS_WRITE = "agents.write"
    AGENTS_DELETE = "agents.delete"
    # Knowledge base
    KB_READ = "kb.read"
    KB_WRITE = "kb.write"
    KB_DELETE = "kb.delete"
    # AI chat
    CHAT_USE = "chat.use"
    # Conversations / leads
    LEADS_READ = "leads.read"
    LEADS_WRITE = "leads.write"
    # Workflows
    WORKFLOW_READ = "workflow.read"
    WORKFLOW_WRITE = "workflow.write"
    WORKFLOW_EXECUTE = "workflow.execute"
    WORKFLOW_DELETE = "workflow.delete"
    # Analytics
    ANALYTICS_READ = "analytics.read"
    # Integrations
    INTEGRATIONS_READ = "integrations.read"
    INTEGRATIONS_MANAGE = "integrations.manage"
    # Team / members
    TEAM_READ = "team.read"
    TEAM_MANAGE = "team.manage"
    # Billing
    BILLING_READ = "billing.read"
    BILLING_MANAGE = "billing.manage"
    # API platform (keys / scopes)
    APIKEYS_READ = "apikeys.read"
    APIKEYS_MANAGE = "apikeys.manage"
    # Organisation-level settings (branding, danger zone)
    SETTINGS_READ = "settings.read"
    SETTINGS_MANAGE = "settings.manage"
    # Owner-exclusive
    ORG_DELETE = "org.delete"
    ORG_TRANSFER = "org.transfer"


#: Every permission known to the system, in display order.
ALL_PERMISSIONS: List[str] = [
    Permission.AGENTS_READ, Permission.AGENTS_WRITE, Permission.AGENTS_DELETE,
    Permission.KB_READ, Permission.KB_WRITE, Permission.KB_DELETE,
    Permission.CHAT_USE,
    Permission.LEADS_READ, Permission.LEADS_WRITE,
    Permission.WORKFLOW_READ, Permission.WORKFLOW_WRITE,
    Permission.WORKFLOW_EXECUTE, Permission.WORKFLOW_DELETE,
    Permission.ANALYTICS_READ,
    Permission.INTEGRATIONS_READ, Permission.INTEGRATIONS_MANAGE,
    Permission.TEAM_READ, Permission.TEAM_MANAGE,
    Permission.BILLING_READ, Permission.BILLING_MANAGE,
    Permission.APIKEYS_READ, Permission.APIKEYS_MANAGE,
    Permission.SETTINGS_READ, Permission.SETTINGS_MANAGE,
    Permission.ORG_DELETE, Permission.ORG_TRANSFER,
]

_ALL: FrozenSet[str] = frozenset(ALL_PERMISSIONS)

# ── Read-only baseline shared by viewers (and inherited upward) ──
_READ_ONLY: FrozenSet[str] = frozenset({
    Permission.AGENTS_READ,
    Permission.KB_READ,
    Permission.CHAT_USE,
    Permission.LEADS_READ,
    Permission.WORKFLOW_READ,
    Permission.ANALYTICS_READ,
    Permission.INTEGRATIONS_READ,
    Permission.TEAM_READ,
    Permission.BILLING_READ,
    Permission.SETTINGS_READ,
    Permission.APIKEYS_READ,
})

# ── Member: day-to-day builders (read + create/edit, run workflows) ──
_MEMBER: FrozenSet[str] = _READ_ONLY | frozenset({
    Permission.AGENTS_WRITE,
    Permission.KB_WRITE,
    Permission.LEADS_WRITE,
    Permission.WORKFLOW_WRITE,
    Permission.WORKFLOW_EXECUTE,
})

# ── Admin: everything operational, including destructive + management ──
_ADMIN: FrozenSet[str] = _ALL - frozenset({
    Permission.ORG_DELETE,
    Permission.ORG_TRANSFER,
})

#: Role → granted permissions. Owners get the full set.
ROLE_PERMISSIONS: Dict[str, FrozenSet[str]] = {
    "owner": _ALL,
    "admin": _ADMIN,
    "member": _MEMBER,
    "viewer": _READ_ONLY,
}


def permissions_for(role: str) -> FrozenSet[str]:
    """Return the permission set granted to ``role`` (empty if unknown)."""
    return ROLE_PERMISSIONS.get((role or "").lower(), frozenset())


def has_permission(role: str, permission: str) -> bool:
    """True if ``role`` is granted ``permission``."""
    return permission in permissions_for(role)


def role_matrix() -> Dict[str, List[str]]:
    """Serialisable role → sorted permission list, for the API/UI."""
    return {
        role: sorted(perms)
        for role, perms in ROLE_PERMISSIONS.items()
    }
