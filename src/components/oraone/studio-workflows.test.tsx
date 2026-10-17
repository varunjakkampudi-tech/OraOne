import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  deleteWorkflow,
  getWorkflow,
  listWorkflowRuns,
  listWorkflows,
  setWorkflowEnabled,
  type WorkflowDetail,
} from "@/lib/api/workflows";
import { runStatusLabel, stepLabel, stepReason, workflowStatusLabel } from "@/lib/workflow-status";
import { WorkflowsPage } from "./studio-workflows";

vi.mock("./studio", async () => {
  const { createElement, Fragment } = await import("react");
  return {
    StudioFrame: ({ children }: { children?: ReactNode }) =>
      createElement(Fragment, null, children),
  };
});

vi.mock("@/lib/studio-helpers", () => ({
  useWorkspaceId: () => ({ id: "ws-1", error: "", loaded: true }),
  when: (iso: string | null | undefined) => (iso ? "a past day" : "—"),
}));

vi.mock("@/lib/api/workflows", () => ({
  listWorkflows: vi.fn(),
  getWorkflow: vi.fn(),
  createWorkflow: vi.fn(),
  setWorkflowEnabled: vi.fn(),
  deleteWorkflow: vi.fn(),
  listWorkflowRuns: vi.fn(),
  getWorkflowRun: vi.fn(),
}));

const TIMESTAMP = "2026-10-01T00:00:00Z";

const workflow: WorkflowDetail = {
  id: "wf-1",
  organization_id: "org-1",
  name: "Lead follow-up",
  description: null,
  status: "paused",
  trigger_type: "event",
  trigger_config: { event: "lead.created" },
  created_by: null,
  run_count: 3,
  success_count: 2,
  last_run_at: null,
  created_at: TIMESTAMP,
  updated_at: TIMESTAMP,
  steps: [
    {
      id: "step-1",
      workflow_id: "wf-1",
      order_index: 0,
      type: "delay",
      name: "Wait",
      config: { hours: 1 },
      created_at: TIMESTAMP,
      updated_at: TIMESTAMP,
    },
  ],
};

const emptyRuns = { items: [], total: 0, limit: 25, offset: 0 };

describe("workflow status labels", () => {
  it("maps stored workflow statuses to On, Off and Draft", () => {
    expect(workflowStatusLabel("active")).toBe("On");
    expect(workflowStatusLabel("paused")).toBe("Off");
    expect(workflowStatusLabel("draft")).toBe("Draft");
  });

  it("does not guess at a status the API does not return", () => {
    expect(workflowStatusLabel("archived")).toBe("Unknown");
  });

  it("labels run and step statuses in plain words", () => {
    expect(runStatusLabel("awaiting_approval")).toBe("Waiting for approval");
    expect(runStatusLabel("cancelled")).toBe("Cancelled");
    expect(runStatusLabel("mystery")).toBe("Unknown");
  });

  it("shows the step kind the author chose, even when the API stores it under another type", () => {
    expect(stepLabel("delay", { hours: 1 })).toBe("Wait");
    expect(stepLabel("notification", { action: "send_message" })).toBe("Send a message");
    expect(stepLabel("transform", { action: "create_task" })).toBe("Create a task");
    expect(stepLabel("condition", { op: "contains" })).toBe("Check a condition");
  });

  it("uses the recorded reason and never invents one", () => {
    expect(stepReason({ error_message: "No phone number.", output: { reason: "ignored" } })).toBe(
      "No phone number.",
    );
    expect(stepReason({ error_message: null, output: { reason: "Condition not met." } })).toBe(
      "Condition not met.",
    );
    expect(stepReason({ error_message: null, output: {} })).toBe("No reason was recorded.");
  });
});

describe("workflow confirm behaviour", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listWorkflows).mockResolvedValue({
      items: [workflow],
      total: 1,
      limit: 200,
      offset: 0,
    });
    vi.mocked(getWorkflow).mockResolvedValue(workflow);
    vi.mocked(listWorkflowRuns).mockResolvedValue(emptyRuns);
  });

  async function openWorkflow() {
    render(<WorkflowsPage />);
    fireEvent.click(await screen.findByRole("button", { name: /Lead follow-up/ }));
    await screen.findByRole("heading", { level: 2, name: "Lead follow-up" });
  }

  it("does not turn a workflow on until the second confirm", async () => {
    vi.mocked(setWorkflowEnabled).mockResolvedValue({ ...workflow, status: "active" });
    await openWorkflow();

    fireEvent.click(screen.getByRole("button", { name: "Turn on" }));
    expect(screen.getByRole("button", { name: "Confirm turn on" })).toBeInTheDocument();
    expect(setWorkflowEnabled).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(setWorkflowEnabled).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Turn on" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Turn on" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm turn on" }));
    await waitFor(() => expect(setWorkflowEnabled).toHaveBeenCalledWith("ws-1", "wf-1", true));
    expect(await screen.findByRole("button", { name: "Turn off" })).toBeInTheDocument();
  });

  it("states the consequence before deleting and deletes only on the second confirm", async () => {
    vi.mocked(deleteWorkflow).mockResolvedValue({ deleted: true });
    await openWorkflow();

    fireEvent.click(screen.getByRole("button", { name: "Delete workflow" }));
    expect(screen.getByText(/this cannot be undone/)).toBeInTheDocument();
    expect(deleteWorkflow).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(deleteWorkflow).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Delete workflow" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete workflow" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
    await waitFor(() => expect(deleteWorkflow).toHaveBeenCalledWith("ws-1", "wf-1"));
    expect(await screen.findByText("No workflows yet.")).toBeInTheDocument();
  });
});
