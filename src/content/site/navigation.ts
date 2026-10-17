import type { Link, Status } from "./types";

// Top navigation. OraOne is presented as one AI platform, so the menu shows one product and its capabilities.
export const PRODUCT_LINKS: Link[] = [
  { label: "AI Chat", to: "/products/ai-chat" },
  { label: "Capabilities", to: "/products" },
  { label: "Roadmap", to: "/roadmap" },
];

export const SOLUTION_LINKS: Link[] = [
  { label: "Customer support", to: "/solutions/customer-support" },
  { label: "Lead generation", to: "/solutions/lead-generation" },
  { label: "Sales", to: "/solutions/sales" },
  { label: "Small business", to: "/solutions/small-business" },
];

export const TOP_LINKS: Link[] = [
  { label: "Pricing", to: "/pricing" },
  { label: "Docs", to: "/docs" },
  { label: "Help", to: "/help" },
];

export const FOOTER_GROUPS: { title: string; links: Link[] }[] = [
  {
    title: "Product",
    links: [
      { label: "AI Chat", to: "/products/ai-chat" },
      { label: "Capabilities", to: "/products" },
      { label: "Integrations", to: "/integrations" },
      { label: "Pricing", to: "/pricing" },
      { label: "Roadmap", to: "/roadmap" },
    ],
  },
  {
    title: "Solutions",
    links: [
      { label: "Customer support", to: "/solutions/customer-support" },
      { label: "Lead generation", to: "/solutions/lead-generation" },
      { label: "Sales", to: "/solutions/sales" },
      { label: "Small business", to: "/solutions/small-business" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", to: "/docs" },
      { label: "Help center", to: "/help" },
      { label: "Changelog", to: "/changelog" },
      { label: "Status", to: "/status" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", to: "/about" },
      { label: "Security", to: "/security" },
      { label: "Contact", to: "/contact" },
      { label: "Book a demo", to: "/demo" },
    ],
  },
];

export const LEGAL_LINKS: Link[] = [
  { label: "Privacy", to: "/privacy" },
  { label: "Terms", to: "/terms" },
  { label: "Cookies", to: "/cookies" },
  { label: "Acceptable use", to: "/acceptable-use" },
  { label: "Refunds", to: "/refund-policy" },
];

// Documentation sidebar, in reading order.
export const DOCS_TREE: { group: string; links: Link[] }[] = [
  {
    group: "Get started",
    links: [
      { label: "Overview", to: "/docs" },
      { label: "Quick start", to: "/docs/getting-started" },
    ],
  },
  {
    group: "Build",
    links: [
      { label: "Assistants and knowledge", to: "/docs/ai-chat" },
      { label: "Add to your website", to: "/docs/integrations" },
    ],
  },
  {
    group: "Developers",
    links: [
      { label: "REST API", to: "/docs/api" },
      { label: "Webhooks", to: "/docs/webhooks" },
    ],
  },
  {
    group: "Help",
    links: [
      { label: "Help center", to: "/help" },
      { label: "Contact support", to: "/help/contact" },
    ],
  },
];

export const STATUS_LABEL: Record<Status, string> = {
  available: "Available",
  active: "In active development",
  beta: "Beta",
  "in-development": "In development",
  planned: "Planned",
  vision: "Long-term vision",
};
