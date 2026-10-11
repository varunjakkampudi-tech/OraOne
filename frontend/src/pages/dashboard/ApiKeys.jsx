import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  KeyRound,
  Loader2,
  RefreshCw,
  Plus,
  Copy,
  Check,
  Trash2,
  ShieldCheck,
  X,
  Terminal,
} from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { usePermissions } from "@/hooks/usePermissions";

function fmtDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return "—";
  }
}

function fmtRelative(value) {
  if (!value) return "Never used";
  const then = new Date(value).getTime();
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function ScopeChip({ children }) {
  return (
    <span className="rounded-md bg-[#EEF2FF] px-2 py-0.5 font-mono text-[11px] font-medium text-[#4F46E5]">
      {children}
    </span>
  );
}

function CreateKeyModal({ scopes, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [selected, setSelected] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const toggle = (scope) =>
    setSelected((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    );

  const submit = async () => {
    if (!name.trim()) {
      toast.error("Give your key a name.");
      return;
    }
    if (!selected.length) {
      toast.error("Select at least one scope.");
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post("/api-keys", {
        name: name.trim(),
        scopes: selected,
      });
      onCreated(data);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold text-[#0F172A]">Create API key</h2>
            <p className="text-sm text-[#64748B]">
              Scope the key to only what it needs.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-[#94A3B8] hover:bg-[#F1F5F9]"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-5 space-y-5">
          <div>
            <label className="text-sm font-medium text-[#334155]">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              data-testid="apikey-name"
              placeholder="e.g. Production server"
              className="mt-1 w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-[#334155]">Scopes</label>
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {scopes.map((s) => {
                const on = selected.includes(s.scope);
                return (
                  <button
                    key={s.scope}
                    type="button"
                    onClick={() => toggle(s.scope)}
                    data-testid={`scope-${s.scope}`}
                    className={`flex items-center justify-between rounded-xl border px-3 py-2 text-left text-sm transition ${
                      on
                        ? "border-[#4F46E5] bg-[#EEF2FF]"
                        : "border-[#E2E8F0] bg-white hover:bg-[#F8FAFC]"
                    }`}
                  >
                    <span>
                      <span className="block font-medium text-[#0F172A]">
                        {s.label}
                      </span>
                      <span className="block font-mono text-[11px] text-[#94A3B8]">
                        {s.scope}
                      </span>
                    </span>
                    {on && <Check className="h-4 w-4 text-[#4F46E5]" />}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-xl border border-[#E2E8F0] px-4 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting}
            data-testid="apikey-create-submit"
            className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Create key
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function RevealKeyModal({ payload, onClose }) {
  const [copied, setCopied] = useState(false);
  const fullKey = payload.key;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(fullKey);
      setCopied(true);
      toast.success("API key copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Couldn't copy — select and copy manually.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#DCFCE7] text-[#16A34A]">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[#0F172A]">
              Save your API key
            </h2>
            <p className="text-sm text-[#64748B]">
              This is the only time you'll see the full key.
            </p>
          </div>
        </div>

        <div className="mt-5">
          <div className="flex items-stretch gap-2">
            <code
              data-testid="apikey-reveal"
              className="flex-1 break-all rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-3 font-mono text-xs text-[#0F172A]"
            >
              {fullKey}
            </code>
            <button
              onClick={copy}
              className="shrink-0 rounded-xl bg-[#4F46E5] px-3 text-white hover:bg-[#4338CA]"
            >
              {copied ? (
                <Check className="h-4 w-4" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </button>
          </div>
          <div className="mt-4 rounded-xl border border-[#E2E8F0] bg-[#0F172A] p-4 text-xs text-[#CBD5E1]">
            <div className="mb-2 flex items-center gap-2 text-[#94A3B8]">
              <Terminal className="h-3.5 w-3.5" /> Example request
            </div>
            <pre className="overflow-x-auto whitespace-pre-wrap font-mono">
{`curl https://api.oraone.app/api/v1/ping \\
  -H "Authorization: Bearer ${fullKey}"`}
            </pre>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            data-testid="apikey-reveal-done"
            className="rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]"
          >
            Done
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export default function ApiKeys() {
  const { can } = usePermissions();
  const [keys, setKeys] = useState([]);
  const [scopes, setScopes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [revealed, setRevealed] = useState(null);

  const canManage = can("apikeys.manage");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/api-keys");
      setKeys(data.keys || []);
      setScopes(data.scopes || []);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onCreated = (payload) => {
    setShowCreate(false);
    setRevealed(payload);
    load();
  };

  const revoke = async (key) => {
    if (!window.confirm(`Revoke "${key.name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/api-keys/${key.id}`);
      toast.success("API key revoked");
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const hasKeys = useMemo(() => keys.length > 0, [keys]);

  if (loading) {
    return (
      <div className="grid h-[60vh] place-items-center">
        <Loader2 className="h-6 w-6 animate-spin text-[#4F46E5]" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-5xl space-y-8 p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#EEF2FF] text-[#4F46E5]">
            <KeyRound className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#0F172A]">API Keys</h1>
            <p className="text-sm text-[#64748B]">
              Programmatic access to your organization via the{" "}
              <span className="font-mono text-[#4F46E5]">/api/v1</span> REST API.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            data-testid="apikeys-refresh"
            className="inline-flex items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
          >
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
          {canManage && (
            <button
              onClick={() => setShowCreate(true)}
              data-testid="apikeys-create"
              className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-3 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]"
            >
              <Plus className="h-4 w-4" /> Create key
            </button>
          )}
        </div>
      </div>

      {!hasKeys ? (
        <div className="grid place-items-center rounded-2xl border border-dashed border-[#CBD5E1] bg-white py-16 text-center">
          <KeyRound className="mb-3 h-10 w-10 text-[#CBD5E1]" />
          <p className="text-sm font-semibold text-[#0F172A]">No API keys yet</p>
          <p className="mt-1 max-w-sm text-sm text-[#64748B]">
            Create a key to call the OraOne API from your own servers,
            scripts, or integrations.
          </p>
          {canManage && (
            <button
              onClick={() => setShowCreate(true)}
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]"
            >
              <Plus className="h-4 w-4" /> Create your first key
            </button>
          )}
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC] text-left text-xs uppercase tracking-wide text-[#94A3B8]">
                <th className="px-5 py-3 font-semibold">Name</th>
                <th className="px-5 py-3 font-semibold">Key</th>
                <th className="px-5 py-3 font-semibold">Scopes</th>
                <th className="px-5 py-3 font-semibold">Last used</th>
                <th className="px-5 py-3 font-semibold">Created</th>
                {canManage && <th className="px-5 py-3" />}
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr
                  key={k.id}
                  className="border-b border-[#F1F5F9] last:border-0"
                >
                  <td className="px-5 py-4 font-medium text-[#0F172A]">
                    {k.name}
                  </td>
                  <td className="px-5 py-4">
                    <code className="rounded-md bg-[#F1F5F9] px-2 py-1 font-mono text-xs text-[#475569]">
                      {k.prefix}…
                    </code>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex flex-wrap gap-1">
                      {(k.scopes || []).map((s) => (
                        <ScopeChip key={s}>{s}</ScopeChip>
                      ))}
                    </div>
                  </td>
                  <td className="px-5 py-4 text-[#64748B]">
                    {fmtRelative(k.last_used_at)}
                  </td>
                  <td className="px-5 py-4 text-[#64748B]">
                    {fmtDate(k.created_at)}
                  </td>
                  {canManage && (
                    <td className="px-5 py-4 text-right">
                      <button
                        onClick={() => revoke(k)}
                        data-testid={`apikey-revoke-${k.id}`}
                        className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-[#DC2626] hover:bg-[#FEF2F2]"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Revoke
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5">
        <h2 className="text-base font-semibold text-[#0F172A]">
          Using the API
        </h2>
        <p className="mt-1 text-sm text-[#64748B]">
          Authenticate every request with your key. Rate limits follow your{" "}
          <Link to="/app/billing" className="font-medium text-[#4F46E5]">
            plan
          </Link>
          .
        </p>
        <pre className="mt-3 overflow-x-auto rounded-xl bg-[#0F172A] p-4 font-mono text-xs text-[#CBD5E1]">
{`# List your agents
curl https://api.oraone.app/api/v1/agents \\
  -H "Authorization: Bearer sk_ora_xxx"`}
        </pre>
      </div>

      {showCreate && (
        <CreateKeyModal
          scopes={scopes}
          onClose={() => setShowCreate(false)}
          onCreated={onCreated}
        />
      )}
      {revealed && (
        <RevealKeyModal
          payload={revealed}
          onClose={() => setRevealed(null)}
        />
      )}
    </motion.div>
  );
}
