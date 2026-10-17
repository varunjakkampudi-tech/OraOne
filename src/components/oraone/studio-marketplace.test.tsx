import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  installMarketplaceListing,
  listMarketplaceListings,
  type MarketplaceListing,
} from "@/lib/api/marketplace";
import { listingStatus } from "@/lib/marketplace-status";
import { MarketplacePage } from "./studio-marketplace";

vi.mock("@tanstack/react-router", async () => {
  const { createElement } = await import("react");
  return {
    Link: ({ to, children, className }: { to: string; children?: ReactNode; className?: string }) =>
      createElement("a", { href: to, className }, children),
  };
});

vi.mock("./studio", async () => {
  const { createElement, Fragment } = await import("react");
  return {
    StudioFrame: ({ children }: { children?: ReactNode }) =>
      createElement(Fragment, null, children),
  };
});

vi.mock("@/lib/studio-helpers", () => ({
  useWorkspaceId: () => ({ id: "ws-1", error: "", loaded: true }),
}));

vi.mock("@/lib/api/marketplace", () => ({
  listMarketplaceListings: vi.fn(),
  installMarketplaceListing: vi.fn(),
}));

const base = {
  icon: "🤖",
  tags: [],
  author: "OraOne",
  featured: false,
  installed: false,
  rating: 0,
  review_count: 0,
};

const agentListing: MarketplaceListing = {
  ...base,
  slug: "agent-support",
  name: "Support agent",
  category: "agent_template",
  summary: "Answers customer questions.",
  installable: true,
  requirements: [],
};

const workflowListing: MarketplaceListing = {
  ...base,
  slug: "workflow-followup",
  name: "Lead follow-up",
  category: "workflow",
  summary: "Follows up with new leads.",
  installable: true,
  requirements: [
    {
      kind: "workflow",
      key: "engine",
      label: "Workflow engine",
      status: "satisfied",
      message: "Every trigger and step is supported by the workflow engine.",
      blocking: true,
    },
  ],
};

const crmListing: MarketplaceListing = {
  ...base,
  slug: "workflow-crm-sync",
  name: "CRM sync",
  category: "workflow",
  summary: "Keeps the CRM up to date.",
  installable: false,
  requirements: [
    {
      kind: "integration",
      key: "hubspot",
      label: "HubSpot",
      status: "requires_integration",
      message: "Requires HubSpot. Connect it on the Integrations page first.",
      blocking: true,
    },
  ],
};

describe("listingStatus", () => {
  it("maps an installable listing to installable", () => {
    expect(listingStatus(agentListing)).toBe("installable");
  });

  it("maps a blocking integration requirement to requires_integration", () => {
    expect(listingStatus(crmListing)).toBe("requires_integration");
  });

  it("maps a blocking unsupported or unavailable requirement to not_supported", () => {
    expect(
      listingStatus({
        installable: false,
        requirements: [
          {
            kind: "workflow",
            key: "step:x",
            label: "Step x",
            status: "unsupported",
            message: "",
            blocking: true,
          },
        ],
      }),
    ).toBe("not_supported");
    expect(
      listingStatus({
        installable: false,
        requirements: [
          {
            kind: "integration",
            key: "y",
            label: "Y",
            status: "unavailable",
            message: "",
            blocking: true,
          },
        ],
      }),
    ).toBe("not_supported");
  });

  it("ignores non-blocking requirements when deciding installability", () => {
    expect(
      listingStatus({
        installable: true,
        requirements: [
          {
            kind: "integration",
            key: "z",
            label: "Z",
            status: "requires_integration",
            message: "",
            blocking: false,
          },
        ],
      }),
    ).toBe("installable");
  });
});

describe("MarketplacePage install confirmation", () => {
  beforeEach(() => {
    vi.mocked(listMarketplaceListings).mockReset();
    vi.mocked(installMarketplaceListing).mockReset();
    vi.mocked(listMarketplaceListings).mockResolvedValue([
      agentListing,
      workflowListing,
      crmListing,
    ]);
  });

  it("only offers Install for installable listings", async () => {
    render(<MarketplacePage />);
    await screen.findByRole("button", { name: "Install Support agent" });
    expect(screen.getByRole("button", { name: "Install Lead follow-up" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Install CRM sync" })).toBeNull();
    const crmCard = screen.getByRole("heading", { name: "CRM sync" }).closest("article");
    if (!crmCard) throw new Error("CRM sync card not rendered");
    expect(
      within(crmCard).getByRole("link", { name: "Open Integrations" }).getAttribute("href"),
    ).toBe("/studio/integrations");
  });

  it("does not install until the second confirm is pressed", async () => {
    vi.mocked(installMarketplaceListing).mockResolvedValue({
      installation: {
        id: "i-1",
        listing_slug: "workflow-followup",
        listing_name: "Lead follow-up",
        category: "workflow",
        status: "installed",
        agent_id: null,
        created_at: "2026-10-17T00:00:00Z",
      },
      agent_id: null,
      workflow_id: "w-1",
      requirements: [],
    });
    render(<MarketplacePage />);

    fireEvent.click(await screen.findByRole("button", { name: "Install Lead follow-up" }));
    expect(installMarketplaceListing).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Confirm install of Lead follow-up" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Cancel install of Lead follow-up" }));
    expect(screen.queryByRole("button", { name: "Confirm install of Lead follow-up" })).toBeNull();
    expect(installMarketplaceListing).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Install Lead follow-up" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm install of Lead follow-up" }));

    await waitFor(() =>
      expect(installMarketplaceListing).toHaveBeenCalledWith("ws-1", "workflow-followup"),
    );
    expect(
      await screen.findByText("Created a draft workflow. Turn it on when you are ready."),
    ).toBeTruthy();
  });

  it("shows a plain-language error and no success when the install fails", async () => {
    vi.mocked(installMarketplaceListing).mockRejectedValue(
      Object.assign(new Error("Requires HubSpot."), { status: 409 }),
    );
    render(<MarketplacePage />);

    fireEvent.click(await screen.findByRole("button", { name: "Install Support agent" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm install of Support agent" }));

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByText(/Added a draft assistant/)).toBeNull();
  });
});
