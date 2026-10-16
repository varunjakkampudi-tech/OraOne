import type { Status } from "./types";

// The OraOne product family, as documented in docs/PRODUCT-PORTFOLIO.md. Only Product 1
// is in active development; every other product is planned or a long-term vision.
// Nothing here is a release date, a completion percentage or an availability claim.

export type Product = {
  id: number;
  name: string;
  status: Status;
  summary: string;
};

export const PORTFOLIO: Product[] = [
  {
    id: 1,
    name: "OraOne AI Chat Platform",
    status: "active",
    summary: "Website assistants that answer from your documents, with a team inbox and leads.",
  },
  {
    id: 2,
    name: "OraOne AI Voice Platform",
    status: "planned",
    summary: "AI voice agents that answer calls and hold natural conversations.",
  },
  {
    id: 3,
    name: "OraOne WhatsApp Platform",
    status: "planned",
    summary: "Business messaging and automation on WhatsApp.",
  },
  {
    id: 4,
    name: "Omnichannel Communication Hub",
    status: "planned",
    summary: "One place for conversations and customer context across every channel.",
  },
  {
    id: 5,
    name: "Workflow Automation Platform",
    status: "planned",
    summary: "Triggers and actions for follow-ups, handovers and reminders.",
  },
  {
    id: 6,
    name: "AI Studio & Agent Builder",
    status: "planned",
    summary: "Build, test and configure your own AI agents.",
  },
  {
    id: 7,
    name: "Marketplace",
    status: "planned",
    summary: "Agents, templates and connectors from partners and the community.",
  },
  {
    id: 8,
    name: "Mobile Applications",
    status: "planned",
    summary: "Run the business and reply to customers from a phone.",
  },
  {
    id: 9,
    name: "Enterprise Edition",
    status: "planned",
    summary: "Advanced security, governance and deployment for larger organisations.",
  },
  {
    id: 10,
    name: "OraOne OS",
    status: "vision",
    summary: "A long-term operating layer for AI and business communication.",
  },
];
