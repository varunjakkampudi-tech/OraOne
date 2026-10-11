import React, { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Loader2,
  Server,
  Database,
  Bot,
  Globe,
  MessageSquare,
} from "lucide-react";
import { PageHeader, Card } from "@/components/dashboard/kit";
import { API_BASE } from "@/lib/api";

// ─────────────────────────────────────────────────────────────────────────────
// Product Status — a live, customer-facing health page. It probes the public
// health endpoints (no auth required) and shows an overall banner plus a
// per-component breakdown. Refreshes automatically every 30s.
// ─────────────────────────────────────────────────────────────────────────────

const STATUS = {
  operational: {
    label: "Operational",
    icon: CheckCircle2,
    dot: "#16A34A",
    text: "#15803D",
    bg: "#DCFCE7",
  },
  degraded: {
    label: "Degraded",
    icon: AlertTriangle,
    dot: "#D97706",
    text: "#B45309",
    bg: "#FEF3C7",
  },
  down: {
    label: "Outage",
    icon: XCircle,
    dot: "#DC2626",
    text: "#B91C1C",
    bg: "#FEE2E2",
  },
};

async function probe(path, ms = 8000) {
  const started = performance.now();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    const res = await fetch(`${API_BASE}${path}`, { signal: ctrl.signal });
    clearTimeout(timer);
    return { ok: res.ok, latency: Math.round(performance.now() - started) };
  } catch {
    clearTimeout(timer);
    return { ok: false, latency: null };
  }
}

const COMPONENTS = [
  { key: "api", label: "API", icon: Server, desc: "Core REST API", probe: "/health" },
  { key: "db", label: "Database", icon: Database, desc: "Postgres primary", probe: "/health/db" },
  { key: "agents", label: "AI Agents", icon: Bot, desc: "Agent runtime", derive: "api" },
  { key: "widgets", label: "Widgets & Chat", icon: MessageSquare, desc: "Embeddable widget runtime", derive: "api" },
  { key: "crawler", label: "Website Crawler", icon: Globe, desc: "Distributed crawl workers", derive: "api" },
];

export default function Status() {
  const [checks, setChecks] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState(null);

  const run = useCallback(async () => {
    setLoading(true);
    const [api, db] = await Promise.all([probe("/health"), probe("/health/db")]);
    setChecks({ api, db });
    setUpdatedAt(new Date());
    setLoading(false);
  }, []);

  useEffect(() => {
    run();
    const t = setInterval(run, 30000);
    return () => clearInterval(t);
  }, [run]);

  const statusFor = (c) => {
    if (!checks) return "operational";
    if (c.derive) return checks[c.derive]?.ok ? "operational" : "degraded";
    const r = checks[c.key];
    if (!r) return "operational";
    return r.ok ? "operational" : c.key === "db" ? "degraded" : "down";
  };

  const components = COMPONENTS.map((c) => ({ ...c, status: statusFor(c), result: checks?.[c.derive || c.key] }));
  const anyDown = components.some((c) => c.status === "down");
  const anyDegraded = components.some((c) => c.status === "degraded");
  const overall = anyDown ? "down" : anyDegraded ? "degraded" : "operational";
  const o = STATUS[overall];
  const OIcon = o.icon;

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Activity}
        eyebrow="Reliability"
        title="Product Status"
        subtitle="Live health of OraOne services."
        actions={
          <button
            type="button"
            onClick={run}
            disabled={loading}
            data-testid="status-refresh"
            className="inline-flex items-center gap-1.5 rounded-xl border border-[#E2E8F0] bg-white px-3.5 py-2 text-[13px] font-semibold text-[#334155] transition hover:border-[#BFD3F5] hover:bg-[#EFF6FF] disabled:opacity-60"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Refresh
          </button>
        }
      />

      {/* Overall banner */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <Card className="p-6" data-testid="status-overall">
          <div className="flex items-center gap-4">
            <span
              className="grid size-12 place-items-center rounded-2xl"
              style={{ background: o.bg, color: o.text }}
            >
              <OIcon size={26} />
            </span>
            <div className="min-w-0">
              <h2 className="text-[20px] font-extrabold tracking-tight text-[#0F172A]">
                {overall === "operational"
                  ? "All Systems Operational"
                  : overall === "degraded"
                  ? "Partial Degradation"
                  : "Active Outage"}
              </h2>
              <p className="mt-0.5 text-[13px] text-[#64748B]">
                {updatedAt
                  ? `Last checked ${updatedAt.toLocaleTimeString()}`
                  : "Checking services…"}
              </p>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Components */}
      <Card className="divide-y divide-[#F1F5F9] overflow-hidden">
        {components.map((c) => {
          const s = STATUS[c.status];
          const SIcon = s.icon;
          return (
            <div
              key={c.key}
              className="flex items-center justify-between gap-4 px-5 py-4"
              data-testid={`status-component-${c.key}`}
            >
              <div className="flex items-center gap-3">
                <span className="grid size-9 place-items-center rounded-xl bg-[#F8FAFC] text-[#475569] ring-1 ring-[#E2E8F0]">
                  <c.icon size={16} />
                </span>
                <div>
                  <p className="text-[14px] font-semibold text-[#0F172A]">{c.label}</p>
                  <p className="text-[12px] text-[#94A3B8]">{c.desc}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {c.result?.latency != null && c.status === "operational" && (
                  <span className="text-[11.5px] font-medium text-[#94A3B8]">{c.result.latency} ms</span>
                )}
                <span
                  className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-semibold"
                  style={{ background: s.bg, color: s.text }}
                >
                  <SIcon size={13} />
                  {s.label}
                </span>
              </div>
            </div>
          );
        })}
      </Card>

      <p className="px-1 text-center text-[12px] text-[#94A3B8]">
        Status refreshes automatically every 30 seconds.
      </p>
    </div>
  );
}
