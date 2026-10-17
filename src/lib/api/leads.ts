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
  // Read-only consent provenance, returned by the API from the lead's extra blob.
  consent?: string | null;
  consent_source?: string | null;
  consent_note?: string | null;
  consent_recorded_at?: string | null;
  // Legacy shape: the API no longer returns the extra blob.
  extra?: Record<string, unknown> | null;
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

// Contact import (CSV / XLSX). Preview writes nothing; commit re-sends the same file
// and saves only the rows the server marked valid.

export type LeadImportStatus = "valid" | "duplicate_existing" | "duplicate_in_file" | "invalid";

export type LeadImportRow = {
  row_number: number;
  status: LeadImportStatus;
  reason: string | null;
  name: string | null;
  phone: string | null;
  email: string | null;
  company: string | null;
  consent: string | null;
};

export type LeadImportPreview = {
  file_name: string;
  file_format: string;
  total_rows: number;
  valid: number;
  duplicate_existing: number;
  duplicate_in_file: number;
  invalid: number;
  columns: { column: string; field: string | null }[];
  warnings: string[];
  rows: LeadImportRow[];
};

export type LeadImportResult = {
  upload_id: string;
  total_rows: number;
  saved: number;
  skipped_duplicate_existing: number;
  skipped_duplicate_in_file: number;
  skipped_invalid: number;
};

function importForm(file: File): FormData {
  const form = new FormData();
  form.append("file", file);
  return form;
}

export function previewLeadImport(projectId: string, file: File) {
  return apiRequest<LeadImportPreview>("/leads/import/preview", {
    method: "POST",
    body: importForm(file),
    projectId,
  });
}

export function commitLeadImport(projectId: string, file: File) {
  return apiRequest<LeadImportResult>("/leads/import/commit", {
    method: "POST",
    body: importForm(file),
    projectId,
  });
}
