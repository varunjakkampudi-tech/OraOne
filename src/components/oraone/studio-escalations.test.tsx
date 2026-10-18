import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  addEscalationNote,
  assignEscalation,
  getEscalationSummary,
  listEscalations,
  type Escalation,
} from "@/lib/api/escalations";
import { getMe } from "@/lib/api/auth";
import { EscalationsPage } from "./studio-escalations";

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

vi.mock("@/lib/api/auth", () => ({
  getMe: vi.fn(),
}));

vi.mock("@/lib/api/escalations", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/escalations")>();
  return {
    ...actual,
    listEscalations: vi.fn(),
    getEscalationSummary: vi.fn(),
    assignEscalation: vi.fn(),
    addEscalationNote: vi.fn(),
    resolveEscalation: vi.fn(),
    reopenEscalation: vi.fn(),
  };
});

const base: Escalation = {
  id: "esc-1",
  channel: "chat",
  question: "Do you deliver to Goa?",
  status: "open",
  has_contact: true,
  contact_name: "Pat",
  contact_email: "pat@example.test",
  contact_phone: null,
  assigned_user_id: null,
  notify_status: "sent",
  notify_attempts: 1,
  last_error: null,
  due_at: new Date(Date.now() - 3_600_000).toISOString(),
  overdue: true,
  internal_notes: [],
  created_at: new Date().toISOString(),
  resolved_at: null,
};

const summary = {
  open: 1,
  assigned: 0,
  resolved: 0,
  overdue: 1,
  notify_failed: 0,
  dead_letter: 0,
  no_recipients: 0,
};

describe("EscalationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getMe).mockResolvedValue({ userId: "user-1" } as Awaited<ReturnType<typeof getMe>>);
    vi.mocked(getEscalationSummary).mockResolvedValue(summary);
    vi.mocked(listEscalations).mockResolvedValue([base]);
  });

  it("shows the question with an overdue target and the summary counts", async () => {
    render(<EscalationsPage />);

    expect(await screen.findByText("Do you deliver to Goa?")).toBeInTheDocument();
    expect(screen.getByText(/Overdue since/)).toBeInTheDocument();
    const counts = screen.getByLabelText("Escalation counts");
    expect(within(counts).getByText("Overdue").nextSibling).toHaveTextContent("1");
  });

  it("assigns the item to the signed-in user", async () => {
    vi.mocked(assignEscalation).mockResolvedValue({ ...base, assigned_user_id: "user-1" });
    render(<EscalationsPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Do you deliver to Goa/ }));
    fireEvent.click(screen.getByRole("button", { name: "Take it" }));

    await waitFor(() => expect(assignEscalation).toHaveBeenCalledWith("ws-1", "esc-1", "user-1"));
  });

  it("saves an internal note and clears the draft", async () => {
    vi.mocked(addEscalationNote).mockResolvedValue({
      ...base,
      internal_notes: [{ at: new Date().toISOString(), user_id: "user-1", text: "Called back." }],
    });
    render(<EscalationsPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Do you deliver to Goa/ }));
    fireEvent.change(screen.getByLabelText("Add a note"), { target: { value: "Called back." } });
    fireEvent.click(screen.getByRole("button", { name: "Save note" }));

    await waitFor(() =>
      expect(addEscalationNote).toHaveBeenCalledWith("ws-1", "esc-1", "Called back."),
    );
    await waitFor(() => expect(screen.getByLabelText("Add a note")).toHaveValue(""));
  });

  it("tells the team plainly when no owner can be emailed", async () => {
    vi.mocked(listEscalations).mockResolvedValue([{ ...base, notify_status: "no_recipients" }]);
    render(<EscalationsPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Do you deliver to Goa/ }));
    expect(screen.getByText(/No owner or admin to email/)).toBeInTheDocument();
  });
});
