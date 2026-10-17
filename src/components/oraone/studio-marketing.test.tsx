import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  cancelMarketingCampaign,
  getMarketingCampaign,
  listMarketingCampaigns,
  sendMarketingCampaign,
  type MarketingCampaign,
  type MarketingCampaignDetail,
} from "@/lib/api/marketing";
import { listLeads } from "@/lib/api/leads";
import { MarketingPage } from "./studio-marketing";

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
  when: () => "Today",
}));

vi.mock("@/lib/api/marketing", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/marketing")>();
  return {
    ...actual,
    listMarketingCampaigns: vi.fn(),
    getMarketingCampaign: vi.fn(),
    sendMarketingCampaign: vi.fn(),
    cancelMarketingCampaign: vi.fn(),
    createMarketingCampaign: vi.fn(),
  };
});

vi.mock("@/lib/api/leads", () => ({
  listLeads: vi.fn(),
}));

const campaign: MarketingCampaign = {
  id: "camp-1",
  project_id: "ws-1",
  name: "Spring offer",
  channel: "email",
  subject: "Spring",
  body: "Our spring offer is live.",
  status: "draft",
  created_by: null,
  created_at: "2026-10-17T10:00:00Z",
  sent_count: 0,
  skipped_count: 1,
  failed_count: 0,
};

function detail(overrides: Partial<MarketingCampaignDetail> = {}): MarketingCampaignDetail {
  return {
    ...campaign,
    queued_count: 2,
    recipients: [
      {
        id: "r-1",
        lead_id: "l-1",
        lead_label: "Jane Doe",
        status: "queued",
        skip_reason: null,
        failure_reason: null,
        sent_at: null,
      },
      {
        id: "r-2",
        lead_id: "l-2",
        lead_label: "Sam Lee",
        status: "queued",
        skip_reason: null,
        failure_reason: null,
        sent_at: null,
      },
      {
        id: "r-3",
        lead_id: "l-3",
        lead_label: "Ana Ruiz",
        status: "skipped",
        skip_reason: "We do not have this contact's consent to reach out.",
        failure_reason: null,
        sent_at: null,
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listMarketingCampaigns).mockResolvedValue([campaign]);
  vi.mocked(getMarketingCampaign).mockResolvedValue(detail());
  vi.mocked(listLeads).mockResolvedValue([]);
});

async function openDraft() {
  render(<MarketingPage />);
  const list = await screen.findByRole("list", { name: "Marketing campaigns" });
  fireEvent.click(within(list).getByRole("button", { name: /Spring offer/ }));
  await screen.findByRole("heading", { name: "Recipients" });
}

describe("marketing send confirmation", () => {
  it("does not call the send API until the sender confirms", async () => {
    vi.mocked(sendMarketingCampaign).mockResolvedValue(
      detail({ status: "completed", sent_count: 2, queued_count: 0 }),
    );
    await openDraft();

    fireEvent.click(screen.getByRole("button", { name: "Send campaign" }));

    const dialog = screen.getByRole("alertdialog", { name: "Confirm send" });
    expect(within(dialog).getByText(/Send to 2 people by Email\?/)).toBeTruthy();
    expect(sendMarketingCampaign).not.toHaveBeenCalled();

    fireEvent.click(within(dialog).getByRole("button", { name: "Confirm send" }));

    await waitFor(() => expect(sendMarketingCampaign).toHaveBeenCalledTimes(1));
    expect(sendMarketingCampaign).toHaveBeenCalledWith("ws-1", "camp-1");
  });

  it("keeps the campaign as a draft when the sender backs out", async () => {
    await openDraft();

    fireEvent.click(screen.getByRole("button", { name: "Send campaign" }));
    fireEvent.click(screen.getByRole("button", { name: "Keep as draft" }));

    expect(screen.queryByRole("alertdialog", { name: "Confirm send" })).toBeNull();
    expect(screen.getByRole("button", { name: "Send campaign" })).toBeTruthy();
    expect(sendMarketingCampaign).not.toHaveBeenCalled();
  });

  it("disables send when no recipient can receive the message", async () => {
    vi.mocked(getMarketingCampaign).mockResolvedValue(detail({ queued_count: 0 }));
    await openDraft();

    expect(screen.getByRole("button", { name: "Send campaign" }).hasAttribute("disabled")).toBe(
      true,
    );
  });

  it("shows the plain-language skip reason for a skipped recipient", async () => {
    await openDraft();

    expect(
      screen.getByText("Reason: We do not have this contact's consent to reach out."),
    ).toBeTruthy();
  });

  it("shows the honest failure reason when no email provider is connected", async () => {
    vi.mocked(getMarketingCampaign).mockResolvedValue(
      detail({
        status: "completed",
        queued_count: 0,
        failed_count: 1,
        recipients: [
          {
            id: "r-9",
            lead_id: "l-9",
            lead_label: "Jane Doe",
            status: "failed",
            skip_reason: null,
            failure_reason: "No email delivery provider is connected yet",
            sent_at: null,
          },
        ],
      }),
    );
    await openDraft();

    expect(screen.getByText("Reason: No email delivery provider is connected yet")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Send campaign" })).toBeNull();
  });
});

describe("marketing cancel confirmation", () => {
  it("cancels only after the second confirmation", async () => {
    vi.mocked(cancelMarketingCampaign).mockResolvedValue(detail({ status: "cancelled" }));
    await openDraft();

    fireEvent.click(screen.getByRole("button", { name: "Cancel campaign" }));
    expect(cancelMarketingCampaign).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Confirm cancel" }));
    await waitFor(() => expect(cancelMarketingCampaign).toHaveBeenCalledWith("ws-1", "camp-1"));
  });
});
