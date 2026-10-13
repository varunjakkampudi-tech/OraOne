import { Suspense, lazy } from "react";
import "@/App.css";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useLocation,
  useParams,
} from "react-router-dom";
import { MotionConfig } from "framer-motion";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";
import OraOneLoader from "@/components/ui/OraOneLoader";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ProtectedRoute, GuestRoute } from "@/components/ProtectedRoute";
import AnalyticsRouteTracker from "@/components/AnalyticsRouteTracker";

// Layouts — MarketingLayout stays eager (first paint for public visitors).
// The dashboard/onboarding shells are lazy so logged-out marketing visitors
// don't download the whole authenticated app chrome in main.js.
import MarketingLayout from "@/layouts/MarketingLayout";
const OnboardingLayout = lazy(() => import("@/layouts/OnboardingLayout"));
const DashboardLayout = lazy(() => import("@/layouts/DashboardLayout"));

// Home stays eager for the fastest LCP on the most-visited route
import Home from "@/pages/marketing/Home";

// Marketing — lazy
const Products = lazy(() => import("@/pages/marketing/Products"));
const MarketingProductRoute = lazy(() =>
  import("@/pages/dashboard/PlannedProduct").then((m) => ({
    default: m.MarketingProductRoute,
  })),
);
const Solutions = lazy(() => import("@/pages/marketing/Solutions"));
const IntegrationsMkt = lazy(() => import("@/pages/marketing/Integrations"));
const Templates = lazy(() => import("@/pages/marketing/Templates"));
const Pricing = lazy(() => import("@/pages/marketing/Pricing"));
const Documentation = lazy(() => import("@/pages/marketing/Documentation"));
const CaseStudies = lazy(() => import("@/pages/marketing/CaseStudies"));
const About = lazy(() => import("@/pages/marketing/About"));
const Contact = lazy(() => import("@/pages/marketing/Contact"));
const Security = lazy(() => import("@/pages/marketing/Security"));
const Privacy = lazy(() =>
  import("@/pages/legal/Legal").then((m) => ({ default: m.Privacy })),
);
const Terms = lazy(() =>
  import("@/pages/legal/Legal").then((m) => ({ default: m.Terms })),
);
const Cookie = lazy(() =>
  import("@/pages/legal/Legal").then((m) => ({ default: m.Cookie })),
);
const DataDeletion = lazy(() =>
  import("@/pages/legal/Legal").then((m) => ({ default: m.DataDeletion })),
);
const NotFound = lazy(() => import("@/pages/NotFound"));
const ServerError = lazy(() => import("@/pages/ServerError"));
const NetworkError = lazy(() =>
  import("@/pages/SystemPages").then((m) => ({ default: m.NetworkError })),
);
const Maintenance = lazy(() =>
  import("@/pages/SystemPages").then((m) => ({ default: m.Maintenance })),
);
// SEO landing pages
const AIChatAgentPage = lazy(() =>
  import("@/pages/marketing/SeoPages").then((m) => ({
    default: m.AIChatAgentPage,
  })),
);
const AILeadGenerationPage = lazy(() =>
  import("@/pages/marketing/SeoPages").then((m) => ({
    default: m.AILeadGenerationPage,
  })),
);
const AIAppointmentBookingPage = lazy(() =>
  import("@/pages/marketing/SeoPages").then((m) => ({
    default: m.AIAppointmentBookingPage,
  })),
);
const AICustomerSupportPage = lazy(() =>
  import("@/pages/marketing/SeoPages").then((m) => ({
    default: m.AICustomerSupportPage,
  })),
);

// Auth — lazy
const AuthCallback = lazy(() => import("@/pages/auth/AuthCallback"));
const Login = lazy(() => import("@/pages/auth/Login"));
const Signup = lazy(() => import("@/pages/auth/Signup"));
const VerifyEmail = lazy(() =>
  import("@/pages/auth/Recovery").then((m) => ({ default: m.VerifyEmail })),
);
const ForgotPassword = lazy(() =>
  import("@/pages/auth/Recovery").then((m) => ({ default: m.ForgotPassword })),
);
const ResetPassword = lazy(() =>
  import("@/pages/auth/Recovery").then((m) => ({ default: m.ResetPassword })),
);
const Welcome = lazy(() => import("@/pages/auth/Welcome"));

// Onboarding — lazy
const Step1Agent = lazy(() => import("@/pages/onboarding/Step1Agent"));
const Step2Business = lazy(() => import("@/pages/onboarding/Step2Business"));
const Step3Channels = lazy(() => import("@/pages/onboarding/Step3Channels"));

// Dashboard — lazy (large, only authenticated users see this)
const Overview = lazy(() => import("@/pages/dashboard/Overview"));
const ProductPortfolio = lazy(
  () => import("@/pages/dashboard/ProductPortfolio"),
);
const PlannedProductRoute = lazy(() =>
  import("@/pages/dashboard/PlannedProduct").then((m) => ({
    default: m.PlannedProductRoute,
  })),
);
const WorkspaceSearch = lazy(() => import("@/pages/dashboard/WorkspaceSearch"));
const Agents = lazy(() => import("@/pages/dashboard/Agents"));
const AgentCreate = lazy(() => import("@/pages/dashboard/AgentCreate"));
const CreateAgentWizard = lazy(
  () => import("@/pages/dashboard/CreateAgentWizard"),
);
const AgentBuilder = lazy(() => import("@/pages/dashboard/AgentBuilder"));
const Chat = lazy(() => import("@/pages/dashboard/Chat"));
const ChatProductOverview = lazy(
  () => import("@/pages/dashboard/ChatProductOverview"),
);
const KnowledgeDocuments = lazy(
  () => import("@/pages/dashboard/KnowledgeDocuments"),
);
const AgentKnowledge = lazy(() => import("@/pages/dashboard/AgentKnowledge"));
const CustomerProfile = lazy(() => import("@/pages/dashboard/CustomerProfile"));
const AgentAnalytics = lazy(() => import("@/pages/dashboard/AgentAnalytics"));
const Conversations = lazy(() => import("@/pages/dashboard/Conversations"));

const Leads = lazy(() => import("@/pages/dashboard/Leads"));
const KnowledgeBase = lazy(() => import("@/pages/dashboard/KnowledgeBase"));
const KnowledgeBaseDetails = lazy(
  () => import("@/pages/dashboard/KnowledgeBaseDetails"),
);
const Websites = lazy(() => import("@/pages/dashboard/Websites"));
const KnowledgeSearch = lazy(() => import("@/pages/dashboard/KnowledgeSearch"));
const IntegrationsDash = lazy(() => import("@/pages/dashboard/Integrations"));
const Deploy = lazy(() => import("@/pages/dashboard/Deploy"));
const Marketplace = lazy(() => import("@/pages/dashboard/Marketplace"));
const Developers = lazy(() => import("@/pages/dashboard/Developers"));
const KnowledgeCoverage = lazy(
  () => import("@/pages/dashboard/KnowledgeCoverage"),
);
const AgentQualityLab = lazy(() => import("@/pages/dashboard/AgentQualityLab"));
const AgentVersions = lazy(() => import("@/pages/dashboard/AgentVersions"));
const InviteAccept = lazy(() => import("@/pages/dashboard/InviteAccept"));
const Team = lazy(() => import("@/pages/dashboard/Team"));
const Teams = lazy(() => import("@/pages/dashboard/Teams"));
const Settings = lazy(() => import("@/pages/dashboard/Settings"));
const Analytics = lazy(() => import("@/pages/dashboard/Analytics"));
const Workflows = lazy(() => import("@/pages/dashboard/Workflows"));
const Widgets = lazy(() => import("@/pages/dashboard/Widgets"));
const OptimizationScore = lazy(
  () => import("@/pages/dashboard/OptimizationScore"),
);
const RevenueAttribution = lazy(
  () => import("@/pages/dashboard/RevenueAttribution"),
);
const Customer360 = lazy(() => import("@/pages/dashboard/Customer360"));
const Billing = lazy(() => import("@/pages/dashboard/Billing"));
const Usage = lazy(() => import("@/pages/dashboard/Usage"));
const ApiKeys = lazy(() => import("@/pages/dashboard/ApiKeys"));
const Webhooks = lazy(() => import("@/pages/dashboard/Webhooks"));
const AIModels = lazy(() => import("@/pages/dashboard/AIModels"));
const Branding = lazy(() => import("@/pages/dashboard/Branding"));
const AuditLogsPage = lazy(() => import("@/pages/dashboard/AuditLogs"));
const Operations = lazy(() => import("@/pages/dashboard/Operations"));
// R9 — Enterprise Team Collaboration
const Projects = lazy(() => import("@/pages/dashboard/Projects"));
const ActivityCenter = lazy(() => import("@/pages/dashboard/ActivityCenter"));
// Launch — product resources
const Changelog = lazy(() => import("@/pages/dashboard/Changelog"));
const Status = lazy(() => import("@/pages/dashboard/Status"));
const FeatureRequests = lazy(() => import("@/pages/dashboard/FeatureRequests"));
const GettingStarted = lazy(() => import("@/pages/dashboard/GettingStarted"));
const Guide = lazy(() => import("@/pages/dashboard/Guide"));
const Portal = lazy(() => import("@/pages/dashboard/Portal"));

// Public, unauthenticated shared conversation transcript (R1)
const SharedConversation = lazy(
  () => import("@/pages/public/SharedConversation"),
);

// Super Admin Control Center (founder/platform-admin only, own shell)
const AdminLayout = lazy(() => import("@/layouts/AdminLayout"));
const AdminDashboard = lazy(() => import("@/pages/admin/Dashboard"));
const AdminMonitoring = lazy(() => import("@/pages/admin/Monitoring"));
const AdminAnalytics = lazy(() => import("@/pages/admin/Analytics"));
const AdminInsights = lazy(() => import("@/pages/admin/Insights"));
const AdminCustomers = lazy(() => import("@/pages/admin/Customers"));
const AdminConversations = lazy(() => import("@/pages/admin/Conversations"));
const AdminBilling = lazy(() => import("@/pages/admin/Billing"));
const AdminUsage = lazy(() => import("@/pages/admin/Usage"));
const AdminSecurity = lazy(() => import("@/pages/admin/Security"));
const AdminFeatureFlags = lazy(() => import("@/pages/admin/FeatureFlags"));
const AdminProducts = lazy(() => import("@/pages/admin/Products"));
const AdminSecrets = lazy(() => import("@/pages/admin/Secrets"));
const AdminReleases = lazy(() => import("@/pages/admin/Releases"));
const AdminInfrastructure = lazy(() => import("@/pages/admin/Infrastructure"));
const AdminAuditLogs = lazy(() => import("@/pages/admin/AuditLogs"));
const AdminResourcePage = lazy(() => import("@/pages/admin/ResourcePage"));
const AdminModulePage = lazy(() => import("@/pages/admin/ModulePage"));
const AdminCostOptimization = lazy(
  () => import("@/pages/admin/CostOptimization"),
);
const AdminQuality = lazy(() => import("@/pages/admin/Quality"));
const AdminSelfImprovement = lazy(
  () => import("@/pages/admin/SelfImprovement"),
);
const AdminBenchmarking = lazy(() => import("@/pages/admin/Benchmarking"));
const AdminHealthMonitor = lazy(() => import("@/pages/admin/HealthMonitor"));
const AdminFraud = lazy(() => import("@/pages/admin/Fraud"));
const AdminCompliance = lazy(() => import("@/pages/admin/Compliance"));
const AdminTenantIsolation = lazy(
  () => import("@/pages/admin/TenantIsolation"),
);
const AdminUniversalSearch = lazy(
  () => import("@/pages/admin/UniversalSearch"),
);
const AdminOraCopilot = lazy(() => import("@/pages/admin/OraCopilot"));
const AdminReports = lazy(() => import("@/pages/admin/Reports"));

function RouteFallback() {
  return <OraOneLoader />;
}

function AgentDesignRoute({ destination = "builder" }) {
  const { id } = useParams();
  const target =
    destination === "deploy"
      ? `/app/agents/${id}/deploy`
      : destination === "chat"
        ? `/app/chat?agent=${encodeURIComponent(id)}`
        : destination === "quality" || destination === "versions"
          ? `/app/agents/${destination}?agent=${encodeURIComponent(id)}`
          : destination === "config"
            ? `/app/agents/${id}?tab=config`
            : `/app/agents/${id}`;
  return <Navigate to={target} replace />;
}

function ConversationDesignRoute() {
  const { conversationId } = useParams();
  return <Navigate to={`/app/conversations/${conversationId}`} replace />;
}

function CustomerDesignRoute() {
  return <CustomerProfile />;
}

function AdminOrganizationDesignRoute() {
  const { organizationId } = useParams();
  return (
    <Navigate
      to={`/admin/customers?customer=${encodeURIComponent(organizationId)}`}
      replace
    />
  );
}

function IntegrationDesignRoute() {
  const { integrationId } = useParams();
  return (
    <Navigate
      to={`/app/integrations?integration=${encodeURIComponent(integrationId)}`}
      replace
    />
  );
}

function AdminUserDesignRoute() {
  const { userId } = useParams();
  return <AdminResourcePage kind="users" initialQuery={userId} />;
}

function OwnerRouteBridge() {
  const { pathname, search, hash } = useLocation();
  const suffix = pathname.replace(/^\/owner\/?/, "");
  const detail = suffix.match(/^(users|organizations)\/([^/]+)$/);
  const collectionTargets = {
    "": "/admin",
    "ai-models": "/admin/ai-operations",
    audit: "/admin/audit-logs",
    billing: "/admin/billing",
    entitlements: "/admin/products",
    errors: "/admin/logs",
    "feature-flags": "/admin/feature-flags",
    infrastructure: "/admin/infrastructure",
    monitoring: "/admin/monitoring",
    organizations: "/admin/workspaces",
    products: "/admin/products",
    security: "/admin/security",
    settings: "/admin/settings",
    subscriptions: "/admin/subscriptions",
    support: "/admin/support",
    usage: "/admin/usage",
    users: "/admin/users",
  };
  const target = detail
    ? detail[1] === "users"
      ? `/admin/users/${encodeURIComponent(detail[2])}`
      : `/admin/organizations/${encodeURIComponent(detail[2])}`
    : collectionTargets[suffix] || "/admin";

  return <Navigate to={`${target}${search}${hash}`} replace />;
}

function NavigateToLeadDetail() {
  const { leadId } = useParams();
  return (
    <Navigate to={`/app/leads?lead=${encodeURIComponent(leadId)}`} replace />
  );
}

function App() {
  return (
    <div className="App">
      <MotionConfig reducedMotion="user">
        <BrowserRouter>
          <ErrorBoundary>
            <AuthProvider>
              <Toaster position="top-right" richColors closeButton />
              <AnalyticsRouteTracker />
              <Suspense fallback={<RouteFallback />}>
                <Routes>
                  {/* Marketing */}
                  <Route element={<MarketingLayout />}>
                    <Route path="/" element={<Home />} />
                    <Route path="/products" element={<Products />} />
                    <Route
                      path="/products/:productSlug"
                      element={<MarketingProductRoute />}
                    />
                    <Route
                      path="/features"
                      element={<Navigate to="/products" replace />}
                    />
                    <Route
                      path="/platform"
                      element={<Navigate to="/products" replace />}
                    />
                    <Route
                      path="/roadmap"
                      element={<Navigate to="/products" replace />}
                    />
                    <Route
                      path="/demo"
                      element={<Navigate to="/products" replace />}
                    />
                    <Route
                      path="/docs"
                      element={<Navigate to="/documentation" replace />}
                    />
                    <Route
                      path="/docs/*"
                      element={<Navigate to="/documentation" replace />}
                    />
                    <Route
                      path="/help"
                      element={<Navigate to="/documentation" replace />}
                    />
                    <Route
                      path="/help/contact"
                      element={<Navigate to="/contact" replace />}
                    />
                    <Route
                      path="/help/*"
                      element={<Navigate to="/documentation" replace />}
                    />
                    <Route
                      path="/solutions/:solutionSlug"
                      element={<Navigate to="/solutions" replace />}
                    />
                    <Route
                      path="/changelog"
                      element={<Navigate to="/products" replace />}
                    />
                    <Route
                      path="/status"
                      element={<Navigate to="/contact" replace />}
                    />
                    <Route
                      path="/acceptable-use"
                      element={<Navigate to="/terms" replace />}
                    />
                    <Route
                      path="/refund-policy"
                      element={<Navigate to="/terms" replace />}
                    />
                    <Route
                      path="/cookies"
                      element={<Navigate to="/cookie-policy" replace />}
                    />
                    <Route path="/solutions" element={<Solutions />} />
                    <Route path="/integrations" element={<IntegrationsMkt />} />
                    <Route path="/templates" element={<Templates />} />
                    <Route path="/pricing" element={<Pricing />} />
                    <Route path="/documentation" element={<Documentation />} />
                    <Route path="/case-studies" element={<CaseStudies />} />
                    <Route path="/about" element={<About />} />
                    <Route path="/contact" element={<Contact />} />
                    <Route path="/security" element={<Security />} />
                    <Route path="/privacy" element={<Privacy />} />
                    <Route path="/terms" element={<Terms />} />
                    <Route path="/cookie-policy" element={<Cookie />} />
                    <Route path="/data-deletion" element={<DataDeletion />} />
                    {/* SEO landing pages */}
                    <Route
                      path="/ai-chat-agent"
                      element={<AIChatAgentPage />}
                    />
                    <Route
                      path="/ai-lead-generation"
                      element={<AILeadGenerationPage />}
                    />
                    <Route
                      path="/ai-appointment-booking"
                      element={<AIAppointmentBookingPage />}
                    />
                    <Route
                      path="/ai-customer-support"
                      element={<AICustomerSupportPage />}
                    />
                    {/* System pages */}
                    <Route path="/500" element={<ServerError />} />
                    <Route path="/network-error" element={<NetworkError />} />
                    <Route path="/maintenance" element={<Maintenance />} />

                    <Route path="*" element={<NotFound />} />
                  </Route>

                  {/* Legacy Cognito OAuth callback route — now just redirects to /login */}
                  <Route path="/auth/callback" element={<AuthCallback />} />
                  <Route
                    path="/auth"
                    element={<Navigate to="/login" replace />}
                  />
                  <Route
                    path="/auth/error"
                    element={<Navigate to="/login?reason=auth-error" replace />}
                  />
                  <Route
                    path="/auth/mfa"
                    element={<Navigate to="/verify-email" replace />}
                  />
                  <Route
                    path="/auth/invitation"
                    element={<Navigate to="/signup" replace />}
                  />
                  <Route
                    path="/auth/*"
                    element={<Navigate to="/login" replace />}
                  />

                  {/* Design-system auth URLs retained as compatibility aliases. */}
                  <Route
                    path="/auth/sign-in"
                    element={<Navigate to="/login" replace />}
                  />
                  <Route
                    path="/auth/sign-up"
                    element={<Navigate to="/signup" replace />}
                  />
                  <Route
                    path="/auth/verify-email"
                    element={<Navigate to="/verify-email" replace />}
                  />
                  <Route
                    path="/auth/forgot-password"
                    element={<Navigate to="/forgot-password" replace />}
                  />
                  <Route
                    path="/auth/reset-password"
                    element={<Navigate to="/reset-password" replace />}
                  />
                  <Route
                    path="/auth/session-expired"
                    element={
                      <Navigate to="/login?reason=session-expired" replace />
                    }
                  />

                  {/* Public shared conversation transcript (R1) — no auth, no layout */}
                  <Route
                    path="/share/:token"
                    element={<SharedConversation />}
                  />

                  {/* Auth — standalone split-screen pages (each renders its own shell) */}
                  {/* Guest-only: signed-in users are bounced to the dashboard. */}
                  <Route
                    path="/login"
                    element={
                      <GuestRoute>
                        <Login />
                      </GuestRoute>
                    }
                  />
                  <Route
                    path="/signup"
                    element={
                      <GuestRoute>
                        <Signup />
                      </GuestRoute>
                    }
                  />
                  <Route path="/verify-email" element={<VerifyEmail />} />
                  <Route path="/verification" element={<VerifyEmail />} />
                  <Route
                    path="/verification/*"
                    element={<Navigate to="/verify-email" replace />}
                  />
                  <Route
                    path="/forgot-password"
                    element={
                      <GuestRoute>
                        <ForgotPassword />
                      </GuestRoute>
                    }
                  />
                  <Route
                    path="/reset-password"
                    element={
                      <GuestRoute>
                        <ResetPassword />
                      </GuestRoute>
                    }
                  />
                  <Route
                    path="/welcome"
                    element={
                      <ProtectedRoute>
                        <Welcome />
                      </ProtectedRoute>
                    }
                  />

                  {/* Onboarding (requires a signed-in account) */}
                  <Route
                    element={
                      <ProtectedRoute>
                        <OnboardingLayout />
                      </ProtectedRoute>
                    }
                  >
                    <Route
                      path="/onboarding"
                      element={<Navigate to="/onboarding/agent" replace />}
                    />
                    <Route path="/onboarding/agent" element={<Step1Agent />} />
                    <Route
                      path="/onboarding/ai-chat"
                      element={<Step1Agent />}
                    />
                    <Route
                      path="/onboarding/use-case"
                      element={<Step1Agent />}
                    />
                    <Route
                      path="/onboarding/business"
                      element={<Step2Business />}
                    />
                    <Route
                      path="/onboarding/profile"
                      element={<Step2Business />}
                    />
                    <Route
                      path="/onboarding/workspace"
                      element={<Step2Business />}
                    />
                    <Route
                      path="/onboarding/channels"
                      element={<Step3Channels />}
                    />
                    <Route
                      path="/onboarding/knowledge"
                      element={<Step3Channels />}
                    />
                    <Route
                      path="/onboarding/install"
                      element={<Step3Channels />}
                    />
                    <Route
                      path="/onboarding/test"
                      element={<Step3Channels />}
                    />
                    <Route path="/onboarding/complete" element={<Welcome />} />
                  </Route>

                  {/* Dashboard (protected) — simplified, grouped information architecture.
                  Related pages are grouped under a section root and surfaced as
                  tabs (see @/constants/navigation). Old flat routes are kept as
                  redirects below for 100% backward compatibility. */}
                  <Route element={<DashboardLayout />}>
                    <Route
                      path="/app"
                      element={<Navigate to="/app/dashboard" replace />}
                    />
                    <Route path="/app/dashboard" element={<Overview />} />
                    <Route
                      path="/app/products"
                      element={<ProductPortfolio />}
                    />
                    <Route
                      path="/app/products/:productSlug/*"
                      element={<PlannedProductRoute />}
                    />
                    <Route
                      path="/studio/*"
                      element={
                        <PlannedProductRoute defaultProductSlug="ai-studio" />
                      }
                    />
                    <Route path="/app/search" element={<WorkspaceSearch />} />
                    <Route
                      path="/app/analytics/customer-360"
                      element={<Navigate to="/app/customer-360" replace />}
                    />
                    <Route
                      path="/app/analytics/optimization"
                      element={
                        <Navigate to="/app/optimization-score" replace />
                      }
                    />
                    <Route
                      path="/app/analytics/revenue"
                      element={
                        <Navigate to="/app/revenue-attribution" replace />
                      }
                    />
                    <Route
                      path="/app/account"
                      element={<Navigate to="/app/settings" replace />}
                    />
                    <Route path="/app/account/profile" element={<Settings />} />
                    <Route
                      path="/app/account/preferences"
                      element={<Settings />}
                    />
                    <Route
                      path="/app/account/notifications"
                      element={<Settings />}
                    />
                    <Route
                      path="/app/account/security"
                      element={<Settings />}
                    />
                    <Route
                      path="/app/account/sessions"
                      element={<Settings />}
                    />
                    <Route
                      path="/app/account/*"
                      element={<Navigate to="/app/settings" replace />}
                    />
                    <Route
                      path="/app/settings/general"
                      element={<Settings />}
                    />
                    <Route
                      path="/app/settings/notifications"
                      element={<Settings />}
                    />
                    <Route
                      path="/app/settings/security"
                      element={<Settings />}
                    />
                    <Route
                      path="/app/settings/tasks"
                      element={<Navigate to="/app/activity" replace />}
                    />
                    <Route
                      path="/app/settings/teams"
                      element={<Navigate to="/app/teams" replace />}
                    />
                    <Route path="/app/settings/data" element={<Settings />} />
                    <Route
                      path="/app/team/activity"
                      element={<ActivityCenter defaultTab="activity" />}
                    />
                    <Route path="/app/team/invitations" element={<Team />} />
                    <Route path="/app/team/members" element={<Team />} />
                    <Route path="/app/team/permissions" element={<Team />} />
                    <Route path="/app/team/roles" element={<Team />} />
                    <Route
                      path="/app/workspaces"
                      element={<Navigate to="/app/projects" replace />}
                    />
                    <Route
                      path="/app/workspaces/new"
                      element={<Navigate to="/app/projects" replace />}
                    />
                    <Route
                      path="/app/workspaces/:workspaceId"
                      element={<Navigate to="/app/projects" replace />}
                    />
                    <Route
                      path="/app/workspaces/:workspaceId/settings"
                      element={<Navigate to="/app/projects" replace />}
                    />
                    <Route
                      path="/app/overview"
                      element={<Navigate to="/app/dashboard" replace />}
                    />

                    {/* Imported design-route compatibility for Product 1. */}
                    <Route
                      path="/app/inbox"
                      element={<Navigate to="/app/conversations" replace />}
                    />
                    <Route
                      path="/app/inbox/:conversationId"
                      element={<ConversationDesignRoute />}
                    />
                    <Route
                      path="/app/customers"
                      element={<Navigate to="/app/leads" replace />}
                    />
                    <Route
                      path="/app/customers/:customerId"
                      element={<CustomerDesignRoute />}
                    />
                    <Route
                      path="/app/products/chat"
                      element={<ChatProductOverview />}
                    />
                    <Route
                      path="/app/products/chat/analytics"
                      element={<Navigate to="/app/analytics" replace />}
                    />
                    <Route
                      path="/app/products/chat/assistants"
                      element={<Navigate to="/app/agents" replace />}
                    />
                    <Route
                      path="/app/products/chat/assistants/new"
                      element={<Navigate to="/app/agents/new" replace />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id"
                      element={<AgentDesignRoute />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id/editor"
                      element={<AgentDesignRoute destination="config" />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id/behavior"
                      element={<AgentDesignRoute destination="config" />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id/knowledge"
                      element={<AgentKnowledge />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id/analytics"
                      element={<AgentAnalytics />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id/quality"
                      element={<AgentDesignRoute destination="quality" />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id/versions"
                      element={<AgentDesignRoute destination="versions" />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id/install"
                      element={<AgentDesignRoute destination="deploy" />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id/widget"
                      element={<AgentDesignRoute destination="deploy" />}
                    />
                    <Route
                      path="/app/products/chat/assistants/:id/playground"
                      element={<AgentDesignRoute destination="chat" />}
                    />
                    <Route
                      path="/app/products/chat/conversations"
                      element={<Navigate to="/app/conversations" replace />}
                    />
                    <Route
                      path="/app/products/chat/knowledge"
                      element={<Navigate to="/app/knowledge-base" replace />}
                    />
                    <Route
                      path="/app/products/chat/knowledge/documents"
                      element={<KnowledgeDocuments />}
                    />
                    <Route
                      path="/app/products/chat/knowledge/websites"
                      element={
                        <Navigate to="/app/knowledge-base/websites" replace />
                      }
                    />
                    <Route
                      path="/app/products/chat/knowledge/search"
                      element={
                        <Navigate to="/app/knowledge-base/search" replace />
                      }
                    />
                    <Route
                      path="/app/products/chat/knowledge/coverage"
                      element={
                        <Navigate to="/app/knowledge-base/coverage" replace />
                      }
                    />
                    <Route
                      path="/app/products/chat/settings"
                      element={<Navigate to="/app/settings" replace />}
                    />
                    <Route
                      path="/app/products/chat/templates"
                      element={<Navigate to="/app/agents/templates" replace />}
                    />
                    <Route
                      path="/app/products/chat/assistants/demo/instructions"
                      element={<Navigate to="/app/agents" replace />}
                    />
                    <Route
                      path="/app/products/chat/assistants/demo/models"
                      element={<Navigate to="/app/ai-models" replace />}
                    />
                    <Route
                      path="/app/products/chat/assistants/demo/settings"
                      element={<Navigate to="/app/settings" replace />}
                    />

                    {/* Design-system account and workspace aliases. */}
                    <Route
                      path="/app/account/*"
                      element={<Navigate to="/app/settings" replace />}
                    />
                    <Route
                      path="/app/billing/usage"
                      element={<Navigate to="/app/usage" replace />}
                    />
                    <Route
                      path="/app/billing/*"
                      element={<Navigate to="/app/billing" replace />}
                    />
                    <Route
                      path="/app/integrations/catalog"
                      element={<Navigate to="/app/integrations" replace />}
                    />
                    <Route
                      path="/app/integrations/connected"
                      element={<Navigate to="/app/integrations" replace />}
                    />
                    <Route
                      path="/app/integrations/webhooks"
                      element={<Navigate to="/app/webhooks" replace />}
                    />
                    <Route
                      path="/app/integrations/:integrationId"
                      element={<IntegrationDesignRoute />}
                    />
                    <Route
                      path="/app/leads/:leadId"
                      element={<NavigateToLeadDetail />}
                    />
                    <Route
                      path="/app/settings/api-keys"
                      element={<Navigate to="/app/api-keys" replace />}
                    />
                    <Route
                      path="/app/settings/audit"
                      element={<Navigate to="/app/audit-logs" replace />}
                    />
                    <Route
                      path="/app/settings/billing"
                      element={<Navigate to="/app/billing" replace />}
                    />
                    <Route
                      path="/app/settings/branding"
                      element={<Navigate to="/app/branding" replace />}
                    />
                    <Route
                      path="/app/settings/developers"
                      element={<Navigate to="/app/developers" replace />}
                    />
                    <Route
                      path="/app/settings/members"
                      element={<Navigate to="/app/team" replace />}
                    />
                    <Route
                      path="/app/settings/models"
                      element={<Navigate to="/app/ai-models" replace />}
                    />
                    <Route
                      path="/app/settings/operations"
                      element={<Navigate to="/app/operations" replace />}
                    />
                    <Route
                      path="/app/settings/projects"
                      element={<Navigate to="/app/projects" replace />}
                    />
                    <Route
                      path="/app/settings/webhooks"
                      element={<Navigate to="/app/webhooks" replace />}
                    />
                    <Route
                      path="/app/team/*"
                      element={<Navigate to="/app/team" replace />}
                    />
                    <Route
                      path="/app/workspaces/*"
                      element={<Navigate to="/app/projects" replace />}
                    />

                    {/* ── AI Agents ── */}
                    <Route
                      path="/app/create-agent"
                      element={<CreateAgentWizard />}
                    />
                    <Route path="/app/agents" element={<Agents />} />
                    <Route path="/app/agents/new" element={<AgentCreate />} />
                    <Route
                      path="/app/agents/templates"
                      element={<Marketplace />}
                    />
                    <Route
                      path="/app/agents/assistants"
                      element={<Navigate to="/app/agents" replace />}
                    />
                    <Route
                      path="/app/agents/versions"
                      element={<AgentVersions />}
                    />
                    <Route
                      path="/app/agents/quality"
                      element={<AgentQualityLab />}
                    />
                    <Route path="/app/agents/:id" element={<AgentBuilder />} />
                    <Route path="/app/agents/:id/deploy" element={<Deploy />} />

                    {/* ── Conversations ── */}
                    <Route path="/app/chat" element={<Chat />} />
                    <Route
                      path="/app/chat/:conversationId"
                      element={<Chat />}
                    />
                    <Route
                      path="/app/conversations"
                      element={<Conversations />}
                    />
                    <Route
                      path="/app/conversations/:conversationId"
                      element={<Conversations />}
                    />

                    {/* ── Knowledge ── */}
                    <Route
                      path="/app/knowledge-base"
                      element={<KnowledgeBase />}
                    />
                    <Route
                      path="/app/knowledge-base/websites"
                      element={<Websites />}
                    />
                    <Route
                      path="/app/knowledge-base/search"
                      element={<KnowledgeSearch />}
                    />
                    <Route
                      path="/app/knowledge-base/coverage"
                      element={<KnowledgeCoverage />}
                    />
                    <Route
                      path="/app/knowledge-base/:id"
                      element={<KnowledgeBaseDetails />}
                    />

                    {/* ── Integrations ── */}
                    <Route
                      path="/app/integrations"
                      element={<IntegrationsDash />}
                    />

                    {/* ── Leads / CRM (entitlement-gated in nav) ── */}
                    <Route path="/app/leads" element={<Leads />} />
                    <Route path="/app/contacts" element={<Leads />} />

                    {/* Automation has no page component yet — keep disabled.
                    Analytics and Settings are real, fully-backed pages. */}
                    <Route path="/app/analytics" element={<Analytics />} />
                    <Route
                      path="/app/analytics/*"
                      element={<Navigate to="/app/analytics" replace />}
                    />
                    <Route
                      path="/app/automation/*"
                      element={
                        <Navigate to="/app/products/automation" replace />
                      }
                    />
                    <Route path="/app/settings" element={<Settings />} />
                    <Route
                      path="/app/settings/*"
                      element={<Navigate to="/app/settings" replace />}
                    />

                    {/* Projects kept canonical for the create-project flow + switcher */}
                    <Route path="/app/projects" element={<Projects />} />

                    {/* Activity & notifications (opened from the bell / profile menu) */}
                    <Route
                      path="/app/activity"
                      element={<ActivityCenter defaultTab="activity" />}
                    />
                    <Route
                      path="/app/notifications"
                      element={<ActivityCenter defaultTab="notifications" />}
                    />

                    {/* Invitations */}
                    <Route
                      path="/app/invite/:token"
                      element={<InviteAccept />}
                    />

                    {/* Product resources (surfaced from the profile menu) */}
                    <Route
                      path="/app/getting-started"
                      element={<GettingStarted />}
                    />
                    <Route path="/app/guide" element={<Guide />} />
                    <Route path="/app/portal" element={<Portal />} />
                    <Route path="/app/changelog" element={<Changelog />} />
                    <Route path="/app/status" element={<Status />} />
                    <Route path="/app/tickets" element={<FeatureRequests />} />
                    <Route
                      path="/app/feature-requests"
                      element={<Navigate to="/app/tickets" replace />}
                    />

                    {/* ── Backward-compatible redirects: old flat routes → new grouped homes ── */}
                    <Route
                      path="/app/marketplace"
                      element={<Navigate to="/app/agents/templates" replace />}
                    />
                    <Route
                      path="/app/assistants"
                      element={<Navigate to="/app/agents" replace />}
                    />
                    <Route
                      path="/app/agent-versions"
                      element={<Navigate to="/app/agents/versions" replace />}
                    />
                    <Route
                      path="/app/quality-lab"
                      element={<Navigate to="/app/agents/quality" replace />}
                    />
                    <Route
                      path="/app/websites"
                      element={
                        <Navigate to="/app/knowledge-base/websites" replace />
                      }
                    />
                    <Route
                      path="/app/knowledge-search"
                      element={
                        <Navigate to="/app/knowledge-base/search" replace />
                      }
                    />
                    <Route
                      path="/app/knowledge-coverage"
                      element={
                        <Navigate to="/app/knowledge-base/coverage" replace />
                      }
                    />
                    {/* Removed sections (Workflows / Analytics / Settings) → dashboard */}
                    <Route path="/app/workflows" element={<Workflows />} />
                    <Route
                      path="/app/deploy"
                      element={<Navigate to="/app/dashboard" replace />}
                    />
                    <Route path="/app/widgets" element={<Widgets />} />
                    <Route
                      path="/app/optimization-score"
                      element={<OptimizationScore />}
                    />
                    <Route
                      path="/app/revenue-attribution"
                      element={<RevenueAttribution />}
                    />
                    <Route path="/app/customer-360" element={<Customer360 />} />
                    <Route path="/app/billing" element={<Billing />} />
                    <Route path="/app/usage" element={<Usage />} />
                    <Route path="/app/api-keys" element={<ApiKeys />} />
                    <Route path="/app/webhooks" element={<Webhooks />} />
                    <Route path="/app/developers" element={<Developers />} />
                    <Route path="/app/ai-models" element={<AIModels />} />
                    <Route path="/app/branding" element={<Branding />} />
                    <Route path="/app/audit-logs" element={<AuditLogsPage />} />
                    <Route path="/app/operations" element={<Operations />} />
                    <Route path="/app/team" element={<Team />} />
                    <Route
                      path="/app/workspace"
                      element={<Navigate to="/app/dashboard" replace />}
                    />
                    <Route path="/app/teams" element={<Teams />} />
                    <Route
                      path="/app/tasks"
                      element={<Navigate to="/app/dashboard" replace />}
                    />

                    {/* protected aliases */}
                    <Route
                      path="/dashboard"
                      element={<Navigate to="/app/dashboard" replace />}
                    />
                    <Route
                      path="/dashboard/*"
                      element={<Navigate to="/app/dashboard" replace />}
                    />
                    <Route
                      path="/agents"
                      element={<Navigate to="/app/agents" replace />}
                    />
                    <Route
                      path="/agents/*"
                      element={<Navigate to="/app/agents" replace />}
                    />
                    <Route
                      path="/settings"
                      element={<Navigate to="/app/settings" replace />}
                    />
                    <Route
                      path="/settings/*"
                      element={<Navigate to="/app/settings" replace />}
                    />
                    <Route
                      path="/analytics"
                      element={<Navigate to="/app/analytics" replace />}
                    />
                    <Route
                      path="/analytics/*"
                      element={<Navigate to="/app/analytics" replace />}
                    />
                  </Route>

                  {/* Super Admin Control Center — founder/platform-admin only.
                  AdminLayout wraps ProtectedRoute + access gate internally. */}
                  <Route element={<AdminLayout />}>
                    <Route path="/admin" element={<AdminDashboard />} />
                    <Route
                      path="/admin/ai-models"
                      element={<Navigate to="/admin/ai-operations" replace />}
                    />
                    <Route
                      path="/admin/audit"
                      element={<Navigate to="/admin/audit-logs" replace />}
                    />
                    <Route
                      path="/admin/errors"
                      element={<Navigate to="/admin/logs" replace />}
                    />
                    <Route
                      path="/admin/organizations"
                      element={<Navigate to="/admin/workspaces" replace />}
                    />
                    <Route
                      path="/admin/organizations/:organizationId"
                      element={<AdminOrganizationDesignRoute />}
                    />
                    <Route
                      path="/admin/users"
                      element={<AdminResourcePage kind="users" />}
                    />
                    <Route
                      path="/admin/users/:userId"
                      element={<AdminUserDesignRoute />}
                    />
                    <Route
                      path="/admin/search"
                      element={<AdminUniversalSearch />}
                    />
                    <Route
                      path="/admin/copilot"
                      element={<AdminOraCopilot />}
                    />
                    <Route path="/admin/reports" element={<AdminReports />} />
                    <Route
                      path="/admin/monitoring"
                      element={<AdminMonitoring />}
                    />
                    <Route
                      path="/admin/analytics"
                      element={<AdminAnalytics />}
                    />
                    <Route path="/admin/insights" element={<AdminInsights />} />

                    <Route
                      path="/admin/customers"
                      element={<AdminCustomers />}
                    />
                    <Route
                      path="/admin/workspaces"
                      element={<AdminResourcePage kind="workspaces" />}
                    />
                    <Route
                      path="/admin/conversations"
                      element={<AdminConversations />}
                    />
                    <Route
                      path="/admin/leads"
                      element={<AdminResourcePage kind="leads" />}
                    />
                    <Route
                      path="/admin/support"
                      element={<AdminModulePage moduleKey="support" />}
                    />

                    <Route
                      path="/admin/agents"
                      element={<AdminResourcePage kind="agents" />}
                    />
                    <Route
                      path="/admin/knowledge"
                      element={<AdminResourcePage kind="knowledge" />}
                    />
                    <Route
                      path="/admin/workflows"
                      element={<AdminResourcePage kind="workflows" />}
                    />
                    <Route
                      path="/admin/channels"
                      element={<AdminResourcePage kind="channels" />}
                    />

                    <Route
                      path="/admin/billing"
                      element={<AdminBilling variant="billing" />}
                    />
                    <Route
                      path="/admin/subscriptions"
                      element={<AdminBilling variant="subscriptions" />}
                    />
                    <Route path="/admin/usage" element={<AdminUsage />} />

                    <Route
                      path="/admin/cost"
                      element={<AdminCostOptimization />}
                    />
                    <Route path="/admin/quality" element={<AdminQuality />} />
                    <Route
                      path="/admin/self-improvement"
                      element={<AdminSelfImprovement />}
                    />
                    <Route
                      path="/admin/benchmarking"
                      element={<AdminBenchmarking />}
                    />
                    <Route
                      path="/admin/health"
                      element={<AdminHealthMonitor />}
                    />

                    <Route
                      path="/admin/integrations"
                      element={<AdminResourcePage kind="integrations" />}
                    />
                    <Route
                      path="/admin/api-keys"
                      element={<AdminResourcePage kind="api_keys" />}
                    />
                    <Route
                      path="/admin/infrastructure"
                      element={<AdminInfrastructure />}
                    />
                    <Route path="/admin/products" element={<AdminProducts />} />
                    <Route
                      path="/admin/databases"
                      element={<AdminModulePage moduleKey="databases" />}
                    />
                    <Route
                      path="/admin/queues"
                      element={<AdminModulePage moduleKey="queues" />}
                    />

                    <Route
                      path="/admin/deployments"
                      element={<AdminReleases variant="deployments" />}
                    />
                    <Route
                      path="/admin/releases"
                      element={<AdminReleases variant="releases" />}
                    />
                    <Route
                      path="/admin/feature-flags"
                      element={<AdminFeatureFlags />}
                    />

                    <Route
                      path="/admin/logs"
                      element={<AdminAuditLogs variant="logs" />}
                    />
                    <Route
                      path="/admin/audit-logs"
                      element={<AdminAuditLogs variant="audit" />}
                    />
                    <Route
                      path="/admin/alerts"
                      element={<AdminModulePage moduleKey="alerts" />}
                    />

                    <Route path="/admin/security" element={<AdminSecurity />} />
                    <Route path="/admin/secrets" element={<AdminSecrets />} />
                    <Route path="/admin/fraud" element={<AdminFraud />} />
                    <Route
                      path="/admin/compliance"
                      element={<AdminCompliance />}
                    />
                    <Route
                      path="/admin/tenant-isolation"
                      element={<AdminTenantIsolation />}
                    />
                    <Route
                      path="/admin/ai-operations"
                      element={<AdminModulePage moduleKey="ai-operations" />}
                    />

                    <Route
                      path="/admin/backups"
                      element={<AdminModulePage moduleKey="backups" />}
                    />
                    <Route
                      path="/admin/disaster-recovery"
                      element={
                        <AdminModulePage moduleKey="disaster-recovery" />
                      }
                    />
                    <Route
                      path="/admin/settings"
                      element={<AdminModulePage moduleKey="settings" />}
                    />
                    <Route
                      path="/admin/developer"
                      element={<AdminModulePage moduleKey="developer" />}
                    />
                    <Route path="/owner/*" element={<OwnerRouteBridge />} />
                  </Route>
                </Routes>
              </Suspense>
            </AuthProvider>
          </ErrorBoundary>
        </BrowserRouter>
      </MotionConfig>
    </div>
  );
}

export default App;
