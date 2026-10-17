import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/client";
import { getMe, type Me } from "@/lib/api/auth";
import { updateProfileName } from "@/lib/api/account";
import {
  createApiKey,
  deleteApiKey,
  listApiKeys,
  type ApiKey,
  type ScopeOption,
} from "@/lib/api/api-keys";
import { getAnalyticsOverview, type AnalyticsOverview } from "@/lib/api/analytics";
import { StudioFrame } from "./studio";
import { Loading, Notice } from "./studio-ui";
import { when, useWorkspaceId } from "@/lib/studio-helpers";

// API keys, analytics and account screens under /studio. Each reads from or
// writes to the API; nothing is simulated.

export function ApiKeysPage() {
  const workspace = useWorkspaceId();
  const [keys, setKeys] = useState<ApiKey[] | null>(null);
  const [scopes, setScopes] = useState<ScopeOption[]>([]);
  const [name, setName] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [created, setCreated] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load(projectId: string) {
    const list = await listApiKeys(projectId);
    setKeys(list.keys);
    setScopes(list.scopes);
  }

  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    load(workspace.id).catch((err) => {
      if (!cancelled) setError(messageOf(err, "Couldn't load API keys."));
    });
    return () => {
      cancelled = true;
    };
  }, [workspace.id]);

  function togglePick(scope: string) {
    setPicked((p) => (p.includes(scope) ? p.filter((s) => s !== scope) : [...p, scope]));
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    if (!workspace.id) return;
    setError("");
    setCreated(null);
    if (name.trim().length < 2) return setError("Name the key with at least 2 characters.");
    if (picked.length === 0) return setError("Choose at least one permission.");
    setBusy(true);
    try {
      const result = await createApiKey(workspace.id, { name: name.trim(), scopes: picked });
      setCreated(result.key);
      setName("");
      setPicked([]);
      await load(workspace.id);
    } catch (err) {
      setError(messageOf(err, "Couldn't create the key."));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(key: ApiKey) {
    if (!workspace.id) return;
    if (!window.confirm(`Revoke "${key.name}"? Apps using it will stop working.`)) return;
    setError("");
    try {
      await deleteApiKey(key.id);
      await load(workspace.id);
    } catch (err) {
      setError(messageOf(err, "Couldn't revoke this key."));
    }
  }

  return (
    <StudioFrame>
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">API keys</h1>
      <p className="mt-2 text-muted-foreground">
        Keys let your own systems read and write this workspace. A key is shown once, when created.
      </p>
      {workspace.error && (
        <div className="mt-4">
          <Notice kind="error">{workspace.error}</Notice>
        </div>
      )}
      {error && (
        <div className="mt-4">
          <Notice kind="error">{error}</Notice>
        </div>
      )}
      {created && (
        <div className="mt-4">
          <Notice>
            Copy this key now. It won't be shown again: <code className="break-all">{created}</code>
          </Notice>
        </div>
      )}
      {workspace.loaded && !workspace.id && !workspace.error && (
        <p className="mt-6 text-muted-foreground">Create a workspace to issue API keys.</p>
      )}
      {workspace.id && (
        <div className="mt-8 grid gap-6 md:grid-cols-[1fr_1.2fr]">
          <form
            onSubmit={create}
            className="grid content-start gap-3 rounded-xl border border-border bg-card p-5"
          >
            <h2 className="text-xl font-semibold">Create a key</h2>
            <label htmlFor="key-name" className="text-sm">
              Name
            </label>
            <input
              id="key-name"
              className="rounded-md border border-input bg-background px-3 py-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Website integration"
            />
            <fieldset className="grid gap-2">
              <legend className="text-sm">Permissions</legend>
              {scopes.map((s) => (
                <label key={s.scope} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={picked.includes(s.scope)}
                    onChange={() => togglePick(s.scope)}
                  />
                  {s.label} <span className="text-muted-foreground">({s.scope})</span>
                </label>
              ))}
            </fieldset>
            <Button type="submit" disabled={busy}>
              Create key
            </Button>
          </form>
          <section className="rounded-xl border border-border bg-card p-5">
            <h2 className="text-xl font-semibold">Existing keys</h2>
            {keys === null && !error ? (
              <div className="mt-3">
                <Loading label="Loading keys…" />
              </div>
            ) : keys && keys.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">No keys yet.</p>
            ) : keys ? (
              <ul className="mt-3 grid gap-2">
                {keys.map((k) => (
                  <li
                    key={k.id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2"
                  >
                    <span>
                      <strong className="block">{k.name}</strong>
                      <span className="text-sm text-muted-foreground">
                        {k.prefix}… · {k.scopes.length} permission(s) · last used{" "}
                        {when(k.last_used_at)}
                      </span>
                    </span>
                    <Button variant="outline" size="sm" onClick={() => revoke(k)}>
                      Revoke
                    </Button>
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        </div>
      )}
    </StudioFrame>
  );
}

export function AnalyticsPage() {
  const workspace = useWorkspaceId();
  const [days, setDays] = useState(30);
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    setError("");
    getAnalyticsOverview(workspace.id, days)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load analytics."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, days]);

  const totals = data
    ? ([
        ["Conversations", data.totals.conversations],
        ["Messages", data.totals.messages],
        ["Agents", data.totals.agents],
        ["Documents", data.totals.documents],
        ["Qualified", data.totals.qualified_conversations],
        ["Conversion", `${data.totals.conversion_rate}%`],
      ] as const)
    : [];

  return (
    <StudioFrame>
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Analytics</h1>
      <p className="mt-2 text-muted-foreground">
        Activity for this workspace over the selected period.
      </p>
      {workspace.error && (
        <div className="mt-4">
          <Notice kind="error">{workspace.error}</Notice>
        </div>
      )}
      {error && (
        <div className="mt-4">
          <Notice kind="error">{error}</Notice>
        </div>
      )}
      {workspace.loaded && !workspace.id && !workspace.error && (
        <p className="mt-6 text-muted-foreground">Create a workspace to see analytics.</p>
      )}
      {workspace.id && (
        <div className="mt-6 flex items-center gap-2">
          <label htmlFor="range" className="text-sm">
            Period
          </label>
          <select
            id="range"
            className="rounded-md border border-input bg-background px-3 py-2"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      )}
      {workspace.id && !data && !error && (
        <div className="mt-6">
          <Loading label="Loading analytics…" />
        </div>
      )}
      {data && (
        <>
          <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3" aria-label="Totals">
            {totals.map(([label, value]) => (
              <div key={label} className="rounded-lg border border-border bg-card p-4">
                <dt className="text-sm text-muted-foreground">{label}</dt>
                <dd className="mt-1 text-2xl font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <section className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-xl font-semibold">Conversations by status</h2>
              <ul className="mt-3 grid gap-1 text-sm">
                {Object.entries(data.breakdowns.conversations_by_status).map(([k, v]) => (
                  <li key={k} className="flex justify-between">
                    <span>{k}</span>
                    <span>{v}</span>
                  </li>
                ))}
                {Object.keys(data.breakdowns.conversations_by_status).length === 0 && (
                  <li className="text-muted-foreground">No conversations in this period.</li>
                )}
              </ul>
            </section>
            <section className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-xl font-semibold">Top assistants</h2>
              <ul className="mt-3 grid gap-1 text-sm">
                {data.top_agents.map((a) => (
                  <li key={a.agent_id} className="flex justify-between">
                    <span>{a.name}</span>
                    <span>{a.conversations}</span>
                  </li>
                ))}
                {data.top_agents.length === 0 && (
                  <li className="text-muted-foreground">No assistant activity yet.</li>
                )}
              </ul>
            </section>
          </div>
        </>
      )}
    </StudioFrame>
  );
}

export function AccountPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [name, setName] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((m) => {
        if (!cancelled) {
          setMe(m);
          setName(m.name);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load your account."));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function save(e: FormEvent) {
    e.preventDefault();
    setStatus("");
    setError("");
    if (name.trim().length < 1) return setError("Enter your name.");
    setBusy(true);
    try {
      const updated = await updateProfileName(name.trim());
      setMe(updated);
      setName(updated.name);
      setStatus("Saved.");
    } catch (err) {
      setError(messageOf(err, "Couldn't save your name."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <StudioFrame>
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Your account</h1>
      {error && (
        <div className="mt-4">
          <Notice kind="error">{error}</Notice>
        </div>
      )}
      {!me && !error && (
        <div className="mt-6">
          <Loading label="Loading account…" />
        </div>
      )}
      {me && (
        <form
          onSubmit={save}
          className="mt-6 grid max-w-md gap-3 rounded-xl border border-border bg-card p-5"
        >
          <label htmlFor="acc-email" className="text-sm">
            Email
          </label>
          <input
            id="acc-email"
            className="rounded-md border border-input bg-muted px-3 py-2"
            value={me.email}
            readOnly
          />
          <label htmlFor="acc-name" className="text-sm">
            Full name
          </label>
          <input
            id="acc-name"
            className="rounded-md border border-input bg-background px-3 py-2"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Button type="submit" disabled={busy}>
            Save
          </Button>
          {status && (
            <p role="status" className="text-sm">
              {status}
            </p>
          )}
        </form>
      )}
    </StudioFrame>
  );
}
