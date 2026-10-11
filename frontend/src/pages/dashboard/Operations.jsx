import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  Activity as ActivityIcon,
  ScanLine,
  Siren,
  ScrollText,
  ToggleLeft,
  ListChecks,
  Rocket,
  Loader2,
  RefreshCw,
  Plus,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Server,
  Database,
  Cpu,
  Lock,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { usePermissions } from "@/hooks/usePermissions";

function fmtRelative(value) {
  if (!value) return "—";
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

const SEVERITY_STYLES = {
  critical: "bg-[#FEE2E2] text-[#B91C1C]",
  high: "bg-[#FFEDD5] text-[#C2410C]",
  medium: "bg-[#FEF3C7] text-[#B45309]",
  low: "bg-[#EEF2FF] text-[#4F46E5]",
  info: "bg-[#F1F5F9] text-[#475569]",
};

function SeverityBadge({ severity }) {
  const cls = SEVERITY_STYLES[severity] || SEVERITY_STYLES.info;
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold capitalize ${cls}`}>
      {severity}
    </span>
  );
}

const HEALTH_ICONS = { database: Database, ai_provider: Cpu, object_storage: Server, auth: Lock };

function statusDot(status) {
  if (status === "healthy" || status === "configured") return "bg-[#16A34A]";
  if (status === "degraded") return "bg-[#F59E0B]";
  return "bg-[#DC2626]";
}

/* ─────────────────────── System Health ─────────────────────── */
function HealthTab() {
  const [health, setHealth] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [h, m] = await Promise.all([api.get("/system/health"), api.get("/system/metrics")]);
      setHealth(h.data);
      setMetrics(m.data);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <TabSpinner />;

  const api_ = metrics?.api || {};

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${statusDot(health?.status)}`} />
          <span className="text-sm font-bold capitalize text-[#0F172A]">{health?.status || "unknown"}</span>
          <span className="text-[12px] text-[#94A3B8]">
            v{health?.version} · up {Math.floor((health?.uptime_seconds || 0) / 60)}m
          </span>
        </div>
        <button onClick={load} className="inline-flex items-center gap-1.5 text-[12px] font-semibold text-[#4F46E5] hover:underline">
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {(health?.checks || []).map((c) => {
          const Icon = HEALTH_ICONS[c.component] || Server;
          return (
            <div key={c.component} className="rounded-2xl border border-[#E2E8F0] bg-white p-4">
              <div className="flex items-center justify-between">
                <Icon className="h-4.5 w-4.5 text-[#4F46E5]" />
                <span className={`h-2 w-2 rounded-full ${statusDot(c.status)}`} />
              </div>
              <p className="mt-3 text-sm font-semibold capitalize text-[#0F172A]">{c.component.replace(/_/g, " ")}</p>
              <p className="text-[12px] capitalize text-[#64748B]">
                {c.status}
                {c.latency_ms != null ? ` · ${c.latency_ms}ms` : ""}
              </p>
            </div>
          );
        })}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Requests (24h)" value={api_.requests ?? 0} />
        <MetricCard label="Error rate" value={`${api_.error_rate ?? 0}%`} tone={api_.error_rate > 5 ? "warn" : "ok"} />
        <MetricCard label="Avg latency" value={`${Math.round(api_.avg_latency_ms ?? 0)}ms`} />
        <MetricCard label="Security events" value={metrics?.security_events ?? 0} />
      </div>
    </div>
  );
}

function MetricCard({ label, value, tone }) {
  const valCls = tone === "warn" ? "text-[#C2410C]" : "text-[#0F172A]";
  return (
    <div className="rounded-2xl border border-[#E2E8F0] bg-white p-4">
      <p className="text-[12px] font-medium text-[#64748B]">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums ${valCls}`}>{value}</p>
    </div>
  );
}

/* ─────────────────────── Security Scanner ─────────────────────── */
function ScannerTab() {
  const [text, setText] = useState("");
  const [direction, setDirection] = useState("input");
  const [result, setResult] = useState(null);
  const [scanning, setScanning] = useState(false);

  const scan = async () => {
    if (!text.trim()) {
      toast.error("Enter some text to scan.");
      return;
    }
    setScanning(true);
    try {
      const { data } = await api.post("/security/scan", { text, direction });
      setResult(data);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="space-y-3">
        <div className="inline-flex rounded-xl border border-[#E2E8F0] bg-white p-1">
          {["input", "output"].map((d) => (
            <button
              key={d}
              onClick={() => setDirection(d)}
              className={`rounded-lg px-4 py-1.5 text-[13px] font-semibold capitalize transition ${
                direction === d ? "bg-[#4F46E5] text-white" : "text-[#475569] hover:bg-[#F8FAFC]"
              }`}
            >
              {d === "input" ? "Prompt (input)" : "Response (output)"}
            </button>
          ))}
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={8}
          placeholder={
            direction === "input"
              ? "Paste a user prompt to scan for PII, injection and unsafe content…"
              : "Paste model output to scan for leaked secrets and internal URLs…"
          }
          className="w-full resize-none rounded-2xl border border-[#E2E8F0] p-4 text-sm outline-none focus:border-[#4F46E5]"
        />
        <button
          onClick={scan}
          disabled={scanning}
          className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60"
        >
          {scanning ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanLine className="h-4 w-4" />}
          Scan
        </button>
      </div>

      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5">
        {!result ? (
          <div className="grid h-full place-items-center text-center">
            <div>
              <ScanLine className="mx-auto h-8 w-8 text-[#CBD5E1]" />
              <p className="mt-2 text-sm text-[#94A3B8]">Run a scan to see results.</p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {result.safe ? (
                  <CheckCircle2 className="h-5 w-5 text-[#16A34A]" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-[#C2410C]" />
                )}
                <span className="text-sm font-bold text-[#0F172A]">{result.safe ? "Safe" : "Issues detected"}</span>
              </div>
              <SeverityBadge severity={result.severity} />
            </div>

            <ScanRow
              label="PII"
              flagged={result.pii?.detected}
              detail={result.pii?.types?.length ? result.pii.types.join(", ") : "None found"}
            />
            <ScanRow
              label="Prompt injection"
              flagged={result.prompt_injection?.injection}
              detail={result.prompt_injection?.flags?.length ? result.prompt_injection.flags.join(", ") : "None found"}
            />
            <ScanRow
              label="Content moderation"
              flagged={result.moderation?.flagged}
              detail={result.moderation?.categories?.length ? result.moderation.categories.join(", ") : "None found"}
            />
            {result.output_validation && (
              <ScanRow
                label="Output secrets"
                flagged={result.output_validation?.safe === false}
                detail={
                  result.output_validation?.violations?.length
                    ? result.output_validation.violations.join(", ")
                    : "None found"
                }
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ScanRow({ label, flagged, detail }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-[#E2E8F0] px-3 py-2.5">
      <div className="flex items-center gap-2">
        {flagged ? (
          <XCircle className="h-4 w-4 text-[#DC2626]" />
        ) : (
          <CheckCircle2 className="h-4 w-4 text-[#16A34A]" />
        )}
        <span className="text-[13px] font-semibold text-[#0F172A]">{label}</span>
      </div>
      <span className={`text-right text-[12px] ${flagged ? "text-[#C2410C]" : "text-[#94A3B8]"}`}>{detail}</span>
    </div>
  );
}

/* ─────────────────────── Security Events ─────────────────────── */
function EventsTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let on = true;
    api
      .get("/security/events", { params: { limit: 100 } })
      .then(({ data }) => on && setData(data))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => on && setLoading(false));
    return () => {
      on = false;
    };
  }, []);

  if (loading) return <TabSpinner />;
  const events = data?.events || [];
  const bySeverity = data?.by_severity || {};

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {Object.keys(bySeverity).length === 0 ? (
          <span className="text-[12px] text-[#94A3B8]">No security events recorded.</span>
        ) : (
          Object.entries(bySeverity).map(([sev, n]) => (
            <span key={sev} className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1 text-[12px] font-semibold ${SEVERITY_STYLES[sev] || SEVERITY_STYLES.info}`}>
              {sev}: {n}
            </span>
          ))
        )}
      </div>
      {events.length === 0 ? (
        <p className="py-12 text-center text-sm text-[#94A3B8]">No events to show.</p>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E2E8F0] text-left text-[11px] uppercase tracking-wide text-[#94A3B8]">
                <th className="px-4 py-2.5 font-semibold">Severity</th>
                <th className="px-4 py-2.5 font-semibold">Event</th>
                <th className="px-4 py-2.5 font-semibold">Title</th>
                <th className="px-4 py-2.5 font-semibold">When</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} className="border-b border-[#F1F5F9] last:border-0">
                  <td className="px-4 py-2.5"><SeverityBadge severity={e.severity} /></td>
                  <td className="px-4 py-2.5 font-mono text-[12px] text-[#475569]">{e.event_type}</td>
                  <td className="px-4 py-2.5 text-[#0F172A]">{e.title}</td>
                  <td className="px-4 py-2.5 text-[12px] text-[#64748B]">{fmtRelative(e.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────── Audit Log ─────────────────────── */
function AuditTab() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let on = true;
    api
      .get("/security/audit", { params: { limit: 100 } })
      .then(({ data }) => on && setEntries(Array.isArray(data?.entries) ? data.entries : []))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => on && setLoading(false));
    return () => {
      on = false;
    };
  }, []);

  if (loading) return <TabSpinner />;
  if (!entries.length) return <p className="py-12 text-center text-sm text-[#94A3B8]">No audit entries.</p>;

  return (
    <div className="overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#E2E8F0] text-left text-[11px] uppercase tracking-wide text-[#94A3B8]">
            <th className="px-4 py-2.5 font-semibold">Action</th>
            <th className="px-4 py-2.5 font-semibold">Resource</th>
            <th className="px-4 py-2.5 font-semibold">When</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((a) => (
            <tr key={a.id} className="border-b border-[#F1F5F9] last:border-0">
              <td className="px-4 py-2.5">
                <span className="rounded-md bg-[#EEF2FF] px-2 py-0.5 font-mono text-[11px] font-semibold text-[#4F46E5]">
                  {a.action}
                </span>
              </td>
              <td className="px-4 py-2.5 text-[#0F172A]">
                {a.resource}
                {a.resource_id ? <span className="text-[#94A3B8]"> · {a.resource_id.slice(0, 8)}</span> : ""}
              </td>
              <td className="px-4 py-2.5 text-[12px] text-[#64748B]">{fmtRelative(a.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─────────────────────── Feature Flags ─────────────────────── */
function FlagsTab({ canManage }) {
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/system/features");
      setFlags(Array.isArray(data?.features) ? data.features : []);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (flag) => {
    setBusyId(flag.id);
    try {
      await api.put(`/system/features/${flag.id}`, { enabled: !flag.enabled });
      setFlags((prev) => prev.map((f) => (f.id === flag.id ? { ...f, enabled: !f.enabled } : f)));
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <TabSpinner />;

  return (
    <div className="space-y-4">
      {canManage && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]"
          >
            <Plus className="h-4 w-4" /> New flag
          </button>
        </div>
      )}
      {flags.length === 0 ? (
        <p className="py-12 text-center text-sm text-[#94A3B8]">No feature flags yet.</p>
      ) : (
        <div className="space-y-2">
          {flags.map((f) => (
            <div key={f.id} className="flex items-center gap-4 rounded-2xl border border-[#E2E8F0] bg-white p-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-mono text-sm font-semibold text-[#0F172A]">{f.name}</p>
                  <span className="rounded bg-[#F1F5F9] px-1.5 py-0.5 text-[10px] font-semibold uppercase text-[#64748B]">
                    {f.environment}
                  </span>
                  <span className="rounded bg-[#F1F5F9] px-1.5 py-0.5 text-[10px] font-semibold uppercase text-[#64748B]">
                    {f.scope}
                  </span>
                </div>
                {f.description && <p className="mt-0.5 text-[12px] text-[#64748B]">{f.description}</p>}
                <p className="mt-0.5 text-[11px] text-[#94A3B8]">Rollout {f.rollout_percentage}%</p>
              </div>
              <button
                onClick={() => canManage && toggle(f)}
                disabled={!canManage || busyId === f.id}
                className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition ${
                  f.enabled ? "bg-[#4F46E5]" : "bg-[#CBD5E1]"
                } ${canManage ? "" : "cursor-not-allowed opacity-70"}`}
                aria-label="Toggle flag"
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                    f.enabled ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      )}
      {showCreate && (
        <CreateFlagModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function CreateFlagModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [rollout, setRollout] = useState(100);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!/^[a-z0-9_]+$/i.test(name.trim())) {
      toast.error("Use a key like beta_feature (letters, numbers, underscores).");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/system/features", {
        name: name.trim(),
        description: description.trim() || null,
        enabled,
        environment: "production",
        rollout_percentage: Number(rollout),
      });
      toast.success("Feature flag saved");
      onCreated();
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
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-bold text-[#0F172A]">New feature flag</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-[#94A3B8] hover:bg-[#F1F5F9]">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-5 space-y-4">
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Key</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="beta_collab"
              className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 font-mono text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Description</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this flag control?"
              className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-[#334155]">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              Enabled
            </label>
            <div className="flex items-center gap-2">
              <label className="text-[12px] font-semibold text-[#334155]">Rollout %</label>
              <input
                type="number"
                min={0}
                max={100}
                value={rollout}
                onChange={(e) => setRollout(e.target.value)}
                className="w-20 rounded-xl border border-[#E2E8F0] px-2 py-1.5 text-sm outline-none focus:border-[#4F46E5]"
              />
            </div>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl px-4 py-2 text-sm font-semibold text-[#475569] hover:bg-[#F1F5F9]">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Save flag
          </button>
        </div>
      </motion.div>
    </div>
  );
}

/* ─────────────────────── Readiness ─────────────────────── */
function ReadinessTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let on = true;
    api
      .get("/system/readiness")
      .then(({ data }) => on && setData(data))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => on && setLoading(false));
    return () => {
      on = false;
    };
  }, []);

  if (loading) return <TabSpinner />;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-4 rounded-2xl border border-[#E2E8F0] bg-white p-5">
        <div className="grid h-16 w-16 place-items-center rounded-2xl bg-[#F0FDF4]">
          <span className="text-xl font-bold text-[#16A34A]">{data?.score ?? 0}%</span>
        </div>
        <div>
          <p className="text-sm font-bold text-[#0F172A]">Release readiness</p>
          <p className="text-[13px] text-[#64748B]">
            {data?.passed}/{data?.total} checks passing · v{data?.version}
          </p>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {(data?.items || []).map((it) => (
          <div key={it.area} className="flex items-start gap-3 rounded-2xl border border-[#E2E8F0] bg-white p-4">
            {it.status === "pass" ? (
              <CheckCircle2 className="mt-0.5 h-4.5 w-4.5 shrink-0 text-[#16A34A]" />
            ) : (
              <AlertTriangle className="mt-0.5 h-4.5 w-4.5 shrink-0 text-[#C2410C]" />
            )}
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[#0F172A]">{it.area}</p>
              <p className="text-[12px] text-[#64748B]">{it.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────── Deployments ─────────────────────── */
function DeploymentsTab({ canManage }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/system/deployments");
      setItems(Array.isArray(data?.deployments) ? data.deployments : []);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <TabSpinner />;

  const statusStyle = {
    succeeded: "bg-[#DCFCE7] text-[#16A34A]",
    failed: "bg-[#FEE2E2] text-[#DC2626]",
    rolled_back: "bg-[#FEF3C7] text-[#B45309]",
    in_progress: "bg-[#EEF2FF] text-[#4F46E5]",
    pending: "bg-[#F1F5F9] text-[#475569]",
  };

  return (
    <div className="space-y-4">
      {canManage && (
        <div className="flex justify-end">
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]"
          >
            <Plus className="h-4 w-4" /> Record deployment
          </button>
        </div>
      )}
      {items.length === 0 ? (
        <p className="py-12 text-center text-sm text-[#94A3B8]">No deployments recorded.</p>
      ) : (
        <div className="space-y-2">
          {items.map((d) => (
            <div key={d.id} className="flex items-center gap-4 rounded-2xl border border-[#E2E8F0] bg-white p-4">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#EEF2FF] text-[#4F46E5]">
                <Rocket className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="font-mono text-sm font-bold text-[#0F172A]">v{d.version}</p>
                  <span className="rounded bg-[#F1F5F9] px-1.5 py-0.5 text-[10px] font-semibold uppercase text-[#64748B]">
                    {d.environment}
                  </span>
                </div>
                {d.notes && <p className="mt-0.5 truncate text-[12px] text-[#64748B]">{d.notes}</p>}
              </div>
              <span className={`rounded-md px-2 py-0.5 text-[11px] font-semibold capitalize ${statusStyle[d.status] || statusStyle.pending}`}>
                {String(d.status).replace(/_/g, " ")}
              </span>
              <span className="shrink-0 text-[11px] text-[#94A3B8]">{fmtRelative(d.created_at)}</span>
            </div>
          ))}
        </div>
      )}
      {showCreate && (
        <RecordDeployModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function RecordDeployModal({ onClose, onCreated }) {
  const [version, setVersion] = useState("");
  const [status, setStatus] = useState("succeeded");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!version.trim()) {
      toast.error("Enter a version.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/system/deployments", {
        version: version.trim(),
        environment: "production",
        status,
        notes: notes.trim() || null,
      });
      toast.success("Deployment recorded");
      onCreated();
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
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-bold text-[#0F172A]">Record deployment</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-[#94A3B8] hover:bg-[#F1F5F9]">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-5 space-y-4">
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Version</label>
            <input
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="1.0.0"
              className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 font-mono text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            >
              <option value="succeeded">Succeeded</option>
              <option value="in_progress">In progress</option>
              <option value="failed">Failed</option>
              <option value="rolled_back">Rolled back</option>
              <option value="pending">Pending</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Release notes…"
              className="w-full resize-none rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl px-4 py-2 text-sm font-semibold text-[#475569] hover:bg-[#F1F5F9]">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Record
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function TabSpinner() {
  return (
    <div className="grid place-items-center py-16">
      <Loader2 className="h-5 w-5 animate-spin text-[#4F46E5]" />
    </div>
  );
}

const TABS = [
  { key: "health", label: "System Health", icon: ActivityIcon },
  { key: "scanner", label: "Security Scanner", icon: ScanLine },
  { key: "events", label: "Security Events", icon: Siren },
  { key: "audit", label: "Audit Log", icon: ScrollText },
  { key: "flags", label: "Feature Flags", icon: ToggleLeft },
  { key: "readiness", label: "Readiness", icon: ListChecks },
  { key: "deployments", label: "Deployments", icon: Rocket },
];

export default function Operations() {
  const { can, role, loading: permsLoading } = usePermissions();
  const isAdmin = ["owner", "admin"].includes((role || "").toLowerCase());
  const canManage = can("settings.manage");
  const [tab, setTab] = useState("health");

  const content = useMemo(() => {
    switch (tab) {
      case "scanner":
        return <ScannerTab />;
      case "events":
        return <EventsTab />;
      case "audit":
        return <AuditTab />;
      case "flags":
        return <FlagsTab canManage={canManage} />;
      case "readiness":
        return <ReadinessTab />;
      case "deployments":
        return <DeploymentsTab canManage={canManage} />;
      default:
        return <HealthTab />;
    }
  }, [tab, canManage]);

  // Internal operations dashboard — never exposed to non-admin customers, even
  // by direct URL. Wait for the role to resolve, then redirect if unauthorized.
  if (!permsLoading && role && !isAdmin) {
    return <Navigate to="/app/dashboard" replace />;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-6xl space-y-6 p-6"
    >
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#EEF2FF] text-[#4F46E5]">
          <ShieldCheck className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#0F172A]">Operations & Security</h1>
          <p className="text-sm text-[#64748B]">
            System health, security scanning, audit trail, feature flags and release readiness.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 rounded-2xl border border-[#E2E8F0] bg-white p-1.5">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-[13px] font-semibold transition ${
              tab === t.key ? "bg-[#4F46E5] text-white" : "text-[#475569] hover:bg-[#F8FAFC]"
            }`}
          >
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      <div>{content}</div>
    </motion.div>
  );
}
