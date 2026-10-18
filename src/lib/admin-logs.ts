// Pure helpers for the admin log viewer. The server enforces every limit (time range,
// row cap, platform role) and redacts every field; these functions only shape requests
// and describe what the server returned.

export const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{8,128}$/;
export const LIST_PAGE_SIZE = 50;
/** Mirrors the server's download cap (EXPORT_ROW_CAP). */
export const EXPORT_ROW_CAP = 10_000;

export type RangePreset = "1h" | "24h" | "7d" | "30d";

export const RANGE_PRESETS: ReadonlyArray<{ value: RangePreset; label: string; hours: number }> = [
  { value: "1h", label: "Last hour", hours: 1 },
  { value: "24h", label: "Last 24 hours", hours: 24 },
  { value: "7d", label: "Last 7 days", hours: 24 * 7 },
  { value: "30d", label: "Last 30 days", hours: 24 * 30 },
];

const DEFAULT_PRESET = { value: "24h", label: "Last 24 hours", hours: 24 } as const;

export const STATUS_OPTIONS = ["any", "500", "502", "503", "504"] as const;
export type StatusFilter = (typeof STATUS_OPTIONS)[number];

export type LogFilters = {
  range: RangePreset;
  route: string;
  status: StatusFilter;
  requestId: string;
};

export const DEFAULT_LOG_FILTERS: LogFilters = {
  range: "24h",
  route: "",
  status: "any",
  requestId: "",
};

export type DownloadFormat = "json" | "csv";

const HOUR_MS = 60 * 60 * 1000;

/** The start and end of a preset window, ending at ``now``, as ISO 8601 strings. */
export function rangeBounds(range: RangePreset, now: Date): { start: string; end: string } {
  const preset = RANGE_PRESETS.find((p) => p.value === range) ?? DEFAULT_PRESET;
  const end = new Date(now.getTime());
  const start = new Date(end.getTime() - preset.hours * HOUR_MS);
  return { start: start.toISOString(), end: end.toISOString() };
}

/** Empty string when the ID is usable (or blank), otherwise the reason it is not. */
export function requestIdProblem(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  return REQUEST_ID_PATTERN.test(trimmed)
    ? null
    : "Request IDs are 8 to 128 letters, digits, dots, colons, underscores or hyphens.";
}

/** Query parameters shared by the list and the download. Empty filters are left out. */
export function buildFilterParams(filters: LogFilters, now: Date): URLSearchParams {
  const params = new URLSearchParams();
  const { start, end } = rangeBounds(filters.range, now);
  params.set("start", start);
  params.set("end", end);
  const route = filters.route.trim();
  if (route) params.set("route", route);
  if (filters.status !== "any") params.set("status", filters.status);
  const requestId = filters.requestId.trim();
  if (requestId && requestIdProblem(requestId) === null) params.set("request_id", requestId);
  return params;
}

/** Query string for one page of the error list. */
export function errorListQuery(filters: LogFilters, now: Date, page: number): string {
  const params = buildFilterParams(filters, now);
  params.set("limit", String(LIST_PAGE_SIZE));
  params.set("offset", String(Math.max(0, page) * LIST_PAGE_SIZE));
  return params.toString();
}

/** Query string for a download of every matching row (up to the server cap). */
export function downloadQuery(filters: LogFilters, now: Date, format: DownloadFormat): string {
  const params = buildFilterParams(filters, now);
  params.set("format", format);
  return params.toString();
}

export function hasActiveFilters(filters: LogFilters): boolean {
  return (
    filters.route.trim() !== "" ||
    filters.status !== "any" ||
    filters.requestId.trim() !== "" ||
    filters.range !== DEFAULT_LOG_FILTERS.range
  );
}

export function pageCount(total: number, pageSize: number = LIST_PAGE_SIZE): number {
  return Math.max(1, Math.ceil(total / pageSize));
}

export function hasNextPage(
  total: number,
  page: number,
  pageSize: number = LIST_PAGE_SIZE,
): boolean {
  return (page + 1) * pageSize < total;
}

export function formatDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "not recorded";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

/** Wording for the download button, including the cap when a download would be cut short. */
export function downloadLabel(format: DownloadFormat): string {
  return format === "json" ? "Download JSON" : "Download CSV";
}

export function downloadNotice(format: DownloadFormat, truncated: boolean): string {
  const label = format.toUpperCase();
  return truncated
    ? `Downloaded ${label}. The file holds the first ${EXPORT_ROW_CAP.toLocaleString("en-US")} matching records, oldest first. Narrow the time range to get the rest.`
    : `Downloaded ${label}.`;
}
