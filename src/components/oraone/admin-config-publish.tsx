import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { messageOf } from "@/lib/api/client";
import {
  discardAdminDraft,
  listAdminDrafts,
  listAdminPublishHistory,
  publishAdminDrafts,
  type PublishResult,
} from "@/lib/api/admin-config";
import {
  REASON_MAX_LENGTH,
  REASON_MIN_LENGTH,
  changedDraftCount,
  draftDiffRows,
  publishChangeLabel,
  publishProblems,
  type ConfigEnvironment,
  type DraftEntry,
  type DraftList,
  type PublishEvent,
  type PublishHistory,
} from "@/lib/admin-config";

type DraftState =
  { kind: "loading" } | { kind: "ready"; data: DraftList } | { kind: "error"; message: string };

type HistoryState =
  | { kind: "loading" }
  | { kind: "ready"; data: PublishHistory }
  | { kind: "error"; message: string };

/** Pending drafts for one environment, with discard and the publish entry point. */
export function DraftsPanel({
  environment,
  refreshKey,
  onChanged,
}: {
  environment: ConfigEnvironment;
  refreshKey: number;
  onChanged: (message: string) => void;
}) {
  const [state, setState] = useState<DraftState>({ kind: "loading" });
  const [discarding, setDiscarding] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [publishOpen, setPublishOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await listAdminDrafts(environment);
      setState({ kind: "ready", data });
    } catch (caught) {
      setState({ kind: "error", message: messageOf(caught, "Drafts could not be loaded.") });
    }
  }, [environment]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  async function discard(name: string) {
    setDiscarding(name);
    setError(null);
    try {
      await discardAdminDraft(name, environment);
      onChanged(`Discarded the draft for ${name}. The active value did not change.`);
    } catch (caught) {
      setError(messageOf(caught, "The draft could not be discarded. Nothing was changed."));
    } finally {
      setDiscarding(null);
    }
  }

  if (state.kind === "loading") {
    return (
      <p role="status" aria-live="polite" className="mb-4 text-sm text-muted-foreground">
        Loading drafts...
      </p>
    );
  }

  if (state.kind === "error") {
    return (
      <div role="alert" className="mb-4 rounded-md border border-destructive p-4 text-sm">
        <p>{state.message}</p>
        <Button type="button" variant="outline" className="mt-3" onClick={() => void load()}>
          Try again
        </Button>
      </div>
    );
  }

  const entries = state.data.drafts;
  const rows = draftDiffRows(entries);
  const unreadable = entries.some((entry) => !entry.readable);
  const changed = changedDraftCount(entries);

  return (
    <section aria-labelledby="drafts-heading" className="mb-8 rounded-md border p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 id="drafts-heading" className="text-base font-semibold">
            Pending drafts
          </h3>
          <p className="text-sm text-muted-foreground">
            {entries.length === 0
              ? "No drafts for this environment. Saving a change creates a draft."
              : `${entries.length} draft${entries.length === 1 ? "" : "s"} waiting to be published. Drafts do not change the running app.`}
          </p>
        </div>
        <Button
          type="button"
          disabled={entries.length === 0 || unreadable}
          onClick={() => setPublishOpen(true)}
        >
          Review and publish
        </Button>
      </div>

      {unreadable && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          A draft cannot be read with the current encryption key. Discard it and save it again
          before publishing.
        </p>
      )}
      {error && (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {error}
        </p>
      )}

      {rows.length > 0 && (
        <ul className="mt-4 divide-y rounded-md border">
          {rows.map((row) => (
            <li
              key={row.name}
              className="flex flex-col gap-2 p-3 sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="min-w-0 flex-1 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <code className="break-all font-semibold">{row.name}</code>
                  <span className="rounded bg-muted px-1.5 py-0.5 text-xs">{row.actionLabel}</span>
                  {!row.changed && (
                    <span className="text-xs text-muted-foreground">No effective change</span>
                  )}
                </div>
                <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
                  <dt className="text-muted-foreground">Now</dt>
                  <dd className="break-all">{row.before}</dd>
                  <dt className="text-muted-foreground">Draft</dt>
                  <dd className="break-all">{row.after}</dd>
                </dl>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={discarding !== null}
                aria-label={`Discard draft for ${row.name}`}
                onClick={() => void discard(row.name)}
              >
                {discarding === row.name ? "Discarding..." : "Discard draft"}
              </Button>
            </li>
          ))}
        </ul>
      )}

      {publishOpen && (
        <PublishDialog
          environment={environment}
          entries={entries}
          changedCount={changed}
          onClose={() => setPublishOpen(false)}
          onPublished={(result) => {
            setPublishOpen(false);
            onChanged(
              `Published ${result.published_count} change(s) to ${environment}. Restart the API so they apply.`,
            );
          }}
        />
      )}
    </section>
  );
}

/** Shows the diff, then requires the environment name and a reason before publishing. */
export function PublishDialog({
  environment,
  entries,
  changedCount,
  onClose,
  onPublished,
}: {
  environment: ConfigEnvironment;
  entries: DraftEntry[];
  changedCount: number;
  onClose: () => void;
  onPublished: (result: PublishResult) => void;
}) {
  const [confirm, setConfirm] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const rows = draftDiffRows(entries);
  const problems = publishProblems({
    environment,
    confirm,
    reason,
    draftCount: entries.length,
  });

  function submit() {
    if (problems.length > 0 || busy) return;
    setBusy(true);
    setError(null);
    publishAdminDrafts({
      environment,
      confirm,
      reason: reason.trim(),
      reviewed: entries.map((entry) => entry.name),
    })
      .then((result) => onPublished(result))
      .catch((caught: unknown) =>
        setError(
          messageOf(
            caught,
            "The publish was not applied. Nothing was changed. Review the drafts again.",
          ),
        ),
      )
      .finally(() => setBusy(false));
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Publish to {environment === "local" ? "Local" : "Production"}</DialogTitle>
          <DialogDescription>
            {entries.length} change{entries.length === 1 ? "" : "s"} ({changedCount} with an
            effective change). Publishing makes them active. The API must restart before they apply.
          </DialogDescription>
        </DialogHeader>

        <ul className="divide-y rounded-md border text-sm">
          {rows.map((row) => (
            <li key={row.name} className="p-3">
              <div className="flex flex-wrap items-center gap-2">
                <code className="break-all font-semibold">{row.name}</code>
                <span className="rounded bg-muted px-1.5 py-0.5 text-xs">{row.actionLabel}</span>
              </div>
              <p className="mt-1 break-all text-muted-foreground">
                {row.before} <span aria-hidden="true">→</span> {row.after}
              </p>
            </li>
          ))}
        </ul>

        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <div className="grid gap-1">
            <Label htmlFor="publish-confirm">Type {environment} to confirm</Label>
            <Input
              id="publish-confirm"
              autoComplete="off"
              spellCheck={false}
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              aria-describedby="publish-confirm-help"
            />
            <p id="publish-confirm-help" className="text-xs text-muted-foreground">
              Must match the environment name exactly.
            </p>
          </div>

          <div className="grid gap-1">
            <Label htmlFor="publish-reason">Reason</Label>
            <Textarea
              id="publish-reason"
              rows={3}
              maxLength={REASON_MAX_LENGTH}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              aria-describedby="publish-reason-help"
            />
            <p id="publish-reason-help" className="text-xs text-muted-foreground">
              {REASON_MIN_LENGTH} to {REASON_MAX_LENGTH} characters. Recorded in the publish
              history. Do not put secrets in it.
            </p>
          </div>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          {problems.length > 0 && (confirm || reason) && (
            <ul className="list-disc pl-5 text-xs text-muted-foreground">
              {problems.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          )}

          <DialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy || problems.length > 0}>
              {busy ? "Publishing..." : "Publish changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** The last 50 publishes for one environment. Key names and reasons only. */
export function PublishHistoryPanel({
  environment,
  refreshKey,
}: {
  environment: ConfigEnvironment;
  refreshKey: number;
}) {
  const [state, setState] = useState<HistoryState>({ kind: "loading" });

  const load = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const data = await listAdminPublishHistory(environment);
      setState({ kind: "ready", data });
    } catch (caught) {
      setState({ kind: "error", message: messageOf(caught, "History could not be loaded.") });
    }
  }, [environment]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  return (
    <section aria-labelledby="publish-history-heading" className="mb-8">
      <h3 id="publish-history-heading" className="mb-2 text-base font-semibold">
        Publish history
      </h3>
      {state.kind === "loading" && (
        <p role="status" className="text-sm text-muted-foreground">
          Loading history...
        </p>
      )}
      {state.kind === "error" && (
        <div role="alert" className="text-sm text-destructive">
          <p>{state.message}</p>
          <Button type="button" variant="outline" className="mt-2" onClick={() => void load()}>
            Try again
          </Button>
        </div>
      )}
      {state.kind === "ready" && state.data.items.length === 0 && (
        <p className="text-sm text-muted-foreground">No publishes yet for this environment.</p>
      )}
      {state.kind === "ready" && state.data.items.length > 0 && (
        <ol className="divide-y rounded-md border">
          {state.data.items.map((event) => (
            <HistoryItem key={event.id} event={event} />
          ))}
        </ol>
      )}
    </section>
  );
}

function HistoryItem({ event }: { event: PublishEvent }) {
  const when = new Date(event.published_at);
  return (
    <li className="p-3 text-sm">
      <p className="font-medium">
        <time dateTime={event.published_at}>
          {Number.isNaN(when.getTime()) ? event.published_at : when.toLocaleString()}
        </time>{" "}
        <span className="font-normal text-muted-foreground">by {event.published_by_email}</span>
      </p>
      <p className="mt-1 text-muted-foreground">{event.reason}</p>
      <ul className="mt-2 flex flex-wrap gap-2">
        {event.changes.map((change) => (
          <li key={`${change.name}-${change.change}`}>
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
              {publishChangeLabel(change)}
            </code>
          </li>
        ))}
      </ul>
    </li>
  );
}
