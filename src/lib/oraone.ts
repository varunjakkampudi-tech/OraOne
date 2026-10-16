import routeManifest from "./route-manifest.json";
import { SITE_URL } from "./site";

/**
 * Products offered by this application. OraOne Product 1 (AI Chat) is the only
 * product in this repository. Other products are planned and have no routes here.
 */
export const products = [
  {
    slug: "chat",
    name: "OraOne AI Chat Platform",
    short: "AI Chat",
    status: "Current product",
    description: "Build, train and manage website assistants that put your knowledge to work.",
    capabilities: [
      "Website assistants",
      "Knowledge connections",
      "Conversation inbox",
      "Widget customization",
    ],
  },
] as const;

export function isIndexablePath(path: string) {
  return (
    !/^\/(app|admin|auth|onboarding)(\/|$)/.test(path) &&
    ![
      "/reset-password",
      "/privacy",
      "/terms",
      "/cookies",
      "/acceptable-use",
      "/refund-policy",
    ].includes(path)
  );
}

export function pageHead(title: string, routePath?: string) {
  const normalizedTitle = title.split(" · ")[0] || title;
  const entry = routeManifest.find((r) => r.title === normalizedTitle);
  const path = routePath || (title.startsWith("OraOne —") ? "/" : entry?.path);
  const publicPage = path ? isIndexablePath(path) : false;
  const description = title.startsWith("OraOne —")
    ? "Explore OraOne: AI assistants, business knowledge and customer conversations in one connected workspace. View the sample experience and product roadmap."
    : `${normalizedTitle} with OraOne. ${entry?.family === "public" ? "Explore business-aware AI assistants, customer communication and the connected product vision." : "Review the OraOne workspace preview. Live operations require verified access and connected services."}`;
  const pageTitle = title.startsWith("OraOne —") ? title : `${title} · OraOne`;
  const url = path && !path.includes("$") ? `${SITE_URL}${path}` : undefined;
  return {
    meta: [
      { title: pageTitle },
      { name: "description", content: description },
      { property: "og:title", content: pageTitle },
      { property: "og:description", content: description },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: pageTitle },
      { name: "twitter:description", content: description },
      { name: "robots", content: publicPage ? "index, follow" : "noindex, follow" },
      ...(url ? [{ property: "og:url", content: url }] : []),
    ],
    links: url ? [{ rel: "canonical", href: url }] : [],
  };
}

export const demoCustomers = [
  {
    id: "olivia",
    name: "Olivia Rhye",
    initials: "OR",
    email: "olivia@example.com",
    company: "Layers",
    status: "Customer",
    channel: "Website",
    date: "Today, 10:42 AM",
  },
  {
    id: "phoenix",
    name: "Phoenix Baker",
    initials: "PB",
    email: "phoenix@example.com",
    company: "Sisyphus",
    status: "Qualified",
    channel: "Website",
    date: "Today, 10:18 AM",
  },
  {
    id: "lana",
    name: "Lana Steiner",
    initials: "LS",
    email: "lana@example.com",
    company: "Catalog",
    status: "New lead",
    channel: "Website",
    date: "Today, 9:56 AM",
  },
  {
    id: "demi",
    name: "Demi Wilkinson",
    initials: "DW",
    email: "demi@example.com",
    company: "Circooles",
    status: "Customer",
    channel: "Website",
    date: "Yesterday",
  },
  {
    id: "drew",
    name: "Drew Cano",
    initials: "DC",
    email: "drew@example.com",
    company: "Hourglass",
    status: "Qualified",
    channel: "Website",
    date: "Yesterday",
  },
];

export const demoConversations = [
  {
    id: "olivia",
    name: "Olivia Rhye",
    initials: "OR",
    subject: "A question about the enterprise plan",
    preview: "Could you help me understand the onboarding process?",
    time: "2m",
    status: "Needs attention",
    unread: true,
  },
  {
    id: "phoenix",
    name: "Phoenix Baker",
    initials: "PB",
    subject: "Getting started with an assistant",
    preview: "Thanks, that answers my question!",
    time: "14m",
    status: "Resolved",
    unread: false,
  },
  {
    id: "lana",
    name: "Lana Steiner",
    initials: "LS",
    subject: "Connecting our knowledge base",
    preview: "Can I import content from our website?",
    time: "28m",
    status: "Open",
    unread: true,
  },
  {
    id: "demi",
    name: "Demi Wilkinson",
    initials: "DW",
    subject: "Widget customization options",
    preview: "I would like to match our brand colors.",
    time: "1h",
    status: "Open",
    unread: false,
  },
  {
    id: "drew",
    name: "Drew Cano",
    initials: "DC",
    subject: "Thank you for your help",
    preview: "Everything is working well now.",
    time: "2h",
    status: "Resolved",
    unread: false,
  },
];

export const sampleWorkspaceName = "Acme Corporation";
export const accessPolicy = { freeForEveryone: true, paymentsEnabled: false } as const;
export const recoveryPath = "/auth/sign-in";
export function isWorkspaceDestinationActive(path: string, destination: string) {
  const normalized = path.replace(/\/$/, "");
  return destination === "/app"
    ? normalized === destination
    : normalized === destination || normalized.startsWith(destination + "/");
}

export const demoAssistants = [
  { id: "support", name: "Customer Support", sources: 142 },
  { id: "sales", name: "Sales Assistant", sources: 28 },
  { id: "onboarding", name: "Onboarding Assistant", sources: 12 },
];
export function visibleConversationId(id: string | undefined, filter: string, query: string) {
  const rows = demoConversations.filter(
    (c) =>
      (filter === "All conversations" || c.status === filter) &&
      (c.name + " " + c.preview).toLowerCase().includes(query.toLowerCase()),
  );
  return rows.find((c) => c.id === id)?.id ?? rows[0]?.id;
}
