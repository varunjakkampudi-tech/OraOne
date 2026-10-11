import {
  LayoutDashboard, Users, Building2, Bot, MessagesSquare, Target, BookOpen,
  Workflow, Rocket, Share2, CreditCard, Repeat, Gauge, Plug, KeyRound,
  Server, Database, ListTree, ScrollText, Activity, BellRing, ShieldCheck,
  Flag, GitBranch, FileClock, LifeBuoy, BarChart3, Archive, HardDriveDownload,
  Settings, TerminalSquare, Lock, BrainCircuit, Sparkles,
  DollarSign, Award, Lightbulb, TrendingUp, HeartPulse, ShieldAlert,
  FileCheck, Network, Search, Wand2, FileBarChart2, Boxes,
} from "lucide-react";

// Canonical Super Admin navigation. Each item declares how its page is
// rendered: "real" (bespoke page), "resource" (generic cross-tenant list via
// /resources/{kind}), or "module" (structured operational page).
export const ADMIN_NAV = [
  {
    group: "Overview",
    items: [
      { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
      { to: "/admin/search", label: "Universal Search", icon: Search },
      { to: "/admin/copilot", label: "Ora Copilot", icon: Wand2 },
      { to: "/admin/reports", label: "AI Reports", icon: FileBarChart2 },
      { to: "/admin/monitoring", label: "Monitoring", icon: Activity },
      { to: "/admin/analytics", label: "Analytics", icon: BarChart3 },
      { to: "/admin/insights", label: "Founder Insights", icon: Sparkles },
    ],
  },
  {
    group: "Customers",
    items: [
      { to: "/admin/customers", label: "Customers", icon: Users },
      { to: "/admin/workspaces", label: "Workspaces", icon: Building2 },
      { to: "/admin/conversations", label: "Conversations", icon: MessagesSquare },
      { to: "/admin/leads", label: "Leads", icon: Target },
      { to: "/admin/support", label: "Support", icon: LifeBuoy },
    ],
  },
  {
    group: "Product",
    items: [
      { to: "/admin/agents", label: "AI Agents", icon: Bot },
      { to: "/admin/knowledge", label: "Knowledge", icon: BookOpen },
      { to: "/admin/workflows", label: "Workflows", icon: Workflow },
      { to: "/admin/channels", label: "Channels", icon: Share2 },
    ],
  },
  {
    group: "Revenue",
    items: [
      { to: "/admin/billing", label: "Billing", icon: CreditCard },
      { to: "/admin/subscriptions", label: "Subscriptions", icon: Repeat },
      { to: "/admin/usage", label: "Usage", icon: Gauge },
      { to: "/admin/integrations", label: "Integrations", icon: Plug },
      { to: "/admin/api-keys", label: "API Keys", icon: KeyRound },
    ],
  },
  {
    group: "Intelligence",
    items: [
      { to: "/admin/cost", label: "Cost Optimization", icon: DollarSign },
      { to: "/admin/quality", label: "Quality Monitoring", icon: Award },
      { to: "/admin/self-improvement", label: "Self-Improvement", icon: Lightbulb },
      { to: "/admin/benchmarking", label: "Benchmarking", icon: TrendingUp },
      { to: "/admin/health", label: "Health Monitor", icon: HeartPulse },
    ],
  },
  {
    group: "Platform",
    items: [
      { to: "/admin/products", label: "Products", icon: Boxes },
      { to: "/admin/infrastructure", label: "Infrastructure", icon: Server },
      { to: "/admin/databases", label: "Databases", icon: Database },
      { to: "/admin/queues", label: "Queues", icon: ListTree },
      { to: "/admin/deployments", label: "Deployments", icon: Rocket },
      { to: "/admin/releases", label: "Releases", icon: GitBranch },
      { to: "/admin/feature-flags", label: "Feature Flags", icon: Flag },
    ],
  },
  {
    group: "Observability",
    items: [
      { to: "/admin/logs", label: "Logs", icon: ScrollText },
      { to: "/admin/audit-logs", label: "Audit Logs", icon: FileClock },
      { to: "/admin/alerts", label: "Alerts", icon: BellRing },
    ],
  },
  {
    group: "Security",
    items: [
      { to: "/admin/security", label: "Security", icon: ShieldCheck },
      { to: "/admin/fraud", label: "Fraud Detection", icon: ShieldAlert },
      { to: "/admin/compliance", label: "Compliance", icon: FileCheck },
      { to: "/admin/tenant-isolation", label: "Tenant Isolation", icon: Network },
      { to: "/admin/secrets", label: "Secrets", icon: Lock },
      { to: "/admin/ai-operations", label: "AI Operations", icon: BrainCircuit },
    ],
  },
  {
    group: "Reliability",
    items: [
      { to: "/admin/backups", label: "Backups", icon: Archive },
      { to: "/admin/disaster-recovery", label: "Disaster Recovery", icon: HardDriveDownload },
    ],
  },
  {
    group: "System",
    items: [
      { to: "/admin/settings", label: "System Settings", icon: Settings },
      { to: "/admin/developer", label: "Developer Console", icon: TerminalSquare },
    ],
  },
];

// Flat list for the command palette / global search.
export const ADMIN_NAV_FLAT = ADMIN_NAV.flatMap((g) =>
  g.items.map((it) => ({ ...it, group: g.group }))
);
