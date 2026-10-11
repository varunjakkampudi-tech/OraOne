import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  MessageSquare,
  Users,
  TrendingUp,
  Bot,
  Zap,
  BookOpen,
  FileText,
  Loader2,
  RefreshCw,
  Phone,
  MessageCircle,
  LayoutDashboard,
  Gauge,
  DollarSign,
  ShieldCheck,
  Code2,
  Workflow,
  Plug,
  UserCog,
  Download,
  Layers,
  Globe,
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  AlertTriangle,
  Lightbulb,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { PageHeader, GhostButton } from "@/components/dashboard/kit";

const RANGES = [
  { label: "7d", days: 7 },
  { label: "14d", days: 14 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
];

const CHANNEL_META = {
  chat: { label: "Chat", color: "#22C55E", icon: MessageSquare },
  whatsapp: { label: "WhatsApp", color: "#F59E0B", icon: MessageCircle },
};

const STATUS_COLORS = {
  active: "#2563EB",
  completed: "#22C55E",
  qualified: "#7C3AED",
  failed: "#EF4444",
  lost: "#94A3B8",
  queued: "#F59E0B",
  running: "#2563EB",
  awaiting_approval: "#A855F7",
  cancelled: "#94A3B8",
  connected: "#22C55E",
  disconnected: "#94A3B8",
  draft: "#94A3B8",
  processed: "#22C55E",
  processing: "#F59E0B",
};

const PALETTE = ["#2563EB", "#22C55E", "#F59E0B", "#7C3AED", "#EC4899", "#06B6D4", "#EF4444", "#14B8A6"];
const AGENT_COLORS = PALETTE;

function shortDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const fmtNum = (v) => (v ?? 0).toLocaleString();
const fmtUSD = (v) => `$${Number(v ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtPct = (v) => `${Number(v ?? 0).toFixed(1).replace(/\.0$/, "")}%`;
const colorFor = (key, i) => STATUS_COLORS[key] || PALETTE[i % PALETTE.length];

function Sparkline({ data, color }) {
  const series = (data || []).map((p, i) => ({ x: i, y: p.count }));
  return (
    <div className="w-24 h-14 shrink-0">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={series} margin={{ top: 6, right: 4, bottom: 4, left: 4 }}>
          <Line type="monotone" dataKey="y" stroke={color} strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function KpiCard({ label, value, icon: Icon, tone, spark, hint }) {
  return (
    <div className="p-5 rounded-2xl bg-white border border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)]">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className="size-11 rounded-2xl grid place-items-center shrink-0" style={{ background: `${tone}1A` }}>
            <Icon size={18} style={{ color: tone }} />
          </div>
          <div className="min-w-0">
            <p className="text-[12px] text-[#64748B] leading-tight">{label}</p>
            <p className="mt-1.5 text-[28px] font-bold tracking-tight text-[#0F172A] leading-none">{value}</p>
            {hint && <p className="mt-1 text-[11px] text-[#94A3B8]">{hint}</p>}
          </div>
        </div>
        {spark && <Sparkline data={spark} color={tone} />}
      </div>
    </div>
  );
}

function Panel({ title, action, children, className = "" }) {
  return (
    <div className={`p-6 rounded-2xl bg-white border border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)] ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-[#0F172A]">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

function EmptyHint({ children = "No data yet." }) {
  return <div className="grid h-full place-items-center text-sm text-[#94A3B8]">{children}</div>;
}

function TrendArea({ data, xKey = "date", areas, height = 260 }) {
  const rows = (data || []).map((p) => {
    const r = { day: shortDate(p[xKey]) };
    areas.forEach((a) => (r[a.label] = p[a.key] ?? 0));
    return r;
  });
  const allZero = rows.every((r) => areas.every((a) => !r[a.label]));
  return (
    <div style={{ height }}>
      {!rows.length || allZero ? (
        <EmptyHint />
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ left: -12, right: 8, top: 8, bottom: 0 }}>
            <defs>
              {areas.map((a) => {
                const id = `grad-${a.label.replace(/\s/g, "")}`;
                return (
                  <linearGradient key={id} id={id} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={a.color} stopOpacity={0.18} />
                    <stop offset="100%" stopColor={a.color} stopOpacity={0} />
                  </linearGradient>
                );
              })}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
            <XAxis dataKey="day" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} minTickGap={20} />
            <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
            <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }} />
            {areas.map((a) => (
              <Area
                key={a.label}
                type="monotone"
                dataKey={a.label}
                stroke={a.color}
                strokeWidth={2.5}
                fill={`url(#grad-${a.label.replace(/\s/g, "")})`}
                dot={false}
                activeDot={{ r: 4 }}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      )}
      {areas.length > 1 && (
        <div className="flex items-center gap-4 text-[12px] text-[#475569] mt-2">
          {areas.map((a) => (
            <span key={a.label} className="inline-flex items-center gap-1.5">
              <span className="size-2 rounded-full" style={{ background: a.color }} /> {a.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function BarBreakdown({ obj, height = 240, barSize = 44 }) {
  const data = Object.entries(obj || {})
    .map(([k, v], i) => ({ name: k.replace(/_/g, " "), value: v, color: colorFor(k, i) }))
    .filter((d) => d.value > 0);
  return (
    <div style={{ height }} className="mt-3">
      {!data.length ? (
        <EmptyHint />
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: -12, right: 8, top: 16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
            <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
            <Tooltip cursor={{ fill: "rgba(15,23,42,0.04)" }} contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }} />
            <Bar dataKey="value" radius={[10, 10, 10, 10]} barSize={barSize}>
              {data.map((c) => (
                <Cell key={c.name} fill={c.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function Donut({ obj, centerLabel, centerValue }) {
  const data = Object.entries(obj || {})
    .filter(([, v]) => v > 0)
    .map(([k, v], i) => ({ name: k.replace(/_/g, " "), value: v, color: colorFor(k, i) }));
  const total = data.reduce((a, b) => a + b.value, 0);
  return (
    <div className="mt-3 grid grid-cols-[1fr_1fr] gap-4 items-center">
      {!data.length ? (
        <p className="text-sm text-[#64748B] col-span-2 text-center py-6">No data yet.</p>
      ) : (
        <>
          <div className="relative h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="value" innerRadius={50} outerRadius={76} paddingAngle={3} stroke="none">
                  {data.map((e, i) => (
                    <Cell key={i} fill={e.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 grid place-items-center pointer-events-none">
              <div className="text-center">
                <p className="text-2xl font-bold tracking-tight text-[#0F172A] leading-none">{centerValue ?? total}</p>
                <p className="text-[11px] text-[#64748B] mt-1">{centerLabel ?? "Total"}</p>
              </div>
            </div>
          </div>
          <div className="space-y-2.5">
            {data.map((s) => (
              <div key={s.name} className="flex items-center justify-between text-[12px]">
                <span className="flex items-center gap-2 text-[#475569] capitalize">
                  <span className="size-2 rounded-full shrink-0" style={{ background: s.color }} /> {s.name}
                </span>
                <span className="font-semibold text-[#0F172A]">{s.value}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function DataTable({ columns, rows, empty = "No data yet." }) {
  if (!rows || !rows.length) {
    return <p className="text-sm text-[#64748B] text-center py-6">{empty}</p>;
  }
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#E2E8F0] text-left text-[11px] uppercase tracking-wide text-[#94A3B8]">
            {columns.map((c) => (
              <th key={c.key} className={`py-2 pr-4 font-semibold ${c.align === "right" ? "text-right" : ""}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-[#F1F5F9] last:border-0">
              {columns.map((c) => (
                <td key={c.key} className={`py-2.5 pr-4 ${c.align === "right" ? "text-right tabular-nums" : ""} ${c.bold ? "font-semibold text-[#0F172A]" : "text-[#475569]"}`}>
                  {c.render ? c.render(row[c.key], row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FeedbackStrip({ feedback }) {
  const f = feedback || {};
  return (
    <div className="grid grid-cols-3 gap-3">
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-3">
        <div className="size-9 rounded-xl bg-[#DCFCE7] grid place-items-center text-[#16A34A]">
          <ThumbsUp size={16} />
        </div>
        <div>
          <p className="text-[18px] font-bold text-[#0F172A] leading-none">{fmtNum(f.positive)}</p>
          <p className="text-[11px] text-[#64748B] mt-1">Positive</p>
        </div>
      </div>
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-3">
        <div className="size-9 rounded-xl bg-[#FEE2E2] grid place-items-center text-[#DC2626]">
          <ThumbsDown size={16} />
        </div>
        <div>
          <p className="text-[18px] font-bold text-[#0F172A] leading-none">{fmtNum(f.negative)}</p>
          <p className="text-[11px] text-[#64748B] mt-1">Negative</p>
        </div>
      </div>
      <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 flex items-center gap-3">
        <div className="size-9 rounded-xl bg-[#EEF2FF] grid place-items-center text-[#4F46E5]">
          <TrendingUp size={16} />
        </div>
        <div>
          <p className="text-[18px] font-bold text-[#0F172A] leading-none">{fmtPct(f.satisfaction_rate)}</p>
          <p className="text-[11px] text-[#64748B] mt-1">Satisfaction</p>
        </div>
      </div>
    </div>
  );
}

function ModelCostTable({ rows }) {
  return (
    <DataTable
      columns={[
        { key: "model", label: "Model", bold: true, render: (v) => v || "unknown" },
        { key: "tokens", label: "Tokens", align: "right", render: fmtNum },
        { key: "cost", label: "Cost", align: "right", render: fmtUSD },
      ]}
      rows={rows}
      empty="No model usage yet."
    />
  );
}

function AgentCostTable({ rows }) {
  return (
    <DataTable
      columns={[
        { key: "agent", label: "Agent", bold: true, render: (v) => v || "Unnamed agent" },
        { key: "conversations", label: "Convos", align: "right", render: fmtNum },
        { key: "tokens", label: "Tokens", align: "right", render: fmtNum },
        { key: "cost", label: "Cost", align: "right", render: fmtUSD },
      ]}
      rows={rows}
      empty="No agent usage yet."
    />
  );
}

function ProjectCostTable({ rows }) {
  return (
    <DataTable
      columns={[
        { key: "project", label: "Project", bold: true, render: (v) => v || "Unassigned" },
        { key: "conversations", label: "Convos", align: "right", render: fmtNum },
        { key: "tokens", label: "Tokens", align: "right", render: fmtNum },
        { key: "cost", label: "Cost", align: "right", render: fmtUSD },
      ]}
      rows={rows}
      empty="No project usage yet."
    />
  );
}

function QuestionList({ rows, icon: Icon = HelpCircle, tone = "#2563EB", empty = "No questions yet." }) {
  if (!rows || !rows.length) {
    return <p className="text-sm text-[#64748B] text-center py-6">{empty}</p>;
  }
  const max = Math.max(...rows.map((r) => r.count || 0), 1);
  return (
    <ul className="mt-3 space-y-2">
      {rows.map((r, i) => (
        <li key={i} className="flex items-center gap-3">
          <span
            className="size-7 rounded-lg grid place-items-center shrink-0"
            style={{ background: `${tone}14`, color: tone }}
          >
            <Icon size={14} />
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[13px] text-[#0F172A] truncate" title={r.question}>
                {r.question}
              </p>
              <span className="text-[12px] font-semibold text-[#475569] tabular-nums shrink-0">
                {fmtNum(r.count)}
              </span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-[#F1F5F9] overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${Math.round(((r.count || 0) / max) * 100)}%`, background: tone }}
              />
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

function TabLoading() {
  return (
    <div className="grid h-[40vh] place-items-center">
      <Loader2 className="h-6 w-6 animate-spin text-[#2563EB]" />
    </div>
  );
}

// ── data hook for module tabs ──────────────────────────────────────────
function useModule(module, days, enabled) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(() => {
    if (!enabled) return;
    let on = true;
    setLoading(true);
    api
      .get(`/analytics/${module}`, { params: { days } })
      .then(({ data }) => on && setData(data))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => on && setLoading(false));
    return () => {
      on = false;
    };
  }, [module, days, enabled]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, reload };
}

// ── Overview tab (preserves the original organization-wide view) ───────
function OverviewTab({ days }) {
  const { data, loading } = useModule("overview", days, true);
  const totals = data?.totals;

  const timeline = useMemo(() => {
    if (!data?.series) return [];
    const conv = data.series.conversations || [];
    const msg = data.series.messages || [];
    const runs = data.series.workflow_runs || [];
    return conv.map((p, i) => ({
      day: shortDate(p.date),
      Conversations: p.count,
      Messages: msg[i]?.count ?? 0,
      "Workflow Runs": runs[i]?.count ?? 0,
    }));
  }, [data]);

  const channelData = useMemo(() => {
    const ch = data?.breakdowns?.conversations_by_channel || {};
    return Object.entries(ch).map(([k, v]) => ({
      channel: CHANNEL_META[k]?.label || k,
      count: v,
      color: CHANNEL_META[k]?.color || "#94A3B8",
    }));
  }, [data]);

  const statusData = useMemo(() => {
    const st = data?.breakdowns?.conversations_by_status || {};
    return Object.entries(st)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({ name: k, value: v, color: STATUS_COLORS[k] || "#94A3B8" }));
  }, [data]);

  const runStatusData = useMemo(() => {
    const rs = data?.breakdowns?.workflow_runs_by_status || {};
    return Object.entries(rs)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({ name: k.replace(/_/g, " "), value: v, color: STATUS_COLORS[k] || "#94A3B8" }));
  }, [data]);

  const topAgents = data?.top_agents || [];
  const maxAgentConvos = Math.max(1, ...topAgents.map((a) => a.conversations));

  if (loading && !data) return <TabLoading />;

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total Conversations" value={fmtNum(totals?.conversations)} icon={MessageSquare} tone="#2563EB" spark={data?.series?.conversations} />
        <KpiCard label="Total Messages" value={fmtNum(totals?.messages)} icon={Users} tone="#22C55E" spark={data?.series?.messages} />
        <KpiCard label="Workflow Runs" value={fmtNum(totals?.workflow_runs)} icon={Zap} tone="#F59E0B" spark={data?.series?.workflow_runs} />
        <KpiCard label="Conversion Rate" value={`${totals?.conversion_rate ?? 0}%`} icon={TrendingUp} tone="#7C3AED" />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Agents", value: totals?.agents, icon: Bot },
          { label: "Knowledge Bases", value: totals?.knowledge_bases, icon: BookOpen },
          { label: "Documents", value: totals?.documents, icon: FileText },
          { label: "Team Members", value: totals?.members, icon: Users },
        ].map((s) => (
          <div key={s.label} className="p-4 rounded-2xl bg-white border border-[#E2E8F0] flex items-center gap-3">
            <div className="size-9 rounded-xl bg-[#EEF2FF] grid place-items-center text-[#4F46E5]">
              <s.icon size={16} />
            </div>
            <div>
              <p className="text-[18px] font-bold text-[#0F172A] leading-none">{fmtNum(s.value)}</p>
              <p className="text-[11px] text-[#64748B] mt-1">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-5">
        <Panel title="Activity Over Time">
          <div className="h-72 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeline} margin={{ left: -12, right: 8, top: 8, bottom: 0 }}>
                <defs>
                  <linearGradient id="aConv" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563EB" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="aMsg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22C55E" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#22C55E" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="aRun" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="#F59E0B" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                <XAxis dataKey="day" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} minTickGap={20} />
                <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }} />
                <Area type="monotone" dataKey="Conversations" stroke="#2563EB" strokeWidth={2.5} fill="url(#aConv)" dot={false} activeDot={{ r: 4 }} />
                <Area type="monotone" dataKey="Messages" stroke="#22C55E" strokeWidth={2.5} fill="url(#aMsg)" dot={false} activeDot={{ r: 4 }} />
                <Area type="monotone" dataKey="Workflow Runs" stroke="#F59E0B" strokeWidth={2.5} fill="url(#aRun)" dot={false} activeDot={{ r: 4 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center gap-4 text-[12px] text-[#475569] mt-2">
            {[
              { label: "Conversations", color: "#2563EB" },
              { label: "Messages", color: "#22C55E" },
              { label: "Workflow Runs", color: "#F59E0B" },
            ].map((l) => (
              <span key={l.label} className="inline-flex items-center gap-1.5">
                <span className="size-2 rounded-full" style={{ background: l.color }} /> {l.label}
              </span>
            ))}
          </div>
        </Panel>

        <Panel title="Conversations by Channel">
          <div className="mt-3 h-72">
            {channelData.every((c) => c.count === 0) ? (
              <EmptyHint>No conversation data yet.</EmptyHint>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={channelData} margin={{ left: -12, right: 8, top: 16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="channel" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip cursor={{ fill: "rgba(15,23,42,0.04)" }} contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }} />
                  <Bar dataKey="count" radius={[10, 10, 10, 10]} barSize={48}>
                    {channelData.map((c) => (
                      <Cell key={c.channel} fill={c.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Panel title="Top Performing Agents">
          <div className="mt-5 space-y-5">
            {topAgents.length === 0 ? (
              <p className="text-sm text-[#64748B] text-center py-6">No agent data yet.</p>
            ) : (
              topAgents.map((a, i) => {
                const color = AGENT_COLORS[i % AGENT_COLORS.length];
                const pct = Math.round((a.conversations / maxAgentConvos) * 100);
                const initials = (a.name || "?").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
                return (
                  <div key={a.agent_id}>
                    <div className="flex items-center gap-3">
                      <div className="size-9 rounded-full grid place-items-center text-white text-[11.5px] font-semibold shrink-0" style={{ background: color }}>
                        {initials}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[13.5px] font-semibold text-[#0F172A] truncate">{a.name}</p>
                        <p className="text-[11px] text-[#64748B] mt-0.5">{a.conversations.toLocaleString()} conversations</p>
                      </div>
                    </div>
                    <div className="mt-2.5 h-1.5 rounded-full bg-[#F1F5F9] overflow-hidden">
                      <div className="h-full rounded-full transition-[width] duration-700" style={{ width: `${pct}%`, background: color }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Panel>

        <Panel title="Conversation Status">
          <Donut obj={data?.breakdowns?.conversations_by_status} centerValue={totals?.conversations ?? 0} />
        </Panel>

        <Panel title="Workflow Runs">
          <div className="mt-4 space-y-3">
            {runStatusData.length === 0 ? (
              <p className="text-sm text-[#64748B] text-center py-6">No workflow runs yet.</p>
            ) : (
              runStatusData.map((s) => {
                const total = runStatusData.reduce((acc, x) => acc + x.value, 0) || 1;
                const pct = Math.round((s.value / total) * 100);
                return (
                  <div key={s.name}>
                    <div className="flex items-center justify-between text-[12px] mb-1">
                      <span className="capitalize text-[#475569]">{s.name}</span>
                      <span className="font-semibold text-[#0F172A]">{s.value}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-[#F1F5F9] overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: s.color }} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}

// ── Executive tab ──────────────────────────────────────────────────────
function ExecutiveTab({ days }) {
  const { data, loading } = useModule("executive", days, true);
  const k = data?.kpis;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Conversations" value={fmtNum(k?.conversations)} icon={MessageSquare} tone="#2563EB" spark={data?.series?.conversations} />
        <KpiCard label="Automated Interactions" value={fmtNum(k?.automated_interactions)} icon={Zap} tone="#22C55E" />
        <KpiCard label="Conversion Rate" value={fmtPct(k?.conversion_rate)} icon={TrendingUp} tone="#7C3AED" />
        <KpiCard label="Satisfaction" value={fmtPct(k?.satisfaction_rate)} icon={ShieldCheck} tone="#06B6D4" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="AI Cost" value={fmtUSD(k?.ai_cost)} icon={DollarSign} tone="#2563EB" hint={`${days}-day window`} />
        <KpiCard label="Human-Equivalent Cost" value={fmtUSD(k?.human_equivalent_cost)} icon={Users} tone="#F59E0B" hint="If handled by staff" />
        <KpiCard label="Estimated Savings" value={fmtUSD(k?.estimated_savings)} icon={TrendingUp} tone="#22C55E" />
        <KpiCard label="ROI Multiple" value={`${fmtNum(k?.roi_multiple)}×`} icon={Gauge} tone="#EC4899" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-5">
        <Panel title="Conversations Trend">
          <div className="mt-4">
            <TrendArea data={data?.series?.conversations} areas={[{ key: "count", color: "#2563EB", label: "Conversations" }]} height={260} />
          </div>
        </Panel>
        <Panel title="Cost Over Time">
          <div className="mt-4">
            <TrendArea data={data?.series?.cost} areas={[{ key: "cost", color: "#22C55E", label: "Cost ($)" }]} height={260} />
          </div>
        </Panel>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel title="Conversations by Channel">
          <BarBreakdown obj={data?.breakdowns?.conversations_by_channel} />
        </Panel>
        <Panel title="Cost by Model">
          <ModelCostTable rows={data?.breakdowns?.cost_by_model} />
        </Panel>
      </div>
    </div>
  );
}

// ── Cost tab ───────────────────────────────────────────────────────────
function CostTab({ days }) {
  const { data, loading } = useModule("cost", days, true);
  const t = data?.totals;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total Tokens" value={fmtNum(t?.total_tokens)} icon={Layers} tone="#2563EB" />
        <KpiCard label="Total Cost" value={fmtUSD(t?.total_cost)} icon={DollarSign} tone="#22C55E" />
        <KpiCard label="Cost / Conversation" value={fmtUSD(t?.cost_per_conversation)} icon={MessageSquare} tone="#F59E0B" />
        <KpiCard label="Projected Monthly" value={fmtUSD(t?.projected_monthly_cost)} icon={TrendingUp} tone="#7C3AED" />
      </div>
      <Panel title="Spend Over Time">
        <div className="mt-4">
          <TrendArea
            data={data?.series?.cost}
            areas={[
              { key: "cost", color: "#22C55E", label: "Cost ($)" },
            ]}
            height={300}
          />
        </div>
      </Panel>
      <Panel title="Cost by Model">
        <ModelCostTable rows={data?.breakdowns?.by_model} />
      </Panel>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel title="Cost by Agent">
          <AgentCostTable rows={data?.breakdowns?.by_agent} />
        </Panel>
        <Panel title="Cost by Project">
          <ProjectCostTable rows={data?.breakdowns?.by_project} />
        </Panel>
      </div>
    </div>
  );
}

// ── Insights tab (top questions / unanswered / knowledge gaps) ─────────
function InsightsTab({ days }) {
  const { data, loading } = useModule("insights", days, true);
  const t = data?.totals;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="AI Answers" value={fmtNum(t?.answers)} icon={Bot} tone="#2563EB" hint={`${days}-day window`} />
        <KpiCard label="Grounded Rate" value={fmtPct(t?.grounded_rate)} icon={ShieldCheck} tone="#22C55E" hint="Backed by knowledge base" />
        <KpiCard label="Unanswered" value={fmtNum(t?.unanswered)} icon={AlertTriangle} tone="#F59E0B" hint={fmtPct(t?.unanswered_rate) + " of answers"} />
        <KpiCard label="Low Confidence" value={fmtNum(t?.low_confidence)} icon={HelpCircle} tone="#EF4444" hint="Confidence < 40%" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel title="Top Questions">
          <QuestionList rows={data?.top_questions} icon={HelpCircle} tone="#2563EB" empty="No questions in this window." />
        </Panel>
        <Panel title="Knowledge Gaps">
          <div className="flex items-start gap-2 mt-1 text-[12px] text-[#94A3B8]">
            <Lightbulb size={14} className="text-[#F59E0B] mt-0.5 shrink-0" />
            <span>Questions asked in conversations the AI could not confidently ground. Add these to your knowledge base.</span>
          </div>
          <QuestionList rows={data?.knowledge_gaps} icon={AlertTriangle} tone="#F59E0B" empty="No knowledge gaps detected. Nice." />
        </Panel>
      </div>
      <Panel title="Answer Feedback">
        <div className="mt-4">
          <FeedbackStrip feedback={data?.feedback} />
        </div>
      </Panel>
    </div>
  );
}

// ── Conversations tab ──────────────────────────────────────────────────
function ConversationsTab({ days }) {
  const { data, loading } = useModule("chat", days, true);
  const t = data?.totals;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard label="Conversations" value={fmtNum(t?.conversations)} icon={MessageSquare} tone="#2563EB" spark={data?.series?.conversations} />
        <KpiCard label="Messages" value={fmtNum(t?.messages)} icon={Users} tone="#22C55E" spark={data?.series?.messages} />
        <KpiCard label="Avg Messages / Conversation" value={fmtNum(t?.avg_messages_per_conversation)} icon={TrendingUp} tone="#F59E0B" />
      </div>
      <Panel title="Conversations & Messages">
        <div className="mt-4">
          <TrendArea
            data={(data?.series?.conversations || []).map((p, i) => ({
              date: p.date,
              count: p.count,
              messages: data?.series?.messages?.[i]?.count ?? 0,
            }))}
            areas={[
              { key: "count", color: "#2563EB", label: "Conversations" },
              { key: "messages", color: "#22C55E", label: "Messages" },
            ]}
            height={300}
          />
        </div>
      </Panel>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel title="By Channel">
          <BarBreakdown obj={data?.breakdowns?.by_channel} />
        </Panel>
        <Panel title="By Status">
          <Donut obj={data?.breakdowns?.by_status} />
        </Panel>
      </div>
      <Panel title="Answer Feedback">
        <div className="mt-4">
          <FeedbackStrip feedback={data?.feedback} />
        </div>
      </Panel>
    </div>
  );
}

// ── Agents tab ─────────────────────────────────────────────────────────
function AgentsTab({ days }) {
  const { data, loading } = useModule("agents", days, true);
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <KpiCard label="Total Agents" value={fmtNum(data?.totals?.agents)} icon={Bot} tone="#2563EB" />
        <div className="p-5 rounded-2xl bg-white border border-[#E2E8F0]">
          <p className="text-[12px] text-[#64748B] mb-2">By Status</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(data?.breakdowns?.by_status || {}).map(([k, v], i) => (
              <span key={k} className="inline-flex items-center gap-1.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0] px-2.5 py-1 text-[12px] text-[#475569]">
                <span className="size-2 rounded-full" style={{ background: colorFor(k, i) }} /> {k} · <b className="text-[#0F172A]">{v}</b>
              </span>
            ))}
          </div>
        </div>
      </div>
      <Panel title="Agent Performance">
        <DataTable
          columns={[
            { key: "name", label: "Agent", bold: true },
            { key: "status", label: "Status", render: (v) => <span className="capitalize">{v}</span> },
            { key: "conversations", label: "Conversations", align: "right", render: fmtNum },
            { key: "qualified", label: "Qualified", align: "right", render: fmtNum },
            { key: "conversion_rate", label: "Conversion", align: "right", render: (v) => fmtPct(v) },
          ]}
          rows={data?.agents}
          empty="No agents yet."
        />
      </Panel>
    </div>
  );
}

// ── Knowledge tab ──────────────────────────────────────────────────────
function KnowledgeTab({ days }) {
  const { data, loading } = useModule("knowledge", days, true);
  const t = data?.totals;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <KpiCard label="Knowledge Bases" value={fmtNum(t?.knowledge_bases)} icon={BookOpen} tone="#2563EB" />
        <KpiCard label="Documents" value={fmtNum(t?.documents)} icon={FileText} tone="#22C55E" />
        <KpiCard label="Chunks" value={fmtNum(t?.chunks)} icon={Layers} tone="#F59E0B" />
        <KpiCard label="Websites" value={fmtNum(t?.websites)} icon={Globe} tone="#7C3AED" />
        <KpiCard label="Crawled Pages" value={fmtNum(t?.crawled_pages)} icon={Globe} tone="#06B6D4" />
      </div>
      <Panel title="Documents by Status">
        <BarBreakdown obj={data?.breakdowns?.documents_by_status} />
      </Panel>
    </div>
  );
}

// ── RAG tab ────────────────────────────────────────────────────────────
function RagTab({ days }) {
  const { data, loading } = useModule("rag", days, true);
  const t = data?.totals;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Answers" value={fmtNum(t?.answers)} icon={MessageSquare} tone="#2563EB" />
        <KpiCard label="Grounded Answers" value={fmtNum(t?.grounded_answers)} icon={ShieldCheck} tone="#22C55E" />
        <KpiCard label="Ungrounded" value={fmtNum(t?.ungrounded_answers)} icon={FileText} tone="#F59E0B" />
        <KpiCard label="Grounded Rate" value={fmtPct(t?.grounded_rate)} icon={TrendingUp} tone="#7C3AED" />
      </div>
      <Panel title="Answer Feedback">
        <div className="mt-4">
          <FeedbackStrip feedback={data?.feedback} />
        </div>
      </Panel>
    </div>
  );
}

// ── Widget tab ─────────────────────────────────────────────────────────
function WidgetTab({ days }) {
  const { data, loading } = useModule("widget", days, true);
  const t = data?.totals;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <KpiCard label="Widgets" value={fmtNum(t?.widgets)} icon={Code2} tone="#2563EB" />
        <KpiCard label="Sessions" value={fmtNum(t?.sessions)} icon={Users} tone="#22C55E" spark={data?.series?.sessions} />
        <KpiCard label="Messages" value={fmtNum(t?.messages)} icon={MessageSquare} tone="#F59E0B" />
        <KpiCard label="Escalations" value={fmtNum(t?.escalations)} icon={Phone} tone="#EF4444" />
        <KpiCard label="Leads" value={fmtNum(t?.leads)} icon={TrendingUp} tone="#7C3AED" />
        <KpiCard label="Escalation Rate" value={fmtPct(t?.escalation_rate)} icon={Gauge} tone="#06B6D4" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel title="Sessions Over Time">
          <div className="mt-4">
            <TrendArea data={data?.series?.sessions} areas={[{ key: "count", color: "#2563EB", label: "Sessions" }]} height={260} />
          </div>
        </Panel>
        <Panel title="Events">
          <BarBreakdown obj={data?.breakdowns?.by_event} />
        </Panel>
      </div>
    </div>
  );
}

// ── Workflows tab ──────────────────────────────────────────────────────
function WorkflowsTab({ days }) {
  const { data, loading } = useModule("workflows", days, true);
  const t = data?.totals;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Workflows" value={fmtNum(t?.workflows)} icon={Workflow} tone="#2563EB" />
        <KpiCard label="Runs" value={fmtNum(t?.runs)} icon={Zap} tone="#22C55E" spark={data?.series?.runs} />
        <KpiCard label="Succeeded" value={fmtNum(t?.succeeded)} icon={ShieldCheck} tone="#7C3AED" />
        <KpiCard label="Success Rate" value={fmtPct(t?.success_rate)} icon={TrendingUp} tone="#F59E0B" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-5">
        <Panel title="Runs Over Time">
          <div className="mt-4">
            <TrendArea data={data?.series?.runs} areas={[{ key: "count", color: "#2563EB", label: "Runs" }]} height={260} />
          </div>
        </Panel>
        <Panel title="Runs by Status">
          <Donut obj={data?.breakdowns?.runs_by_status} centerLabel="Runs" />
        </Panel>
      </div>
      <Panel title="Top Workflows">
        <DataTable
          columns={[
            { key: "name", label: "Workflow", bold: true },
            { key: "runs", label: "Runs", align: "right", render: fmtNum },
            { key: "successes", label: "Successes", align: "right", render: fmtNum },
          ]}
          rows={data?.top_workflows}
          empty="No workflow runs yet."
        />
      </Panel>
    </div>
  );
}

// ── Integrations tab ───────────────────────────────────────────────────
function IntegrationsTab({ days }) {
  const { data, loading } = useModule("integrations", days, true);
  const t = data?.totals;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard label="Integrations" value={fmtNum(t?.integrations)} icon={Plug} tone="#2563EB" />
        <KpiCard label="Sync Jobs" value={fmtNum(t?.sync_jobs)} icon={RefreshCw} tone="#22C55E" />
        <KpiCard label="Documents Synced" value={fmtNum(t?.documents_synced)} icon={FileText} tone="#F59E0B" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel title="Integrations by Status">
          <BarBreakdown obj={data?.breakdowns?.integrations_by_status} />
        </Panel>
        <Panel title="Sync Jobs by Status">
          <BarBreakdown obj={data?.breakdowns?.sync_jobs_by_status} />
        </Panel>
      </div>
    </div>
  );
}

// ── Team tab ───────────────────────────────────────────────────────────
function TeamTab({ days }) {
  const { data, loading } = useModule("users", days, true);
  const t = data?.totals;
  if (loading && !data) return <TabLoading />;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <KpiCard label="Members" value={fmtNum(t?.members)} icon={Users} tone="#2563EB" />
        <KpiCard label="Active Users" value={fmtNum(t?.active_users)} icon={UserCog} tone="#22C55E" hint={`Active in last ${days} days`} />
      </div>
      <Panel title="Members by Role">
        <BarBreakdown obj={data?.breakdowns?.by_role} />
      </Panel>
    </div>
  );
}

// ── tab registry ───────────────────────────────────────────────────────
const TABS = [
  { key: "overview", label: "Overview", icon: LayoutDashboard, exportModule: "executive", Component: OverviewTab },
  { key: "executive", label: "Executive", icon: Gauge, exportModule: "executive", Component: ExecutiveTab },
  { key: "cost", label: "AI & Cost", icon: DollarSign, exportModule: "cost", Component: CostTab },
  { key: "insights", label: "Questions", icon: Lightbulb, exportModule: "insights", Component: InsightsTab },
  { key: "conversations", label: "Conversations", icon: MessageSquare, exportModule: "chat", Component: ConversationsTab },
  { key: "agents", label: "Agents", icon: Bot, exportModule: "agents", Component: AgentsTab },
  { key: "knowledge", label: "Knowledge", icon: BookOpen, exportModule: "knowledge", Component: KnowledgeTab },
  { key: "rag", label: "RAG", icon: ShieldCheck, exportModule: "rag", Component: RagTab },
  { key: "widget", label: "Widget", icon: Code2, exportModule: "widget", Component: WidgetTab },
  { key: "workflows", label: "Workflows", icon: Workflow, exportModule: "workflows", Component: WorkflowsTab },
  { key: "integrations", label: "Integrations", icon: Plug, exportModule: "integrations", Component: IntegrationsTab },
  { key: "team", label: "Team", icon: UserCog, exportModule: "users", Component: TeamTab },
];

export default function Analytics() {
  const [days, setDays] = useState(14);
  const [tab, setTab] = useState("overview");
  const [exporting, setExporting] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const active = TABS.find((t) => t.key === tab) || TABS[0];
  const ActiveTab = active.Component;

  const exportCsv = async () => {
    setExporting(true);
    try {
      const res = await api.get("/analytics/export", {
        params: { module: active.exportModule, days, format: "csv" },
        responseType: "blob",
      });
      const blob = new Blob([res.data], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `oraone-${active.exportModule}-${days}d.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Report exported");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <PageHeader
        eyebrow="Analytics"
        icon={LayoutDashboard}
        title="Analytics"
        subtitle="Enterprise insights across conversations, agents, knowledge, cost and ROI."
        actions={
          <>
            <div
              className="inline-flex rounded-xl bg-[#F1F5F9] p-1"
              data-testid="analytics-range"
            >
              {RANGES.map((r) => (
                <button
                  key={r.days}
                  onClick={() => setDays(r.days)}
                  className={`px-3 py-1.5 rounded-lg text-[13px] font-semibold transition-colors ${
                    days === r.days
                      ? "bg-white text-[#0F172A] shadow-sm"
                      : "text-[#64748B] hover:text-[#0F172A]"
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <GhostButton
              onClick={() => setRefreshKey((k) => k + 1)}
              data-testid="analytics-refresh"
            >
              <RefreshCw size={14} /> Refresh
            </GhostButton>
            <button
              onClick={exportCsv}
              disabled={exporting}
              data-testid="analytics-export"
              className="inline-flex items-center gap-2 rounded-full bg-[#2563EB] px-4 py-2 text-[13px] font-semibold text-white shadow-sm transition-colors hover:bg-[#1D4ED8] disabled:opacity-60"
            >
              {exporting ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Download size={14} />
              )}{" "}
              Export CSV
            </button>
          </>
        }
      />

      {/* Tab bar */}
      <div className="flex items-center gap-1 overflow-x-auto rounded-xl border border-[#E2E8F0] bg-white p-1 scrollbar-thin" data-testid="analytics-tabs">
        {TABS.map((t) => {
          const on = t.key === tab;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              data-testid={`analytics-tab-${t.key}`}
              className={`inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors ${
                on ? "bg-[#EFF6FF] text-[#2563EB]" : "text-[#475569] hover:bg-[#F8FAFC]"
              }`}
            >
              <t.icon size={15} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Active tab content (remount on refresh) */}
      <ActiveTab key={`${tab}-${days}-${refreshKey}`} days={days} />
    </div>
  );
}
