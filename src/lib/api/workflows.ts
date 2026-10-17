import { apiRequest } from "./client";

// Workflow automation is scoped to a workspace (project). Pass the workspace id as projectId.
// Field names mirror backend/app/schemas/workflows.py. Status, trigger, step and run values are
// the stored strings the API returns; labels for people live in src/lib/workflow-status.ts.

export type Workflow = {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  status: string;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  created_by: string | null;
  run_count: number;
  success_count: number;
  last_run_at: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkflowStep = {
  id: string;
  workflow_id: string;
  order_index: number;
  type: string;
  name: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type WorkflowDetail = Workflow & { steps: WorkflowStep[] };

export type WorkflowListResponse = {
  items: Workflow[];
  total: number;
  limit: number;
  offset: number;
};

export type WorkflowStepInput = {
  type: string;
  name: string;
  config: Record<string, unknown>;
  order_index?: number | null;
};

export type CreateWorkflowInput = {
  name: string;
  description?: string | null;
  trigger_type: string;
  trigger_config: Record<string, unknown>;
  steps: WorkflowStepInput[];
};

export type UpdateWorkflowInput = {
  name?: string;
  description?: string | null;
  status?: string;
  trigger_type?: string;
  trigger_config?: Record<string, unknown>;
  steps?: WorkflowStepInput[];
};

export type WorkflowRun = {
  id: string;
  workflow_id: string;
  organization_id: string;
  status: string;
  trigger: string;
  triggered_by: string | null;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error_message: string | null;
  steps_total: number;
  steps_completed: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type WorkflowRunStep = {
  id: string;
  run_id: string;
  step_id: string | null;
  order_index: number;
  type: string;
  name: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type WorkflowRunDetail = WorkflowRun & { run_steps: WorkflowRunStep[] };

export type WorkflowRunListResponse = {
  items: WorkflowRun[];
  total: number;
  limit: number;
  offset: number;
};

/** Newest first, up to the API maximum of 200. The screen says so when more exist. */
export function listWorkflows(projectId: string) {
  return apiRequest<WorkflowListResponse>("/workflows?limit=200", { projectId });
}

export function getWorkflow(projectId: string, workflowId: string) {
  return apiRequest<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}`, {
    projectId,
  });
}

/** New workflows are created as drafts by the API. */
export function createWorkflow(projectId: string, input: CreateWorkflowInput) {
  return apiRequest<WorkflowDetail>("/workflows", {
    method: "POST",
    body: input,
    projectId,
  });
}

export function updateWorkflow(projectId: string, workflowId: string, input: UpdateWorkflowInput) {
  return apiRequest<WorkflowDetail>(`/workflows/${encodeURIComponent(workflowId)}`, {
    method: "PATCH",
    body: input,
    projectId,
  });
}

/** Turning a workflow on sets status "active"; turning it off sets status "paused". */
export function setWorkflowEnabled(projectId: string, workflowId: string, enabled: boolean) {
  return updateWorkflow(projectId, workflowId, { status: enabled ? "active" : "paused" });
}

/** Soft delete on the server: the workflow stops and is no longer returned. */
export function deleteWorkflow(projectId: string, workflowId: string) {
  return apiRequest<{ deleted: boolean }>(`/workflows/${encodeURIComponent(workflowId)}`, {
    method: "DELETE",
    projectId,
  });
}

export function listWorkflowRuns(projectId: string, workflowId: string) {
  return apiRequest<WorkflowRunListResponse>(
    `/workflows/${encodeURIComponent(workflowId)}/runs?limit=25`,
    { projectId },
  );
}

export function getWorkflowRun(projectId: string, runId: string) {
  return apiRequest<WorkflowRunDetail>(`/workflows/runs/${encodeURIComponent(runId)}`, {
    projectId,
  });
}
