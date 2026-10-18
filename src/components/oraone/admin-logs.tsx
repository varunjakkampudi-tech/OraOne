import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Copy, Download, RefreshCw, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, messageOf } from "@/lib/api/client";
import {
  downloadAdminErrors,
  getAdminError,
  listAdminErrors,
  type ErrorDetailResponse,
  type ErrorEvent,
  type ErrorListResponse,
} from "@/lib/api/admin-logs";
import {
  DEFAULT_LOG_FILTERS,
  LIST_PAGE_SIZE,
  RANGE_PRESETS,
  STATUS_OPTIONS,
  downloadLabel,
  downloadNotice,
  downloadQuery,
  errorListQuery,
  formatDuration,
  hasNextPage,
  requestIdProblem,
  type DownloadFormat,
  type LogFilters,
  type StatusFilter,
} from "@/lib/admin-logs";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; data: ErrorListResponse }
  | { kind: "forbidden"; message: string }
  | { kind: "error"; message: string };

type DetailState =
  | { kind: "loading"; requestId: string }
  | { kind: "ready"; requestId: string; data: ErrorDetailResponse }
  | { kind: "error"; requestId: string; message: string };

function formatTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

function statusTone(status: number): "destructive" | "secondary" {
  return status >= 500 ? "destructive" : "secondary";
}

export function AdminLogsPanel() {
  const [draft, setDraft] = useState<LogFilters>(DEFAULT_LOG_FILTERS);
  const [applied, setApplied] = useState<LogFilters>(DEFAULT_LOG_FILTERS);
  const [page, setPage] = useState(0);
  const [refreshKey, setRefreshKey] = useState(0);
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [download, setDownload] = useState<{
    busy: DownloadFormat | null;
    notice: string | null;
    error: string | null;
  }>({ busy: null, notice: null, error: null });

  const requestIdError = requestIdProblem(draft.requestId);

  const load = useCallback(async (filters: LogFilters, pageIndex: number) => {
    setState({ kind: "loading" });
    try {
      const data = await listAdminErrors(errorListQuery(filters, new Date(), pageIndex));
      setState({ kind: "ready", data });
    } catch (error) {
      if (error instanceof ApiError && error.status === 403) {
        setState({
          kind: "forbidden",
          message: "Only platform administrators can view error logs.",
        });
      } else {
        setState({
          kind: "error",
          message: messageOf(error, "Error logs could not be loaded. Try again shortly."),
        });
      }
    }
  }, []);

  useEffect(() => {
    void load(applied, page);
  }, [applied, page, refreshKey, load]);

  function onApply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (requestIdError) return;
    setDownload({ busy: null, notice: null, error: null });
    setPage(0);
    setApplied({ ...draft, route: draft.route.trim(), requestId: draft.requestId.trim() });
  }

  function onReset() {
    setDraft(DEFAULT_LOG_FILTERS);
    setApplied(DEFAULT_LOG_FILTERS);
    setPage(0);
    setDownload({ busy: null, notice: null, error: null });
  }

  async function openDetail(requestId: string) {
    setDetail({ kind: "loading", requestId });
    try {
      const data = await getAdminError(requestId);
      setDetail({ kind: "ready", requestId, data });
    } catch (error) {
      setDetail({
        kind: "error",
        requestId,
        message:
          error instanceof ApiError && error.status === 404
            ? "No error was recorded for that request ID."
            : messageOf(error, "That error could not be loaded. Try again shortly."),
      });
    }
  }

  async function onDownload(format: DownloadFormat) {
    setDownload({ busy: format, notice: null, error: null });
    try {
      const result = await downloadAdminErrors(format, downloadQuery(applied, new Date(), format));
      setDownload({
        busy: null,
        notice: downloadNotice(format, result.truncated),
        error: null,
      });
    } catch (error) {
      setDownload({
        busy: null,
        notice: null,
        error: messageOf(error, "The download could not be completed. Try again shortly."),
      });
    }
  }

  async function copyRequestId(requestId: string) {
    try {
      await navigator.clipboard.writeText(requestId);
    } catch {
      // Clipboard access can be refused; the ID stays visible for manual copy.
    }
  }

  const ready = state.kind === "ready" ? state.data : null;
  const canDownload = state.kind === "ready" && ready !== null && ready.total > 0;

  return (
    <section aria-labelledby="admin-logs-heading" className="admin-section">
      <h2 id="admin-logs-heading">Error logs</h2>
      <p className="admin-table-summary">
        Server errors (5xx) and unhandled exceptions, newest first. Messages and stack traces are
        scrubbed of email addresses, tokens and query strings. Each download holds up to 10,000
        records.
      </p>

      <form onSubmit={onApply} className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="grid gap-1">
          <Label htmlFor="admin-logs-range">Time range</Label>
          <select
            id="admin-logs-range"
            className="h-9 rounded-md border bg-background px-3 text-sm"
            value={draft.range}
            onChange={(event) =>
              setDraft({ ...draft, range: event.target.value as LogFilters["range"] })
            }
          >
            {RANGE_PRESETS.map((preset) => (
              <option key={preset.value} value={preset.value}>
                {preset.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-1">
          <Label htmlFor="admin-logs-route">Route</Label>
          <Input
            id="admin-logs-route"
            placeholder="/api/admin/logs"
            maxLength={255}
            value={draft.route}
            onChange={(event) => setDraft({ ...draft, route: event.target.value })}
          />
        </div>

        <div className="grid gap-1">
          <Label htmlFor="admin-logs-status">Status</Label>
          <select
            id="admin-logs-status"
            className="h-9 rounded-md border bg-background px-3 text-sm"
            value={draft.status}
            onChange={(event) => setDraft({ ...draft, status: event.target.value as StatusFilter })}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option === "any" ? "Any server error" : option}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-1">
          <Label htmlFor="admin-logs-request-id">Request ID</Label>
          <Input
            id="admin-logs-request-id"
            placeholder="req-7f3a9c10"
            maxLength={128}
            autoComplete="off"
            spellCheck={false}
            aria-invalid={requestIdError ? true : undefined}
            aria-describedby={requestIdError ? "admin-logs-request-id-error" : undefined}
            value={draft.requestId}
            onChange={(event) => setDraft({ ...draft, requestId: event.target.value })}
          />
          {requestIdError && (
            <p id="admin-logs-request-id-error" role="alert" className="text-xs text-destructive">
              {requestIdError}
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-2 sm:col-span-2 lg:col-span-4">
          <Button type="submit" disabled={Boolean(requestIdError)}>
            <Search className="size-4" aria-hidden="true" />
            Apply filters
          </Button>
          <Button type="button" variant="outline" onClick={onReset}>
            Reset
          </Button>
        </div>
      </form>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={!canDownload || download.busy !== null}
          onClick={() => void onDownload("json")}
        >
          <Download className="size-4" aria-hidden="true" />
          {download.busy === "json" ? "Preparing JSON..." : downloadLabel("json")}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={!canDownload || download.busy !== null}
          onClick={() => void onDownload("csv")}
        >
          <Download className="size-4" aria-hidden="true" />
          {download.busy === "csv" ? "Preparing CSV..." : downloadLabel("csv")}
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => setRefreshKey((key) => key + 1)}
          aria-label="Refresh error list"
        >
          <RefreshCw className="size-4" aria-hidden="true" />
        </Button>
      </div>

      {download.notice && (
        <p role="status" aria-live="polite" className="mb-4 text-sm text-muted-foreground">
          {download.notice}
        </p>
      )}
      {download.error && (
        <p role="alert" className="mb-4 text-sm text-destructive">
          {download.error}
        </p>
      )}

      {state.kind === "loading" && (
        <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
          Loading error records...
        </p>
      )}

      {(state.kind === "forbidden" || state.kind === "error") && (
        <div role="alert" className="rounded-md border border-destructive p-4 text-sm">
          <p>{state.message}</p>
          {state.kind === "error" && (
            <Button
              type="button"
              variant="outline"
              className="mt-3"
              onClick={() => void load(applied, page)}
            >
              Try again
            </Button>
          )}
        </div>
      )}

      {ready && ready.items.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No server errors match these filters in the selected time range.
        </p>
      )}

      {ready && ready.items.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Route</TableHead>
                <TableHead>Request ID</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {ready.items.map((item: ErrorEvent) => (
                <TableRow key={item.id}>
                  <TableCell className="whitespace-nowrap">
                    {formatTime(item.occurred_at)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusTone(item.status_code)}>{item.status_code}</Badge>
                  </TableCell>
                  <TableCell className="break-all font-mono text-xs">
                    {item.method} {item.route}
                  </TableCell>
                  <TableCell className="break-all font-mono text-xs">{item.request_id}</TableCell>
                  <TableCell className="max-w-[28rem] break-words text-sm">
                    {item.exception_type ? `${item.exception_type}: ` : ""}
                    {item.message ?? "No message recorded"}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-sm">
                    {formatDuration(item.duration_ms)}
                  </TableCell>
                  <TableCell>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void openDetail(item.request_id)}
                    >
                      Details
                      <span className="sr-only"> for request {item.request_id}</span>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <nav
            aria-label="Error log pages"
            className="admin-pagination mt-4 flex items-center justify-between gap-3 text-sm"
          >
            <span className="text-muted-foreground">
              Showing {page * LIST_PAGE_SIZE + 1} to {page * LIST_PAGE_SIZE + ready.items.length} of{" "}
              {ready.total}
            </span>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((current) => Math.max(0, current - 1))}
              >
                Previous
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!hasNextPage(ready.total, page)}
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </Button>
            </div>
          </nav>
        </>
      )}

      <Dialog open={detail !== null} onOpenChange={(open) => !open && setDetail(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>Error details</DialogTitle>
            <DialogDescription className="break-all font-mono text-xs">
              {detail?.requestId}
            </DialogDescription>
          </DialogHeader>

          {detail?.kind === "loading" && (
            <p role="status" className="text-sm text-muted-foreground">
              Loading...
            </p>
          )}
          {detail?.kind === "error" && (
            <p role="alert" className="text-sm text-destructive">
              {detail.message}
            </p>
          )}
          {detail?.kind === "ready" && <ErrorDetailBody detail={detail.data} />}

          {detail && detail.kind !== "loading" && (
            <div className="flex justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void copyRequestId(detail.requestId)}
              >
                <Copy className="size-4" aria-hidden="true" />
                Copy request ID
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}

function ErrorDetailBody({ detail }: { detail: ErrorDetailResponse }) {
  const { error } = detail;
  const fields: Array<[string, string]> = [
    ["Time", formatTime(error.occurred_at)],
    ["Status", String(error.status_code)],
    ["Route", `${error.method} ${error.route}`],
    ["Duration", formatDuration(error.duration_ms)],
    ["Exception", error.exception_type ?? "Not recorded"],
    ["Release", error.release_version],
    ["Trace ID", error.trace_id ?? "Not recorded"],
    ["Actor (hashed)", error.actor_hash ?? "Not recorded"],
    ["Organization (hashed)", error.org_hash ?? "Not recorded"],
  ];

  return (
    <div className="grid gap-4">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {fields.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="break-all">{value}</dd>
          </div>
        ))}
      </dl>

      <div>
        <h3 className="mb-1 text-sm font-semibold">Message</h3>
        <p className="break-words text-sm">{error.message ?? "No message recorded"}</p>
      </div>

      <div>
        <h3 className="mb-1 text-sm font-semibold">Stack trace</h3>
        <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">
          {error.stack_trace ?? "No stack trace recorded."}
        </pre>
      </div>

      <div>
        <h3 className="mb-1 text-sm font-semibold">Related log lines</h3>
        {!detail.log_file_configured && (
          <p className="text-sm text-muted-foreground">
            This server does not write an application log file, so only the error record is
            available.
          </p>
        )}
        {detail.log_file_configured && detail.related_logs.length === 0 && (
          <p className="text-sm text-muted-foreground">No related log lines were found.</p>
        )}
        {detail.related_logs.map((line, index) => (
          <pre
            key={index}
            className="mb-2 overflow-x-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap"
          >
            {JSON.stringify(line, null, 2)}
          </pre>
        ))}
      </div>
    </div>
  );
}
