import { apiRequest } from "./client";

// Escalations are visitor questions the assistant could not answer, or requests
// for a person. They are scoped to a workspace (project).

export type EscalationNote = {
  at: string;
  user_id: string;
  text: string;
};

export type Escalation = {
  id: string;
  channel: string;
  question: string;
  status: "open" | "assigned" | "resolved";
  has_contact: boolean;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  assigned_user_id: string | null;
  notify_status: "pending" | "sent" | "failed" | "dead_letter" | "no_recipients";
  notify_attempts: number;
  last_error: string | null;
  due_at: string | null;
  overdue: boolean;
  internal_notes: EscalationNote[];
  created_at: string;
  resolved_at: string | null;
};

export type EscalationSummary = {
  open: number;
  assigned: number;
  resolved: number;
  overdue: number;
  notify_failed: number;
  dead_letter: number;
  no_recipients: number;
};

export type EscalationFilter = "open" | "assigned" | "resolved" | "overdue";

export function listEscalations(projectId: string, filter: EscalationFilter) {
  const query =
    filter === "overdue"
      ? "overdue=true&limit=100"
      : `status=${encodeURIComponent(filter)}&limit=100`;
  return apiRequest<Escalation[]>(`/escalations?${query}`, { projectId });
}

export function getEscalationSummary(projectId: string) {
  return apiRequest<EscalationSummary>("/escalations/summary", { projectId });
}

export function assignEscalation(projectId: string, id: string, userId: string | null) {
  return apiRequest<Escalation>(`/escalations/${id}/assign`, {
    method: "POST",
    body: { user_id: userId },
    projectId,
  });
}

export function addEscalationNote(projectId: string, id: string, text: string) {
  return apiRequest<Escalation>(`/escalations/${id}/notes`, {
    method: "POST",
    body: { text },
    projectId,
  });
}

export function resolveEscalation(projectId: string, id: string) {
  return apiRequest<Escalation>(`/escalations/${id}/resolve`, {
    method: "POST",
    body: {},
    projectId,
  });
}

export function reopenEscalation(projectId: string, id: string) {
  return apiRequest<Escalation>(`/escalations/${id}/reopen`, {
    method: "POST",
    body: {},
    projectId,
  });
}
