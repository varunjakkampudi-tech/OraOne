import { apiRequest } from "./client";

// Call campaigns are scoped to a workspace (project). Pass the workspace id as projectId.
// Calls are placed only when the telephony account is connected; these endpoints
// report what the server did and never imply a call was placed on their own.
// Field names mirror backend/app/schemas/calls.py.

export type CallCampaignCounts = {
  total: number;
  queued: number;
  calling: number;
  completed: number;
  failed: number;
  skipped: number;
};

export type CallCampaign = {
  id: string;
  project_id: string;
  name: string;
  status: string;
  timezone: string;
  created_by: string | null;
  created_at: string;
  counts: CallCampaignCounts;
};

export type CallAttempt = {
  id: string;
  campaign_id: string;
  lead_id: string;
  status: string;
  /** Set when the attempt was skipped; the reason is written for people, not codes. */
  skip_reason: string | null;
  attempted_at: string | null;
  duration_seconds: number | null;
  outcome: string | null;
};

export type CreateCallCampaignInput = {
  name: string;
  lead_ids: string[];
};

export function listCallCampaigns(projectId: string) {
  return apiRequest<CallCampaign[]>("/calls/campaigns", { projectId });
}

export function getCallCampaign(projectId: string, campaignId: string) {
  return apiRequest<CallCampaign>(`/calls/campaigns/${encodeURIComponent(campaignId)}`, {
    projectId,
  });
}

export function listCallAttempts(projectId: string, campaignId: string) {
  return apiRequest<CallAttempt[]>(`/calls/campaigns/${encodeURIComponent(campaignId)}/attempts`, {
    projectId,
  });
}

export function createCallCampaign(projectId: string, input: CreateCallCampaignInput) {
  return apiRequest<CallCampaign>("/calls/campaigns", {
    method: "POST",
    body: input,
    projectId,
  });
}

export function startCallCampaign(projectId: string, campaignId: string) {
  return apiRequest<CallCampaign>(`/calls/campaigns/${encodeURIComponent(campaignId)}/start`, {
    method: "POST",
    projectId,
  });
}

export function pauseCallCampaign(projectId: string, campaignId: string) {
  return apiRequest<CallCampaign>(`/calls/campaigns/${encodeURIComponent(campaignId)}/pause`, {
    method: "POST",
    projectId,
  });
}
