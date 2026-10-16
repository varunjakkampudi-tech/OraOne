// Browser client for the OraOne FastAPI backend (backend/).
//
// Sessions live in httpOnly cookies set by the backend, so no token is ever
// read or stored by JavaScript. Requests go same-origin to `/api` (Vite proxies
// it in development; Caddy routes it in production) unless VITE_API_BASE_URL
// names another HTTPS origin.

const configuredBase = (import.meta.env["VITE_API_BASE_URL"] as string | undefined)?.trim();
export const API_BASE = (configuredBase ? configuredBase.replace(/\/+$/, "") : "") + "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function messageOf(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type RequestOptions = {
  method?: Method;
  /** JSON-serialized, except FormData which is sent as multipart (the browser sets the boundary). */
  body?: unknown;
  /** Sent as X-Project-Id; the backend scopes project resources to it. */
  projectId?: string;
  /** Internal: set after one refresh attempt so a retry cannot loop. */
  retried?: boolean;
};

// Paths where a 401 must not trigger a silent session refresh.
const NO_REFRESH_PATHS = ["/auth/email-code/", "/auth/refresh", "/auth/logout"];

let refreshInFlight: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

async function errorMessage(response: Response): Promise<string> {
  if (response.status === 429) return "Too many requests. Please wait a minute and try again.";
  const fallback =
    response.status >= 500
      ? "OraOne couldn't complete that right now. Please try again."
      : "That request couldn't be completed.";
  try {
    // The API returns either { detail } (FastAPI) or { error, message } (provider errors).
    // Some routes answer with a { success, error: { code, message } } envelope.
    const body = (await response.json()) as {
      detail?: unknown;
      message?: unknown;
      error?: { message?: unknown } | unknown;
    };
    const detail = body.detail;
    if (typeof detail === "string" && detail) return detail;
    if (typeof body.message === "string" && body.message) return body.message;
    const envelope = body.error;
    if (envelope && typeof envelope === "object") {
      const nestedMessage = (envelope as { message?: unknown }).message;
      if (typeof nestedMessage === "string" && nestedMessage) return nestedMessage;
    }
    if (detail && typeof detail === "object") {
      const nested = (detail as { message?: unknown }).message;
      if (typeof nested === "string" && nested) return nested;
    }
  } catch {
    // Non-JSON error bodies fall back to the generic message.
  }
  return fallback;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, projectId } = options;
  const headers: Record<string, string> = { Accept: "application/json" };
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  if (body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  if (projectId) headers["X-Project-Id"] = projectId;

  let response: Response;
  try {
    const init: RequestInit = { method, headers, credentials: "include" };
    if (isForm) init.body = body;
    else if (body !== undefined) init.body = JSON.stringify(body);
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(
      0,
      "OraOne can't be reached right now. Check your connection and try again.",
    );
  }

  if (
    response.status === 401 &&
    !options.retried &&
    !NO_REFRESH_PATHS.some((p) => path.startsWith(p))
  ) {
    if (await refreshSession()) {
      return apiRequest<T>(path, { ...options, retried: true });
    }
  }

  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
