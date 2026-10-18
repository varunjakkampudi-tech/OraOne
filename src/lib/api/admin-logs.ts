// Admin log viewer API. Only platform super_admin and admin accounts can call these; the
// server checks the role on every request and redacts every field it returns.

import { API_BASE, ApiError, apiRequest } from "./client";
import type { DownloadFormat } from "@/lib/admin-logs";

export type ErrorEvent = {
  id: string;
  request_id: string;
  occurred_at: string;
  method: string;
  route: string;
  status_code: number;
  duration_ms: number;
  exception_type: string | null;
  message: string | null;
  release_version: string;
  trace_id: string | null;
  actor_hash: string | null;
  org_hash: string | null;
};

export type ErrorDetail = ErrorEvent & { stack_trace: string | null };

export type ErrorListResponse = {
  items: ErrorEvent[];
  total: number;
  limit: number;
  offset: number;
  range: { start: string; end: string };
};

export type ErrorDetailResponse = {
  error: ErrorDetail;
  related_logs: Array<Record<string, unknown>>;
  log_file_configured: boolean;
};

export function listAdminErrors(query: string): Promise<ErrorListResponse> {
  return apiRequest<ErrorListResponse>(`/admin/logs/errors?${query}`);
}

export function getAdminError(requestId: string): Promise<ErrorDetailResponse> {
  return apiRequest<ErrorDetailResponse>(`/admin/logs/errors/${encodeURIComponent(requestId)}`);
}

function filenameFrom(disposition: string | null, format: DownloadFormat): string {
  const match = disposition?.match(/filename="([^"]+)"/);
  return match?.[1] ?? `oraone-error-logs.${format}`;
}

async function failureMessage(response: Response): Promise<string> {
  if (response.status === 403) return "Only platform administrators can download error logs.";
  if (response.status === 422) return "That time range is not allowed. Choose a shorter range.";
  if (response.status === 401) return "Sign in again to download error logs.";
  return "The download could not be completed. Try again shortly.";
}

/**
 * Fetches the file and hands it to the browser as a save. The request stays cookie-based
 * like every other API call, and the object URL is released straight after the click.
 */
export async function downloadAdminErrors(
  format: DownloadFormat,
  query: string,
): Promise<{ filename: string; truncated: boolean }> {
  const response = await fetch(`${API_BASE}/admin/logs/download?${query}`, {
    method: "GET",
    credentials: "include",
    headers: { Accept: format === "json" ? "application/json" : "text/csv" },
  });
  if (!response.ok) {
    throw new ApiError(response.status, await failureMessage(response));
  }
  const blob = await response.blob();
  const filename = filenameFrom(response.headers.get("Content-Disposition"), format);
  const truncated = response.headers.get("X-Truncated") === "true";

  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
  return { filename, truncated };
}
