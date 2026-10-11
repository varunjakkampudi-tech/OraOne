"""Repositories — thin data-access objects (one per aggregate).

Each repository takes an `AsyncSession` and exposes typed CRUD/query methods.
Services orchestrate multiple repositories and hold the business logic.

Layering:

    routes  →  services  →  repositories  →  ORM models / database
"""

from app.database.repositories.base import BaseRepository
from app.database.repositories.user_repository import UserRepository
from app.database.repositories.organization_repository import OrganizationRepository
from app.database.repositories.organization_member_repository import OrganizationMemberRepository
from app.database.repositories.agent_repository import AgentRepository
from app.database.repositories.conversation_repository import ConversationRepository
from app.database.repositories.message_repository import MessageRepository
from app.database.repositories.integration_repository import (
    IntegrationRepository,
    OrgScopedIntegrationRepository,
)
from app.database.repositories.sync_repository import (
    SyncJobRepository,
    SyncLogRepository,
)

__all__ = [
    "BaseRepository",
    "UserRepository",
    "OrganizationRepository",
    "OrganizationMemberRepository",
    "AgentRepository",
    "ConversationRepository",
    "MessageRepository",
    "IntegrationRepository",
    "OrgScopedIntegrationRepository",
    "SyncJobRepository",
    "SyncLogRepository",
]
