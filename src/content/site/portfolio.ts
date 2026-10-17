import type { Status } from "./types";

// The OraOne platform's capabilities, as documented in docs/PRODUCT-PORTFOLIO.md. The ten
// entries were planned as separate products for development; to customers they are
// capabilities of one platform. Only capability 1 is in active development. Nothing here
// is a release date, a completion percentage or an availability claim.

export type Product = {
  id: number;
  /** The internal product name, used in roadmap and documentation. */
  name: string;
  /** The capability as a customer sees it inside the one OraOne platform. */
  capability: string;
  status: Status;
  summary: string;
};

export const PORTFOLIO: Product[] = [
  {
    id: 1,
    name: "OraOne AI Chat Platform",
    capability: "Conversations and knowledge",
    status: "active",
    summary: "Assistants that answer from your documents, with one inbox and leads.",
  },
  {
    id: 2,
    name: "OraOne AI Voice Platform",
    capability: "Voice calls",
    status: "planned",
    summary: "AI voice assistants that answer calls and hold natural conversations.",
  },
  {
    id: 3,
    name: "OraOne WhatsApp Platform",
    capability: "WhatsApp",
    status: "planned",
    summary: "Business messaging and automation on WhatsApp.",
  },
  {
    id: 4,
    name: "Omnichannel Communication Hub",
    capability: "Every channel in one inbox",
    status: "planned",
    summary: "One place for conversations and customer context across every channel.",
  },
  {
    id: 5,
    name: "Workflow Automation Platform",
    capability: "Automations",
    status: "planned",
    summary: "Triggers and actions for follow-ups, handovers and reminders.",
  },
  {
    id: 6,
    name: "AI Studio & Agent Builder",
    capability: "Build your own agents",
    status: "planned",
    summary: "Build, test and configure your own AI agents.",
  },
  {
    id: 7,
    name: "Marketplace",
    capability: "Marketplace",
    status: "planned",
    summary: "Agents, templates and connectors from partners and the community.",
  },
  {
    id: 8,
    name: "Mobile Applications",
    capability: "Mobile",
    status: "planned",
    summary: "Run the business and reply to customers from a phone.",
  },
  {
    id: 9,
    name: "Enterprise Edition",
    capability: "Enterprise controls",
    status: "planned",
    summary: "Advanced security, governance and deployment for larger organisations.",
  },
  {
    id: 10,
    name: "OraOne OS",
    capability: "OraOne OS",
    status: "vision",
    summary: "A long-term operating layer for AI and business communication.",
  },
];
