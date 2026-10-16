import { apiRequest } from "./client";

// Leads are scoped to a workspace (project). Pass the workspace id as projectId.

export type Lead = {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  company: string | null;
  intent: string | null;
  message: string | null;
  source: string;
  status: string;
  temperature: string;
  score: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type LeadStats = {
  total: number;
  new: number;
  contacted: number;
  qualified: number;
  won: number;
  lost: number;
  hot: number;
  warm: number;
  cold: number;
  conversion_rate: number;
};

export const LEAD_STATUSES = ["new", "contacted", "qualified", "won", "lost"] as const;

export function listLeads(projectId: string, status?: string) {
  const query = status ? `&status=${encodeURIComponent(status)}` : "";
  return apiRequest<Lead[]>(`/leads?limit=200&sort=-created_at${query}`, { projectId });
}

export function getLeadStats(projectId: string) {
  return apiRequest<LeadStats>("/leads/stats", { projectId });
}

export function updateLeadStatus(projectId: string, leadId: string, status: string) {
  return apiRequest<Lead>(`/leads/${leadId}`, { method: "PATCH", body: { status }, projectId });
}
