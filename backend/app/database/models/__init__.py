"""SQLAlchemy ORM models. Import this package to register tables with Base."""

from app.database.models.user import User, UserRole, UserStatus
from app.database.models.organization import Organization, OrgPlan
from app.database.models.organization_member import (
    OrganizationMember,
    MemberRole,
    MemberStatus,
)
from app.database.models.project import Project, ProjectStatus
from app.database.models.agent import Agent, AgentType, AgentStatus
from app.database.models.agent_config import AgentConfig
from app.database.models.conversation import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
)
from app.database.models.message import Message, MessageSender
from app.database.models.integration import (
    Integration,
    IntegrationStatus,
    IntegrationType,
    ConnectionType,
    SyncSchedule,
)
from app.database.models.sync_job import SyncJob, SyncJobStatus, SyncTrigger
from app.database.models.sync_log import SyncLog, SyncLogLevel
from app.database.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
from app.database.models.document import Document, DocumentStatus
from app.database.models.document_chunk import DocumentChunk
from app.database.models.integration_document import (
    IntegrationDocument,
    IntegrationDocStatus,
)
from app.database.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowTrigger,
    WorkflowStep,
    StepType,
    WorkflowRun,
    RunStatus,
    WorkflowRunStep,
    RunStepStatus,
    WorkflowVersion,
)
from app.database.models.billing import (
    Plan,
    PlanCode,
    Subscription,
    SubscriptionStatus,
    BillingCycle,
    Invoice,
    InvoiceStatus,
)
from app.database.models.organization_invitation import (
    OrganizationInvitation,
    InvitationStatus,
)
from app.database.models.usage import UsageCounter
from app.database.models.api_key import ApiKey
from app.database.models.ai_model_policy import AIModelPolicy
from app.database.models.org_branding import OrgBranding
from app.database.models.audit_log import AuditLog
from app.database.models.conversation_folder import ConversationFolder
from app.database.models.knowledge_folder import KnowledgeFolder
from app.database.models.document_version import DocumentVersion
from app.database.models.website import (
    Website,
    WebsiteStatus,
    CrawlMode,
    CrawlFrequency,
)
from app.database.models.website_page import WebsitePage, PageStatus
from app.database.models.crawl_job import (
    CrawlJob,
    CrawlJobStatus,
    CrawlTrigger,
    CrawlLog,
)
from app.database.models.crawl_frontier import CrawlFrontier, FrontierStatus
from app.database.models.widget import (
    Widget,
    WidgetStatus,
    WidgetType,
    WidgetPosition,
    WidgetAuthMode,
)
from app.database.models.widget_domain import WidgetDomain
from app.database.models.widget_session import WidgetSession
from app.database.models.widget_event import WidgetEvent, WidgetEventType
from app.database.models.webhook import (
    WebhookEndpoint,
    WebhookDelivery,
    WebhookEventType,
    WebhookStatus,
    WebhookOutbox,
    OutboxStatus,
)
from app.database.models.api_log import ApiRequestLog
from app.database.models.contact import ContactSubmission, NewsletterSubscriber
from app.database.models.analytics import (
    AnalyticsEvent,
    DailyMetric,
    CostReport,
    AnswerFeedback,
)
from app.database.models.collaboration import (
    Team,
    TeamMember,
    TeamRole,
    ResourcePermission,
    ResourceType,
    PrincipalType,
    PermissionLevel,
    Comment,
    Mention,
    Reaction,
    Notification,
    NotificationType,
    ActivityEvent,
    Task,
    TaskStatus,
    ResourceFollow,
)
from app.database.models.operations import (
    SecurityEvent,
    SecuritySeverity,
    SecurityEventType,
    FeatureFlag,
    DeploymentRecord,
    DeploymentStatus,
)
from app.database.models.lead import Lead, LeadStatus, LeadTemperature
from app.database.models.visitor_profile import VisitorProfile
from app.database.models.feature_request import (
    FeatureRequest,
    FeatureRequestType,
    FeatureRequestStatus,
)
from app.database.models.agent_channel import AgentChannel, ChannelType, ChannelStatus
from app.database.models.marketplace import (
    MarketplaceInstallation,
    InstallStatus,
)
from app.database.models.agent_prompt_version import AgentPromptVersion
from app.database.models.marketplace_review import MarketplaceReview
from app.database.models.product import (
    Product,
    ProductStatus,
    ProductVisibility,
)
from app.database.models.organization_entitlement import OrganizationEntitlement

__all__ = [
    "User", "UserRole", "UserStatus",
    "Organization", "OrgPlan",
    "OrganizationMember", "MemberRole", "MemberStatus",
    "Agent", "AgentType", "AgentStatus",
    "AgentConfig",
    "AgentPromptVersion",
    "MarketplaceReview",
    "Conversation", "ConversationChannel", "ConversationStatus",
    "Message", "MessageSender",
    "Integration", "IntegrationStatus", "IntegrationType",
    "ConnectionType", "SyncSchedule",
    "SyncJob", "SyncJobStatus", "SyncTrigger",
    "SyncLog", "SyncLogLevel",
    "KnowledgeBase", "KnowledgeBaseStatus",
    "Document", "DocumentStatus",
    "DocumentChunk",
    "IntegrationDocument", "IntegrationDocStatus",
    "Workflow", "WorkflowStatus", "WorkflowTrigger",
    "WorkflowStep", "StepType",
    "WorkflowRun", "RunStatus",
    "WorkflowRunStep", "RunStepStatus",
    "WorkflowVersion",
    "Plan", "PlanCode",
    "Subscription", "SubscriptionStatus", "BillingCycle",
    "Invoice", "InvoiceStatus",
    "OrganizationInvitation", "InvitationStatus",
    "UsageCounter",
    "ApiKey",
    "AIModelPolicy",
    "OrgBranding",
    "AuditLog",
    "ConversationFolder",
    "KnowledgeFolder",
    "DocumentVersion",
    "Website", "WebsiteStatus", "CrawlMode", "CrawlFrequency",
    "WebsitePage", "PageStatus",
    "CrawlJob", "CrawlJobStatus", "CrawlTrigger", "CrawlLog",
    "CrawlFrontier", "FrontierStatus",
    "Widget", "WidgetStatus", "WidgetType", "WidgetPosition", "WidgetAuthMode",
    "WidgetDomain",
    "WidgetSession",
    "WidgetEvent", "WidgetEventType",
    "WebhookEndpoint", "WebhookDelivery", "WebhookEventType", "WebhookStatus",
    "WebhookOutbox", "OutboxStatus",
    "ApiRequestLog",
    "ContactSubmission", "NewsletterSubscriber",
    "AnalyticsEvent", "DailyMetric", "CostReport", "AnswerFeedback",
    # R9 — Collaboration
    "Team", "TeamMember", "TeamRole",
    "ResourcePermission", "ResourceType", "PrincipalType", "PermissionLevel",
    "Comment", "Mention", "Reaction",
    "Notification", "NotificationType",
    "ActivityEvent",
    "Task", "TaskStatus",
    "ResourceFollow",
    # R10 — Security & Operations
    "SecurityEvent", "SecuritySeverity", "SecurityEventType",
    "FeatureFlag",
    "DeploymentRecord", "DeploymentStatus",
    # Leads (CRM)
    "Lead", "LeadStatus", "LeadTemperature",
    # Unified cross-channel visitor identity
    "VisitorProfile",
    # Feature requests / feedback board
    "FeatureRequest", "FeatureRequestType", "FeatureRequestStatus",
    # Agent delivery channels (Website Chat, Widget, WhatsApp, SMS, API)
    "AgentChannel", "ChannelType", "ChannelStatus",
    "MarketplaceInstallation", "InstallStatus",
    # Phase 1 — Product catalog & entitlements
    "Product", "ProductStatus", "ProductVisibility",
    "OrganizationEntitlement",
]