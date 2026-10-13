// ─────────────────────────────────────────────────────────────────────────────
// Single source of truth for the authenticated app's information architecture.
//
// Both the Sidebar (primary nav) and the TopBar (section tab bars) read from
// this file, so navigation stays consistent and is trivial to extend when a new
// product ships. Nothing here fetches data or holds state — it is pure config,
// which keeps the navigation surfaces dumb and testable (SRP).
//
// Product/feature gating is expressed declaratively via `product` / `feature`
// keys that map to the entitlement engine (see `@/lib/entitlements`). The
// backend remains the authoritative, fail-closed authority; this only decides
// what to *show*.
// ─────────────────────────────────────────────────────────────────────────────
import {
  LayoutDashboard,
  MessagesSquare,
  Plug,
  Users,
  ChartNoAxesCombined,
  MessageSquare,
  Mic,
  Phone,
  Mail,
  Workflow,
  Lightbulb,
  CreditCard,
  Settings,
} from "lucide-react";
import { DASH } from "@/constants/testIds";

// Grouped sidebar navigation — the single source of truth for the primary nav.
// Each group may carry a `label` rendered as a small section header. Items are
// gated declaratively via `product`/`feature`; future products remain real
// preview links and use a truthful `Planned` label until their services ship.
export const NAV_GROUPS = [
  {
    items: [
      {
        to: "/app/dashboard",
        icon: LayoutDashboard,
        label: "Overview",
        id: DASH.sidebarOverview,
        end: true,
      },
      {
        to: "/app/conversations",
        icon: MessagesSquare,
        label: "Unified Inbox",
        id: DASH.sidebarConversations,
      },
      {
        to: "/app/leads",
        icon: Users,
        label: "Customers & Leads",
        id: DASH.sidebarLeads,
      },
      {
        to: "/app/analytics",
        icon: ChartNoAxesCombined,
        label: "Analytics",
        id: DASH.sidebarAnalytics,
      },
    ],
  },
  {
    label: "AI Products",
    items: [
      {
        to: "/app/products/chat",
        icon: MessageSquare,
        label: "AI Chat",
        id: DASH.sidebarChat,
        activePaths: [
          "/app/products/chat",
          "/app/agents",
          "/app/knowledge-base",
          "/app/widgets",
        ],
        children: [
          {
            to: "/app/products/chat",
            label: "Overview",
            end: true,
            activePaths: ["/app/products/chat"],
          },
          {
            to: "/app/products/chat/assistants",
            label: "Agents",
            id: DASH.sidebarAgents,
            activePaths: ["/app/products/chat/assistants", "/app/agents"],
          },
          {
            to: "/app/products/chat/knowledge",
            label: "Knowledge",
            id: DASH.sidebarKnowledge,
            activePaths: [
              "/app/products/chat/knowledge",
              "/app/knowledge-base",
            ],
          },
          {
            to: "/app/widgets",
            label: "Widget",
            id: "nav-widgets",
            activePaths: ["/app/widgets"],
          },
          {
            to: "/app/products/chat/conversations",
            label: "Conversations",
            id: DASH.sidebarConversations,
            activePaths: ["/app/products/chat/conversations"],
          },
        ],
      },
      {
        to: "/app/products/voice",
        icon: Mic,
        label: "AI Voice",
        id: "nav-product-voice",
        badge: "Planned",
      },
      {
        to: "/app/products/whatsapp",
        icon: Phone,
        label: "WhatsApp",
        id: "nav-product-whatsapp",
        badge: "Planned",
      },
      {
        to: "/app/products/omnichannel",
        icon: Mail,
        label: "Omnichannel",
        id: "nav-product-omnichannel",
        badge: "Planned",
      },
      {
        to: "/app/products/automation",
        icon: Workflow,
        label: "Automation",
        id: "nav-product-automation",
        badge: "Planned",
      },
      {
        to: "/app/products/ai-studio",
        icon: Lightbulb,
        label: "AI Studio",
        id: "nav-product-ai-studio",
        badge: "Planned",
      },
    ],
  },
  {
    label: "Management",
    items: [
      {
        to: "/app/integrations",
        icon: Plug,
        label: "Integrations",
        id: DASH.sidebarIntegrations,
      },
      {
        to: "/app/team",
        icon: Users,
        label: "Team & Access",
        id: "nav-team",
      },
      {
        to: "/app/usage",
        icon: CreditCard,
        label: "Free access & Usage",
        id: "nav-usage",
      },
      {
        to: "/app/settings",
        icon: Settings,
        label: "Workspace Settings",
        id: "nav-settings",
      },
    ],
  },
];

// Flat list of navigable (non-disabled) destinations — used for tab-title
// resolution and simple lookups. Derived from NAV_GROUPS so it never drifts.
export const PRIMARY_NAV = NAV_GROUPS.flatMap((g) =>
  g.items.flatMap((item) => [item, ...(item.children || [])]),
).filter((i) => !i.disabled);

// Retained for back-compat with importers; the sidebar now renders NAV_GROUPS.
export const SECONDARY_NAV = [];

// Section tab bars. Keyed by the section root. When the active route lives
// inside a section, the TopBar renders these as horizontal tabs — turning what
// used to be a dozen separate sidebar items into a single, focused surface.
// `end: true` marks the index tab (active only on an exact match).
export const SECTIONS = {
  "/app/agents": {
    label: "AI Assistants",
    tabs: [
      { to: "/app/agents", label: "Overview", end: true },
      {
        to: "/app/agents/templates",
        label: "Templates",
        feature: "marketplace",
      },
    ],
  },
  "/app/knowledge-base": {
    label: "Knowledge",
    tabs: [
      {
        to: "/app/knowledge-base",
        label: "Overview",
        end: true,
        activePaths: ["/app/knowledge-base"],
      },
      {
        to: "/app/products/chat/knowledge/documents",
        label: "Documents",
        activePaths: ["/app/products/chat/knowledge/documents"],
      },
      {
        to: "/app/knowledge-base/websites",
        label: "Websites",
        activePaths: [
          "/app/knowledge-base/websites",
          "/app/products/chat/knowledge/websites",
        ],
      },
      {
        to: "/app/knowledge-base/search",
        label: "Search",
        activePaths: [
          "/app/knowledge-base/search",
          "/app/products/chat/knowledge/search",
        ],
      },
      {
        to: "/app/knowledge-base/coverage",
        label: "Coverage",
        activePaths: [
          "/app/knowledge-base/coverage",
          "/app/products/chat/knowledge/coverage",
        ],
      },
    ],
  },
};

const ASSISTANT_ROUTE_SEGMENTS = new Set([
  "new",
  "templates",
  "assistants",
  "versions",
  "quality",
]);

function getAssistantId(pathname, search = "") {
  const designMatch = pathname.match(
    /^\/app\/products\/chat\/assistants\/([^/]+)/,
  );
  if (designMatch && !ASSISTANT_ROUTE_SEGMENTS.has(designMatch[1])) {
    return designMatch[1];
  }

  const canonicalMatch = pathname.match(/^\/app\/agents\/([^/]+)/);
  if (canonicalMatch && !ASSISTANT_ROUTE_SEGMENTS.has(canonicalMatch[1])) {
    return canonicalMatch[1];
  }

  if (
    pathname === "/app/agents/versions" ||
    pathname === "/app/agents/quality"
  ) {
    return new URLSearchParams(search).get("agent")?.trim() || "";
  }

  return "";
}

function assistantSection(pathname, search) {
  const id = getAssistantId(pathname, search);
  if (!id) return null;

  const base = `/app/products/chat/assistants/${encodeURIComponent(id)}`;
  const canonicalBase = `/app/agents/${encodeURIComponent(id)}`;

  return {
    root: "/app/agents",
    label: "Assistant",
    tabs: [
      {
        to: canonicalBase,
        label: "Edit",
        end: true,
        activePaths: [canonicalBase],
        activeSearch: (value) => !new URLSearchParams(value).has("tab"),
      },
      {
        to: `${base}/behavior`,
        label: "Behavior",
        activePaths: [canonicalBase],
        activeSearch: (value) =>
          new URLSearchParams(value).get("tab") === "config",
      },
      {
        to: `${base}/knowledge`,
        label: "Knowledge",
        activePaths: [`${base}/knowledge`],
      },
      {
        to: `${base}/quality`,
        label: "Quality",
        activePaths: ["/app/agents/quality"],
        activeSearch: (value) => new URLSearchParams(value).get("agent") === id,
      },
      {
        to: `${base}/versions`,
        label: "Versions",
        activePaths: ["/app/agents/versions"],
        activeSearch: (value) => new URLSearchParams(value).get("agent") === id,
      },
      {
        to: `${base}/analytics`,
        label: "Analytics",
        activePaths: [`${base}/analytics`],
      },
      {
        to: `${base}/install`,
        label: "Install",
        activePaths: [`${base}/install`, `${canonicalBase}/deploy`],
      },
      {
        to: `${base}/playground`,
        label: "Playground",
        activePaths: ["/app/chat"],
        activeSearch: (value) => new URLSearchParams(value).get("agent") === id,
      },
    ],
  };
}

// Resolve the section config for a given pathname (longest-prefix match so
// `/app/agents/versions` resolves to the `/app/agents` section).
export function resolveSection(pathname, search = "") {
  const assistant = assistantSection(pathname, search);
  if (assistant) return assistant;

  const root = Object.keys(SECTIONS)
    .filter((r) => {
      if (pathname === r || pathname.startsWith(r + "/")) return true;
      if (r === "/app/knowledge-base") {
        return (
          pathname === "/app/products/chat/knowledge" ||
          pathname.startsWith("/app/products/chat/knowledge/")
        );
      }
      return false;
    })
    .sort((a, b) => b.length - a.length)[0];
  return root ? { root, ...SECTIONS[root] } : null;
}

// Filter a list of nav/tab entries by the caller's entitlements. `check` is
// `{ isProductEnabled, isFeatureEnabled }` from `useEntitlements()`.
export function filterByEntitlements(
  items,
  { isProductEnabled, isFeatureEnabled } = {},
) {
  return items.filter((it) => {
    if (it.product && isProductEnabled && !isProductEnabled(it.product))
      return false;
    if (it.feature && isFeatureEnabled && !isFeatureEnabled(it.feature))
      return false;
    return true;
  });
}
