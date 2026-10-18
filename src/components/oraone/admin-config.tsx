import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { LockKeyhole, RefreshCw, ShieldCheck } from "lucide-react";
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
import { ApiError, messageOf } from "@/lib/api/client";
import {
  listAdminConfig,
  reloadAdminConfig,
  saveAdminConfigDraft,
  type DraftSaveResult,
} from "@/lib/api/admin-config";
import {
  REASON_MAX_LENGTH,
  REASON_MIN_LENGTH,
  groupItems,
  maskedDisplay,
  removeProblems,
  sourceLabel,
  statusLabel,
  writeProblems,
  type ConfigEnvironment,
  type ConfigItem,
  type ConfigList,
} from "@/lib/admin-config";
import { DraftsPanel, PublishHistoryPanel } from "@/components/oraone/admin-config-publish";

const ENVIRONMENT_COPY: Record<ConfigEnvironment, string> = {
  local: "Local values come from this server and from console changes published for local.",
  production:
    "Production values are never shown here. Each key shows only whether it is set, because the deployment's secret store holds them.",
};

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; data: ConfigList }
  | { kind: "signin"; message: string }
  | { kind: "error"; message: string };

export function AdminConfigPanel() {
  const [environment, setEnvironment] = useState<ConfigEnvironment>("local");
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<ConfigItem | null>(null);
  const [reloadOpen, setReloadOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async (env: ConfigEnvironment) => {
    setState({ kind: "loading" });
    try {
      const data = await listAdminConfig(env);
      setState({ kind: "ready", data });
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        setState({
          kind: "signin",
          message:
            error.status === 403
              ? "This account is not a super-admin. Only super-admins can view or change configuration."
              : "Sign in with a super-admin account to view configuration.",
        });
      } else {
        setState({
          kind: "error",
          message: messageOf(error, "Configuration could not be loaded. Try again shortly."),
        });
      }
    }
  }, []);

  useEffect(() => {
    void load(environment);
  }, [environment, load]);

  /** After a draft, publish or discard: say what happened and refresh every panel. */
  const changed = useCallback(
    (message: string) => {
      setNotice(message);
      setRefreshKey((key) => key + 1);
      void load(environment);
    },
    [environment, load],
  );

  const groups = useMemo(
    () => (state.kind === "ready" ? groupItems(state.data, query) : []),
    [state, query],
  );

  return (
    <section aria-labelledby="admin-config-heading" className="admin-section">
      <h2 id="admin-config-heading">Application configuration</h2>
      <p className="admin-table-summary">
        Settings the API reads from its environment. Secrets are never shown in full. Saving a
        change creates a draft. A draft changes nothing until it is published, and published values
        take effect after the API restarts.
      </p>

      <div role="group" aria-label="Environment" className="mb-4 flex flex-wrap gap-2">
        {(["local", "production"] as ConfigEnvironment[]).map((env) => (
          <Button
            key={env}
            type="button"
            variant={environment === env ? "default" : "outline"}
            aria-pressed={environment === env}
            onClick={() => {
              setNotice(null);
              setEnvironment(env);
            }}
          >
            {env === "local" ? "Local" : "Production"}
          </Button>
        ))}
      </div>
      <p className="mb-4 text-sm text-muted-foreground">{ENVIRONMENT_COPY[environment]}</p>

      {state.kind === "ready" && state.data.restart_required && (
        <div
          role="status"
          className="mb-4 rounded-md border border-amber-500 bg-amber-50 p-4 text-sm text-amber-950 dark:bg-amber-950/40 dark:text-amber-100"
        >
          <strong>Restart required.</strong> Published changes apply when the API restarts. Restart
          every API worker, then reload this page.
        </div>
      )}
      {notice && (
        <div role="status" className="mb-4 rounded-md border p-4 text-sm">
          {notice}
        </div>
      )}

      {state.kind === "signin" && (
        <div className="admin-access-notice">
          <ShieldCheck />
          <div>
            <strong>Super-admin access required</strong>
            <p>{state.message}</p>
          </div>
          <Button asChild variant="outline">
            <Link to="/auth/sign-in">Sign in</Link>
          </Button>
        </div>
      )}

      {state.kind === "error" && (
        <div role="alert" className="rounded-md border border-destructive p-4 text-sm">
          <p>{state.message}</p>
          <Button
            type="button"
            variant="outline"
            className="mt-3"
            onClick={() => void load(environment)}
          >
            Try again
          </Button>
        </div>
      )}

      {state.kind === "loading" && (
        <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
          Loading configuration...
        </p>
      )}

      {state.kind === "ready" && (
        <>
          <DraftsPanel environment={environment} refreshKey={refreshKey} onChanged={changed} />
          <PublishHistoryPanel environment={environment} refreshKey={refreshKey} />

          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div className="w-full sm:max-w-sm">
              <Label htmlFor="admin-config-search">Search settings</Label>
              <Input
                id="admin-config-search"
                type="search"
                value={query}
                placeholder="Name, group or description"
                onChange={(event) => setQuery(event.target.value)}
                className="mt-1"
              />
            </div>
            {environment === "local" && (
              <Button type="button" variant="outline" onClick={() => setReloadOpen(true)}>
                <RefreshCw />
                Reload from store
              </Button>
            )}
          </div>

          {!state.data.deployment_visible && (
            <p className="mb-4 text-sm text-muted-foreground">
              This server runs as {state.data.runtime_environment}. For {state.data.environment},
              only values saved in the console are visible here.
            </p>
          )}

          {groups.length === 0 && (
            <p className="text-sm text-muted-foreground">No settings match that search.</p>
          )}

          {groups.map((section) => (
            <section
              key={section.group}
              aria-labelledby={`cfg-${slug(section.group)}`}
              className="mb-8"
            >
              <h3 id={`cfg-${slug(section.group)}`} className="mb-2 text-base font-semibold">
                {section.group}
              </h3>
              <ul className="divide-y rounded-md border">
                {section.items.map((item) => (
                  <ConfigRow
                    key={item.name}
                    item={item}
                    environment={environment}
                    onEdit={() => setEditing(item)}
                  />
                ))}
              </ul>
            </section>
          ))}
        </>
      )}

      {editing && state.kind === "ready" && (
        <EditDialog
          item={editing}
          environment={environment}
          onClose={() => setEditing(null)}
          onSaved={(result: DraftSaveResult) => {
            setEditing(null);
            changed(
              result.status === "unchanged"
                ? `Nothing is published for ${result.name}, so there is nothing to remove.`
                : result.status === "draft_removal_saved"
                  ? `Draft saved to remove ${result.name}. Publish it to apply.`
                  : `Draft saved for ${result.name}. Publish it to apply.`,
            );
          }}
        />
      )}

      {reloadOpen && (
        <ReloadDialog
          onClose={() => setReloadOpen(false)}
          onReloaded={(reloaded) => {
            setReloadOpen(false);
            setNotice(
              reloaded.length
                ? `Reloaded this server: ${reloaded.length} setting(s) changed. Restart all workers to apply everything.`
                : "Reloaded this server. Nothing changed. Restart all workers to apply published changes.",
            );
            void load(environment);
          }}
        />
      )}
    </section>
  );
}

function ConfigRow({
  item,
  environment,
  onEdit,
}: {
  item: ConfigItem;
  environment: ConfigEnvironment;
  onEdit: () => void;
}) {
  const status = statusLabel(item);
  const toneClass =
    status.tone === "ok"
      ? "text-emerald-700 dark:text-emerald-300"
      : status.tone === "missing"
        ? "text-destructive"
        : "text-muted-foreground";
  return (
    <li className="flex flex-col gap-2 p-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <code className="break-all text-sm font-semibold">{item.name}</code>
          {item.kind === "secret" && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs">Secret</span>
          )}
          {item.required && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-xs">Required</span>
          )}
          <span className={`text-xs font-medium ${toneClass}`}>{status.label}</span>
          {item.draft_pending && (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-950 dark:bg-amber-950/60 dark:text-amber-100">
              Draft pending
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Value</dt>
          <dd className="break-all">{maskedDisplay(item)}</dd>
          <dt className="text-muted-foreground">Source</dt>
          <dd>{sourceLabel(item)}</dd>
          {item.kind === "plain" && environment === "production" && (
            <>
              <dt className="sr-only">Note</dt>
              <dd className="text-xs text-muted-foreground">Hidden for production.</dd>
            </>
          )}
        </dl>
      </div>
      <div className="shrink-0">
        {item.console_managed ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full sm:w-auto"
            onClick={onEdit}
            aria-label={`Edit ${item.name}`}
          >
            Edit
          </Button>
        ) : (
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            <LockKeyhole className="size-3" aria-hidden="true" />
            Managed outside the console
          </p>
        )}
      </div>
    </li>
  );
}

function EditDialog({
  item,
  environment,
  onClose,
  onSaved,
}: {
  item: ConfigItem;
  environment: ConfigEnvironment;
  onClose: () => void;
  onSaved: (result: DraftSaveResult) => void;
}) {
  const [value, setValue] = useState("");
  const [confirm, setConfirm] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const problems = writeProblems({
    name: item.name,
    kind: item.kind,
    value,
    confirm,
    reason,
  });
  const removal = removeProblems({ name: item.name, confirm, reason });

  async function submit(nextValue: string | null) {
    setBusy(true);
    setError(null);
    try {
      const result = await saveAdminConfigDraft(item.name, {
        environment,
        value: nextValue,
        confirm,
        reason: reason.trim(),
      });
      setValue("");
      onSaved(result);
    } catch (caught) {
      setError(messageOf(caught, "The change could not be saved. Nothing was changed."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            Edit <code className="break-all">{item.name}</code>
          </DialogTitle>
          <DialogDescription>
            {environment === "local" ? "Local" : "Production"} · {item.description}
          </DialogDescription>
        </DialogHeader>

        <p className="text-sm text-muted-foreground">
          Current: {maskedDisplay(item)}. Saving creates a draft. Nothing changes until someone
          publishes it, and published values apply after the API restarts. Do not paste other
          secrets into the reason field.
        </p>

        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (problems.length === 0 && !busy) void submit(value);
          }}
        >
          <div className="grid gap-1">
            <Label htmlFor="cfg-value">New value</Label>
            <Input
              id="cfg-value"
              type={item.kind === "secret" ? "password" : "text"}
              autoComplete="off"
              spellCheck={false}
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
          </div>

          <div className="grid gap-1">
            <Label htmlFor="cfg-confirm">Type {item.name} to confirm</Label>
            <Input
              id="cfg-confirm"
              autoComplete="off"
              spellCheck={false}
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
              aria-describedby="cfg-confirm-help"
            />
            <p id="cfg-confirm-help" className="text-xs text-muted-foreground">
              Must match the key name exactly.
            </p>
          </div>

          <div className="grid gap-1">
            <Label htmlFor="cfg-reason">Reason</Label>
            <Textarea
              id="cfg-reason"
              rows={3}
              maxLength={REASON_MAX_LENGTH}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              aria-describedby="cfg-reason-help"
            />
            <p id="cfg-reason-help" className="text-xs text-muted-foreground">
              {REASON_MIN_LENGTH} to {REASON_MAX_LENGTH} characters. This is recorded in the audit
              log.
            </p>
          </div>

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}

          {problems.length > 0 && (value || confirm || reason) && (
            <ul className="list-disc pl-5 text-xs text-muted-foreground">
              {problems.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          )}

          <DialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-between">
            {item.overridden ? (
              <Button
                type="button"
                variant="outline"
                disabled={busy || removal.length > 0}
                onClick={() => void submit(null)}
              >
                Draft removal of saved value
              </Button>
            ) : (
              <span />
            )}
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
                Cancel
              </Button>
              <Button type="submit" disabled={busy || problems.length > 0}>
                {busy ? "Saving draft..." : "Save draft"}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ReloadDialog({
  onClose,
  onReloaded,
}: {
  onClose: () => void;
  onReloaded: (changed: string[]) => void;
}) {
  const [confirm, setConfirm] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const problems = removeProblems({ name: "RELOAD", confirm, reason });

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Reload from store</DialogTitle>
          <DialogDescription>
            Reads saved console values into this API process only. Other workers keep their values
            until they restart.
          </DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            if (problems.length > 0 || busy) return;
            setBusy(true);
            setError(null);
            reloadAdminConfig({ confirm, reason: reason.trim() })
              .then((result) => onReloaded(result.changed_keys))
              .catch((caught: unknown) =>
                setError(messageOf(caught, "Reload failed. Nothing was changed.")),
              )
              .finally(() => setBusy(false));
          }}
        >
          <div className="grid gap-1">
            <Label htmlFor="reload-confirm">Type RELOAD to confirm</Label>
            <Input
              id="reload-confirm"
              autoComplete="off"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
            />
          </div>
          <div className="grid gap-1">
            <Label htmlFor="reload-reason">Reason</Label>
            <Textarea
              id="reload-reason"
              rows={2}
              maxLength={REASON_MAX_LENGTH}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <DialogFooter className="flex flex-col gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy || problems.length > 0}>
              {busy ? "Reloading..." : "Reload this server"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function slug(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}
