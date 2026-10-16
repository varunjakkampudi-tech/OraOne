import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/client";
import {
  connectIntegration,
  disconnectIntegration,
  listIntegrations,
  syncIntegration,
  type IntegrationCatalogEntry,
} from "@/lib/api/integrations";
import {
  createWebhook,
  deleteWebhook,
  listWebhookDeliveries,
  listWebhooks,
  rotateWebhookSecret,
  testWebhook,
  updateWebhook,
  type Webhook,
  type WebhookDelivery,
  type WebhookEventInfo,
  type WebhookWithSecret,
} from "@/lib/api/webhooks";
import { Loading, Notice } from "./studio-ui";
import { when, useWorkspaceId } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";

// Live integrations and webhooks under /studio. Connecting uses the provider's
// real OAuth flow; nothing is marked connected unless the API says so.

function StatusPill({ tone, children }: { tone: "ok" | "muted" | "warn"; children: string }) {
  const cls =
    tone === "ok"
      ? "border-emerald-600 text-emerald-700 dark:text-emerald-400"
      : tone === "warn"
        ? "border-destructive text-destructive"
        : "border-border text-muted-foreground";
  return <span className={`rounded-full border px-2 py-0.5 text-sm ${cls}`}>{children}</span>;
}

function WorkspaceGate({
  workspace,
  children,
}: {
  workspace: ReturnType<typeof useWorkspaceId>;
  children: React.ReactNode;
}) {
  if (workspace.error)
    return (
      <div className="mt-4">
        <Notice kind="error">{workspace.error}</Notice>
      </div>
    );
  if (!workspace.loaded) return <Loading label="Loading your workspace…" />;
  if (!workspace.id) return <p className="mt-6 text-muted-foreground">Create a workspace first.</p>;
  return <>{children}</>;
}

export function IntegrationsPage() {
  const workspace = useWorkspaceId();
  const [entries, setEntries] = useState<IntegrationCatalogEntry[] | null>(null);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmProvider, setConfirmProvider] = useState<string | null>(null);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    setError("");
    listIntegrations(workspace.id)
      .then((res) => {
        if (!cancelled) setEntries(res.items);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load integrations."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, reloadKey]);

  async function connect(entry: IntegrationCatalogEntry) {
    if (!workspace.id) return;
    setBusy(entry.catalog.provider);
    setError("");
    setNotice("");
    try {
      const res = await connectIntegration(workspace.id, entry.catalog.provider);
      if (res.authorize_url) {
        // Leave for the provider's consent screen; the callback returns to the API.
        window.location.assign(res.authorize_url);
        return;
      }
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(messageOf(err, `Couldn't connect ${entry.catalog.name}.`));
    } finally {
      setBusy(null);
    }
  }

  async function sync(entry: IntegrationCatalogEntry) {
    if (!workspace.id || !entry.integration) return;
    setBusy(entry.catalog.provider);
    setError("");
    setNotice("");
    try {
      const job = await syncIntegration(workspace.id, entry.integration.id);
      setNotice(`${entry.catalog.name} sync ${job.status}.`);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(messageOf(err, `Couldn't sync ${entry.catalog.name}.`));
    } finally {
      setBusy(null);
    }
  }

  async function disconnect(entry: IntegrationCatalogEntry) {
    if (!workspace.id || !entry.integration) return;
    setBusy(entry.catalog.provider);
    setError("");
    setNotice("");
    try {
      await disconnectIntegration(workspace.id, entry.integration.id);
      setConfirmProvider(null);
      setNotice(`${entry.catalog.name} disconnected. Its synced documents were removed.`);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(messageOf(err, `Couldn't disconnect ${entry.catalog.name}.`));
    } finally {
      setBusy(null);
    }
  }

  const connectedCount = entries?.filter((e) => e.integration?.status === "connected").length ?? 0;

  return (
    <StudioFrame>
      <span className="marketing-eyebrow">LIVE · INTEGRATIONS</span>
      <h1 className="mt-2 text-3xl font-semibold">Integrations</h1>
      <p className="mt-2 text-muted-foreground">
        Connect the tools that feed your assistants. Only providers marked available can be
        connected.
      </p>
      <WorkspaceGate workspace={workspace}>
        {error && (
          <div className="mt-4">
            <Notice kind="error">{error}</Notice>
          </div>
        )}
        {notice && (
          <div className="mt-4">
            <Notice>{notice}</Notice>
          </div>
        )}
        {entries === null && !error ? (
          <div className="mt-6">
            <Loading label="Loading integrations…" />
          </div>
        ) : entries && entries.length === 0 ? (
          <p className="mt-6 text-muted-foreground">No integrations are available yet.</p>
        ) : entries ? (
          <>
            <p className="mt-6 text-sm text-muted-foreground">{connectedCount} connected</p>
            <ul className="mt-3 grid gap-3 sm:grid-cols-2" aria-label="Integrations">
              {entries.map((entry) => {
                const { catalog, integration } = entry;
                const connected = integration?.status === "connected";
                const isBusy = busy === catalog.provider;
                return (
                  <li
                    key={catalog.provider}
                    className="rounded-lg border border-border bg-card p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h2 className="font-semibold">{catalog.name}</h2>
                        <span className="text-sm text-muted-foreground">
                          {catalog.category} · {catalog.type}
                        </span>
                      </div>
                      {integration ? (
                        <StatusPill tone={connected ? "ok" : "warn"}>
                          {connected ? "Connected" : integration.status}
                        </StatusPill>
                      ) : (
                        <StatusPill tone="muted">
                          {catalog.available ? "Not connected" : "Unavailable"}
                        </StatusPill>
                      )}
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{catalog.description}</p>
                    {integration && (
                      <dl className="mt-3 grid gap-1 text-sm text-muted-foreground">
                        <div>Account: {integration.external_account || "—"}</div>
                        <div>Last synced: {when(integration.last_synced_at)}</div>
                        {integration.last_error && (
                          <div className="text-destructive">Error: {integration.last_error}</div>
                        )}
                      </dl>
                    )}
                    <div className="mt-4 flex flex-wrap gap-2">
                      {integration ? (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={isBusy || !connected}
                            onClick={() => sync(entry)}
                          >
                            Sync now
                          </Button>
                          {confirmProvider === catalog.provider ? (
                            <>
                              <Button
                                variant="destructive"
                                size="sm"
                                disabled={isBusy}
                                onClick={() => disconnect(entry)}
                              >
                                Confirm disconnect
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setConfirmProvider(null)}
                              >
                                Cancel
                              </Button>
                            </>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={isBusy}
                              onClick={() => setConfirmProvider(catalog.provider)}
                            >
                              Disconnect
                            </Button>
                          )}
                        </>
                      ) : (
                        <Button
                          size="sm"
                          disabled={isBusy || !catalog.available}
                          onClick={() => connect(entry)}
                        >
                          {isBusy ? "Connecting…" : catalog.available ? "Connect" : "Not available"}
                        </Button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </>
        ) : null}
      </WorkspaceGate>
    </StudioFrame>
  );
}

function SecretBox({ secret, onDismiss }: { secret: string; onDismiss: () => void }) {
  return (
    <div className="mt-4 rounded-lg border border-border bg-muted p-4 text-sm" role="status">
      <p className="font-medium">Signing secret — copy it now. It won&apos;t be shown again.</p>
      <code className="mt-2 block break-all rounded bg-background p-2">{secret}</code>
      <Button variant="outline" size="sm" className="mt-3" onClick={onDismiss}>
        I&apos;ve saved it
      </Button>
    </div>
  );
}

export function WebhooksPage() {
  const workspace = useWorkspaceId();
  const [hooks, setHooks] = useState<Webhook[] | null>(null);
  const [events, setEvents] = useState<WebhookEventInfo[]>([]);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [secret, setSecret] = useState<{ id: string; value: string } | null>(null);
  const [testResult, setTestResult] = useState<{ id: string; delivery: WebhookDelivery } | null>(
    null,
  );
  const [openDeliveries, setOpenDeliveries] = useState<string | null>(null);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[] | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    setError("");
    listWebhooks(workspace.id)
      .then((res) => {
        if (cancelled) return;
        setHooks(res.webhooks);
        setEvents(res.events);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load webhooks."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, reloadKey]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspace.id || picked.length === 0) return;
    setCreating(true);
    setCreateError("");
    try {
      const res: WebhookWithSecret = await createWebhook(workspace.id, {
        url: url.trim(),
        events: picked,
        description: description.trim() || undefined,
      });
      setSecret({ id: res.webhook.id, value: res.secret });
      setUrl("");
      setDescription("");
      setPicked([]);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setCreateError(messageOf(err, "Couldn't create this endpoint."));
    } finally {
      setCreating(false);
    }
  }

  async function run(id: string, action: () => Promise<unknown>, fallback: string) {
    setBusy(id);
    setError("");
    try {
      await action();
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(messageOf(err, fallback));
    } finally {
      setBusy(null);
    }
  }

  async function rotate(hook: Webhook) {
    setBusy(hook.id);
    setError("");
    try {
      const res = await rotateWebhookSecret(hook.id);
      setSecret({ id: hook.id, value: res.secret });
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(messageOf(err, "Couldn't rotate the signing secret."));
    } finally {
      setBusy(null);
    }
  }

  async function test(hook: Webhook) {
    setBusy(hook.id);
    setError("");
    try {
      const delivery = await testWebhook(hook.id);
      setTestResult({ id: hook.id, delivery });
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(messageOf(err, "The test delivery couldn't be sent."));
    } finally {
      setBusy(null);
    }
  }

  async function toggleDeliveries(hook: Webhook) {
    if (openDeliveries === hook.id) {
      setOpenDeliveries(null);
      return;
    }
    setOpenDeliveries(hook.id);
    setDeliveries(null);
    try {
      setDeliveries(await listWebhookDeliveries(hook.id));
    } catch (err) {
      setDeliveries([]);
      setError(messageOf(err, "Couldn't load recent deliveries."));
    }
  }

  return (
    <StudioFrame>
      <span className="marketing-eyebrow">LIVE · WEBHOOKS</span>
      <h1 className="mt-2 text-3xl font-semibold">Webhooks</h1>
      <p className="mt-2 text-muted-foreground">
        Send workspace events to your own systems. Each request is signed with the endpoint&apos;s
        secret.
      </p>
      <WorkspaceGate workspace={workspace}>
        {error && (
          <div className="mt-4">
            <Notice kind="error">{error}</Notice>
          </div>
        )}
        {secret && <SecretBox secret={secret.value} onDismiss={() => setSecret(null)} />}

        <form
          onSubmit={create}
          className="mt-6 grid max-w-2xl gap-3 rounded-lg border border-border p-4"
        >
          <h2 className="font-semibold">Add endpoint</h2>
          <label className="grid gap-1 text-sm">
            Endpoint URL
            <input
              type="url"
              required
              maxLength={2048}
              placeholder="https://example.com/webhooks/oraone"
              className="rounded-md border border-input bg-background px-3 py-2"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </label>
          <label className="grid gap-1 text-sm">
            Description (optional)
            <input
              maxLength={255}
              className="rounded-md border border-input bg-background px-3 py-2"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </label>
          <fieldset className="grid gap-2 text-sm">
            <legend className="mb-1">Events (choose at least one)</legend>
            {events.map((ev) => (
              <label key={ev.event} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={picked.includes(ev.event)}
                  onChange={(e) =>
                    setPicked((cur) =>
                      e.target.checked ? [...cur, ev.event] : cur.filter((x) => x !== ev.event),
                    )
                  }
                />
                <span>
                  <code className="text-sm">{ev.event}</code>
                  <span className="block text-muted-foreground">{ev.description}</span>
                </span>
              </label>
            ))}
          </fieldset>
          {createError && <Notice kind="error">{createError}</Notice>}
          <div>
            <Button type="submit" disabled={creating || picked.length === 0 || !url.trim()}>
              {creating ? "Adding…" : "Add endpoint"}
            </Button>
          </div>
        </form>

        <div className="mt-8">
          {hooks === null && !error ? (
            <Loading label="Loading webhooks…" />
          ) : hooks && hooks.length === 0 ? (
            <p className="text-muted-foreground">No webhook endpoints yet.</p>
          ) : hooks ? (
            <ul className="grid gap-3" aria-label="Webhook endpoints">
              {hooks.map((hook) => {
                const active = hook.status === "active";
                const isBusy = busy === hook.id;
                return (
                  <li key={hook.id} className="rounded-lg border border-border bg-card p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="break-all font-medium">{hook.url}</p>
                        {hook.description && (
                          <p className="text-sm text-muted-foreground">{hook.description}</p>
                        )}
                        <p className="mt-1 text-sm text-muted-foreground">
                          {hook.events.length} event{hook.events.length === 1 ? "" : "s"} ·{" "}
                          {hook.failure_count} recent failure{hook.failure_count === 1 ? "" : "s"} ·
                          Last delivery {when(hook.last_delivery_at)}
                          {hook.last_status ? ` · ${hook.last_status}` : ""}
                        </p>
                      </div>
                      <StatusPill tone={active ? "ok" : "warn"}>{hook.status}</StatusPill>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isBusy || hook.status === "disabled"}
                        onClick={() =>
                          run(
                            hook.id,
                            () => updateWebhook(hook.id, { status: active ? "paused" : "active" }),
                            "Couldn't change this endpoint.",
                          )
                        }
                      >
                        {active ? "Pause" : "Resume"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isBusy}
                        onClick={() => test(hook)}
                      >
                        Send test
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={isBusy}
                        onClick={() => rotate(hook)}
                      >
                        Rotate secret
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => toggleDeliveries(hook)}>
                        {openDeliveries === hook.id ? "Hide deliveries" : "Recent deliveries"}
                      </Button>
                      {confirmId === hook.id ? (
                        <>
                          <Button
                            variant="destructive"
                            size="sm"
                            disabled={isBusy}
                            onClick={() =>
                              run(
                                hook.id,
                                () => deleteWebhook(hook.id),
                                "Couldn't delete this endpoint.",
                              ).then(() => setConfirmId(null))
                            }
                          >
                            Confirm delete
                          </Button>
                          <Button variant="outline" size="sm" onClick={() => setConfirmId(null)}>
                            Cancel
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={isBusy}
                          onClick={() => setConfirmId(hook.id)}
                        >
                          Delete
                        </Button>
                      )}
                    </div>
                    {testResult?.id === hook.id && (
                      <p className="mt-3 text-sm" role="status">
                        Test delivery {testResult.delivery.success ? "succeeded" : "failed"}
                        {testResult.delivery.status_code
                          ? ` with HTTP ${testResult.delivery.status_code}`
                          : ""}
                        {testResult.delivery.error ? `: ${testResult.delivery.error}` : "."}
                      </p>
                    )}
                    {openDeliveries === hook.id && (
                      <div className="mt-3 text-sm">
                        {deliveries === null ? (
                          <Loading label="Loading deliveries…" />
                        ) : deliveries.length === 0 ? (
                          <p className="text-muted-foreground">No deliveries yet.</p>
                        ) : (
                          <ul className="grid gap-1">
                            {deliveries.map((d) => (
                              <li key={d.id}>
                                <code className="text-sm">{d.event}</code> ·{" "}
                                {d.success ? "delivered" : "failed"}
                                {d.status_code ? ` (HTTP ${d.status_code})` : ""} · {d.attempts}{" "}
                                attempt{d.attempts === 1 ? "" : "s"} · {when(d.created_at)}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
      </WorkspaceGate>
    </StudioFrame>
  );
}
