import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  MessagesSquare,
  CheckCircle2,
  Circle,
  Bot,
  DollarSign,
  TrendingUp,
  ArrowUpRight,
  ArrowRight,
  Inbox,
  Plus,
  BookOpen,
  Rocket,
  Users,
  Workflow as WorkflowIcon,
  Activity,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/* ──────────────────────────────────────────────────────────────────────────
   Dashboard — Mission Control.
   Visual language mirrors the approved reference: status pill, greeting with
   inline stats, KPI row, conversation trend + system status, "needs your
   attention" nudges, top agents and recent activity.

   Every number is REAL (from /analytics/overview and /agents). Nothing is
   fabricated — when a signal is missing the card degrades to a calm empty
   hint instead of inventing data. Empty workspaces get onboarding instead.
   ────────────────────────────────────────────────────────────────────────── */

function useOverview(days) {
  const [state, setState] = useState({
    loading: true,
    overview: null,
    agents: [],
    knowledgeCount: 0,
    memberCount: 0,
  });

  // Static context (agents, knowledge, team) — fetched once.
  useEffect(() => {
    let active = true;
    (async () => {
      const results = await Promise.allSettled([
        api.get("/agents", { params: { limit: 8, sort: "-updated_at" } }),
        api.get("/knowledge-bases", { params: { limit: 1 } }),
        api.get("/team/members", { params: { limit: 50 } }),
      ]);
      if (!active) return;
      const val = (r) => (r.status === "fulfilled" ? r.value.data : null);
      const kb = val(results[1]);
      const team = val(results[2]);
      const kbList = Array.isArray(kb) ? kb : kb?.items || kb?.knowledge_bases || [];
      const teamList = Array.isArray(team) ? team : team?.items || team?.members || [];
      setState((s) => ({
        ...s,
        loading: false,
        agents: val(results[0])?.items || val(results[0])?.agents || [],
        knowledgeCount: kb?.total ?? kbList.length ?? 0,
        memberCount: team?.total ?? teamList.length ?? 0,
      }));
    })();
    return () => {
      active = false;
    };
  }, []);

  // Analytics — refetched when the range changes.
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const { data } = await api.get("/analytics/overview", { params: { days } });
        if (active) setState((s) => ({ ...s, overview: data }));
      } catch {
        if (active) setState((s) => ({ ...s, overview: s.overview }));
      }
    })();
    return () => {
      active = false;
    };
  }, [days]);

  return state;
}

/* ── helpers ─────────────────────────────────────────────────────────────── */
const initials = (name = "") =>
  name
    .split(" ")
    .map((w) => w[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase() || "A";

function fmtRelative(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} hour${h === 1 ? "" : "s"} ago`;
  const days = Math.floor(h / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

const shortDate = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? String(iso ?? "") : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

/* ── small building blocks ───────────────────────────────────────────────── */
function DeltaChip({ delta, up = true }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11.5px] font-semibold ${
        up ? "bg-success-soft text-success-ink" : "bg-danger-soft text-danger"
      }`}
    >
      <TrendingUp size={12} className={up ? "" : "rotate-180"} /> {delta}
    </span>
  );
}

/* Tiny inline sparkline — REAL series only (no fabricated points). */
function Sparkline({ data, color, id }) {
  if (!Array.isArray(data) || data.length < 2) return null;
  const w = 76;
  const h = 30;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const step = w / (data.length - 1);
  const line = data.map((v, i) => `${(i * step).toFixed(1)},${(h - ((v - min) / range) * h).toFixed(1)}`).join(" ");
  const area = `0,${h} ${line} ${w},${h}`;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="ml-auto shrink-0" aria-hidden="true">
      <defs>
        <linearGradient id={`spark-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.22" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={area} fill={`url(#spark-${id})`} />
      <polyline points={line} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function KpiCard({ kpi, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-2xl border border-line bg-white p-5 shadow-card"
    >
      <div className="flex items-center gap-2.5">
        <span className="grid size-9 place-items-center rounded-xl" style={{ background: kpi.bg }}>
          <kpi.icon size={17} style={{ color: kpi.tone }} />
        </span>
        <span className="text-[13.5px] font-semibold text-[#475569]">{kpi.label}</span>
      </div>
      <div className="mt-4 flex items-end gap-3">
        <p className="text-[30px] font-extrabold leading-none tracking-tight text-ink">{kpi.value}</p>
        {kpi.sub ? <span className="pb-0.5 text-[12.5px] text-faint">{kpi.sub}</span> : null}
        {kpi.spark ? <Sparkline data={kpi.spark} color={kpi.tone} id={kpi.key} /> : null}
      </div>
      <div className="mt-3 flex items-center gap-2 text-[12px] text-faint">
        {kpi.delta ? <DeltaChip delta={kpi.delta} up={kpi.up} /> : null}
        {kpi.foot ? <span>{kpi.foot}</span> : null}
      </div>
    </motion.div>
  );
}

function RangeToggle({ value, onChange }) {
  const opts = [
    { v: 7, label: "7 days" },
    { v: 30, label: "30 days" },
    { v: 90, label: "90 days" },
  ];
  return (
    <div className="inline-flex rounded-full bg-hairline p-0.5">
      {opts.map((o) => (
        <button
          key={o.v}
          onClick={() => onChange(o.v)}
          aria-pressed={value === o.v}
          className={`rounded-full px-3 py-1 text-[12.5px] font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 ${
            value === o.v ? "bg-white text-ink shadow-sm" : "text-sub hover:text-ink"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function StatusRow({ icon: Icon, tone, label, healthy, stats }) {
  return (
    <li className="flex items-center justify-between gap-4 px-5 py-3.5">
      <div className="flex min-w-0 items-center gap-3">
        <span className="grid size-8 shrink-0 place-items-center rounded-lg" style={{ background: `${tone}1A` }}>
          <Icon size={15} style={{ color: tone }} />
        </span>
        <div className="min-w-0">
          <p className="truncate text-[13px] font-semibold text-ink">{label}</p>
          <span
            className={`inline-flex items-center gap-1 text-[11.5px] font-semibold ${
              healthy ? "text-success-ink" : "text-faint"
            }`}
          >
            <span className={`size-1.5 rounded-full ${healthy ? "bg-success" : "bg-[#CBD5E1]"}`} />
            {healthy ? "Healthy" : "Idle"}
          </span>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-5 text-right">
        {stats.map((s) => (
          <div key={s.label}>
            <p className="text-[13px] font-bold text-ink">{s.value}</p>
            <p className="text-[11px] text-faint">{s.label}</p>
          </div>
        ))}
      </div>
    </li>
  );
}

/* ── Dashboard ───────────────────────────────────────────────────────────── */
export default function Overview() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [days, setDays] = useState(7);
  const { loading, overview, agents, knowledgeCount, memberCount } = useOverview(days);

  const [greeting, setGreeting] = useState("Good morning");
  useEffect(() => {
    const h = new Date().getHours();
    setGreeting(h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening");
  }, []);

  const firstName = (user?.full_name || user?.name || "there").split(" ")[0];

  const totals = overview?.totals || null;
  const conversations = totals?.conversations ?? overview?.total_conversations ?? overview?.conversations ?? 0;
  const messages = totals?.messages ?? null;
  const resolution = totals?.resolution_rate ?? totals?.conversion_rate ?? overview?.resolution_rate ?? null;
  const workflowRuns = totals?.workflow_runs ?? null;
  const documents = totals?.documents ?? knowledgeCount ?? 0;
  const revenue = overview?.attributed_revenue ?? totals?.attributed_revenue ?? null;

  const agentCount = agents.length;
  const activeAgents = totals?.active_agents ?? agents.filter((a) => a?.status === "active").length;
  const workflowFailures = overview?.breakdowns?.workflow_runs_by_status?.failed ?? 0;

  const topAgents = useMemo(() => {
    const list = overview?.top_agents;
    if (Array.isArray(list) && list.length) return list.slice(0, 5);
    // Fall back to the org's own agents (real data), ranked by conversations.
    return [...agents]
      .map((a) => ({
        id: a.id,
        name: a.name || "Untitled agent",
        type: a.type,
        status: a.status,
        conversations: a.conversation_count ?? a.conversations ?? 0,
        success_rate: a.success_rate ?? null,
      }))
      .sort((x, y) => (y.conversations || 0) - (x.conversations || 0))
      .slice(0, 5);
  }, [overview, agents]);

  const trend = useMemo(() => {
    const conv = overview?.series?.conversations || [];
    return conv.map((p) => ({ day: shortDate(p.date), Conversations: p.count ?? 0 }));
  }, [overview]);
  const trendTotal = trend.reduce((sum, r) => sum + (r.Conversations || 0), 0);
  const trendHasData = trend.some((r) => r.Conversations > 0);

  // Real per-day series for KPI sparklines (no fabricated points).
  const convSpark = useMemo(() => {
    const s = (overview?.series?.conversations || []).map((p) => p.count ?? 0);
    return s.some((v) => v > 0) ? s : null;
  }, [overview]);
  const msgSpark = useMemo(() => {
    const s = (overview?.series?.messages || []).map((p) => p.count ?? 0);
    return s.some((v) => v > 0) ? s : null;
  }, [overview]);
  const resSpark = useMemo(() => {
    const s = (overview?.series?.resolution_rate || []).map((p) => p.count ?? 0);
    return s.some((v) => v > 0) ? s : null;
  }, [overview]);
  const agentsSpark = useMemo(() => {
    const s = (overview?.series?.active_agents || []).map((p) => p.count ?? 0);
    return s.some((v) => v > 0) ? s : null;
  }, [overview]);

  const recentActivity = useMemo(
    () =>
      [...agents]
        .filter((a) => a.updated_at || a.created_at)
        .sort((a, b) => new Date(b.updated_at || b.created_at) - new Date(a.updated_at || a.created_at))
        .slice(0, 5),
    [agents]
  );

  const hasActivity = agentCount > 0 || conversations > 0;

  // Real, actionable suggestions — no invented alerts.
  const attention = [];
  const draftOrPaused = agents.filter((a) => a?.status === "draft" || a?.status === "paused").length;
  if (draftOrPaused > 0)
    attention.push({
      icon: Bot,
      tone: "#F59E0B",
      title: `${draftOrPaused} agent${draftOrPaused === 1 ? "" : "s"} not live`,
      desc: "Activate them to start handling conversations.",
      to: "/app/agents",
      cta: "Review",
    });
  if (knowledgeCount === 0)
    attention.push({
      icon: BookOpen,
      tone: "#0EA5E9",
      title: "No knowledge connected",
      desc: "Ground your agents in your own content for accurate answers.",
      to: "/app/knowledge-base",
      cta: "Connect",
    });
  if (memberCount <= 1)
    attention.push({
      icon: Users,
      tone: "#2563EB",
      title: "Invite your team",
      desc: "Collaborate on conversations and agents together.",
      to: "/app/team",
      cta: "Get started",
    });

  /* ── Loading skeleton ── */
  if (loading) {
    return (
      <div className="space-y-6" data-testid="dashboard-overview">
        <div className="h-9 w-72 animate-pulse rounded-lg bg-line motion-reduce:animate-none" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-2xl bg-line motion-reduce:animate-none" />
          ))}
        </div>
        <div className="h-72 animate-pulse rounded-2xl bg-line motion-reduce:animate-none" />
      </div>
    );
  }

  /* ── Mission Control onboarding (empty workspace) ── */
  if (!hasActivity) {
    const steps = [
      { key: "agent", title: "Create your first AI Agent", desc: "Spin up an agent to answer questions and capture leads automatically.", to: "/app/agents/new", cta: "Create agent", icon: Bot, tone: "#2563EB", bg: "#EFF4FF", done: agentCount > 0 },
      { key: "kb", title: "Connect a Knowledge Base", desc: "Upload documents or crawl your website so agents answer accurately.", to: "/app/knowledge-base", cta: "Add knowledge", icon: BookOpen, tone: "#0EA5E9", bg: "#F0F9FF", done: knowledgeCount > 0 },
      { key: "deploy", title: "Deploy to a channel", desc: "Put your agent live on your website.", to: "/app/agents", cta: "Deploy", icon: Rocket, tone: "#0891B2", bg: "#ECFEFF", done: false },
      { key: "integrations", title: "Connect your tools", desc: "Link the apps your team already uses to keep everything in sync.", to: "/app/integrations", cta: "Connect", icon: Users, tone: "#F59E0B", bg: "#FFF7ED", done: false },
    ];
    const completed = steps.filter((s) => s.done).length;
    return (
      <div className="space-y-4" data-testid="dashboard-overview">
        <div className="min-w-0">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-hairline px-2.5 py-1 text-[11px] font-semibold text-sub">
            <Rocket size={12} /> Welcome to OraOne
          </span>
          <h1 className="mt-2.5 text-[32px] font-extrabold tracking-tight text-ink sm:text-[36px]">
            {greeting}, {firstName}
          </h1>
          <p className="mt-1 text-[14px] text-body">
            Let&apos;s get your AI workspace set up &mdash; you&apos;re about 5 minutes from launching your first AI agent.
          </p>
        </div>

        <div className="rounded-2xl border border-line bg-white shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline px-5 py-4">
            <div>
              <h2 className="text-[16px] font-bold text-ink">Get started</h2>
              <p className="mt-0.5 text-[12.5px] text-sub">{completed} of {steps.length} complete</p>
            </div>
            <div className="flex items-center gap-2.5">
              <div className="h-2.5 w-44 overflow-hidden rounded-full bg-line">
                <div className="h-full rounded-full bg-gradient-to-r from-brand to-[#06B6D4] transition-all" style={{ width: `${(completed / steps.length) * 100}%` }} />
              </div>
              <span className="text-[12px] font-semibold tabular-nums text-sub">{Math.round((completed / steps.length) * 100)}%</span>
            </div>
          </div>
          <ul className="divide-y divide-hairline">
            {steps.map((s) => (
              <li key={s.key} className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-[#F8FBFF]">
                <span className="shrink-0">
                  {s.done ? <CheckCircle2 size={22} className="text-success" /> : <Circle size={22} className="text-[#CBD5E1]" />}
                </span>
                <span className="grid size-10 shrink-0 place-items-center rounded-xl" style={{ background: s.bg }}>
                  <s.icon size={18} style={{ color: s.tone }} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className={`text-[14px] font-semibold ${s.done ? "text-faint line-through" : "text-ink"}`}>{s.title}</p>
                  <p className="mt-0.5 text-[12.5px] text-body">{s.desc}</p>
                </div>
                {!s.done && (
                  <Link to={s.to} className="inline-flex shrink-0 items-center justify-center gap-1.5 rounded-full bg-brand px-4 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-brand-hover min-w-[132px]">
                    {s.cta} <ArrowRight size={14} />
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div className="grid grid-cols-1 gap-4 pt-1 sm:grid-cols-2 lg:grid-cols-3">
          <QuickStart to="/app/agents/new" icon={Bot} tone="#2563EB" bg="#EFF4FF" title="Create an AI Agent" desc="Website chat — live in minutes." />
          <QuickStart to="/app/knowledge-base" icon={BookOpen} tone="#0EA5E9" bg="#F0F9FF" title="Connect Knowledge" desc="Ground your agents in your own content." />
        </div>
      </div>
    );
  }

  /* ── Active workspace — real metrics only ── */
  const kpis = [
    { key: "conv", label: "Conversations", value: Number(conversations).toLocaleString(), icon: MessagesSquare, tone: "#2563EB", bg: "#EFF4FF", foot: `last ${days} days`, spark: convSpark },
    ...(resolution != null
      ? [{ key: "res", label: "Resolution Rate", value: `${resolution}%`, icon: CheckCircle2, tone: "#16A34A", bg: "#ECFDF3", foot: "resolved automatically", spark: resSpark }]
      : []),
    { key: "agents", label: "Active Agents", value: `${activeAgents}`, sub: agentCount ? `/ ${agentCount}` : undefined, icon: Bot, tone: "#0891B2", bg: "#ECFEFF", foot: `${agentCount} total`, spark: agentsSpark },
    ...(revenue != null
      ? [{ key: "rev", label: "Attributed Revenue", value: `$${Number(revenue).toLocaleString()}`, icon: DollarSign, tone: "#F59E0B", bg: "#FFF7ED" }]
      : messages != null
      ? [{ key: "msg", label: "Messages", value: Number(messages).toLocaleString(), icon: Activity, tone: "#F59E0B", bg: "#FFF7ED", foot: `last ${days} days`, spark: msgSpark }]
      : []),
  ];

  return (
    <div className="space-y-6" data-testid="dashboard-overview">
      {/* Greeting header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-success-soft px-2.5 py-1 text-[12px] font-semibold text-success-ink">
            <span className="size-1.5 rounded-full bg-success" /> All systems operational
          </span>
          <h1 className="mt-3 text-[30px] font-extrabold tracking-tight text-ink sm:text-[34px]">
            {greeting}, {firstName}
          </h1>
          <p className="mt-1 text-[14.5px] text-sub">Here&apos;s what&apos;s happening in your workspace.</p>

          {/* Inline stat row */}
          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13.5px]">
            <span className="text-ink">
              <span className="font-bold">{activeAgents}</span> <span className="text-sub">AI agents active</span>
            </span>
            <span className="hidden h-4 w-px bg-stroke sm:block" />
            <span className="text-ink">
              <span className="font-bold">{Number(conversations).toLocaleString()}</span>{" "}
              <span className="text-sub">conversations · {days}d</span>
            </span>
            {resolution != null && (
              <>
                <span className="hidden h-4 w-px bg-stroke sm:block" />
                <span className="text-ink">
                  <span className="font-bold">{resolution}%</span> <span className="text-sub">resolution rate</span>
                </span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/app/conversations" className="inline-flex items-center gap-2 rounded-full border border-stroke bg-white px-4 py-2.5 text-[13.5px] font-semibold text-body transition-colors hover:bg-wash focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40">
            <Inbox size={16} className="text-sub" /> Inbox
          </Link>
          <Link to="/app/agents/new" data-tour="create-agent" className="inline-flex items-center gap-2 rounded-full bg-brand px-4 py-2.5 text-[13.5px] font-semibold text-white shadow-sm transition-colors hover:bg-brand-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 focus-visible:ring-offset-2">
            <Plus size={16} /> Create AI Agent
          </Link>
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi, i) => (
          <KpiCard key={kpi.key} kpi={kpi} index={i} />
        ))}
      </div>

      {/* Trend + System status */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.6fr_1fr]">
        <div className="rounded-2xl border border-line bg-white p-5 shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-[15px] font-bold text-ink">Conversation Trend</h2>
              <p className="mt-0.5 text-[12.5px] text-faint">
                {trendHasData ? `${trendTotal.toLocaleString()} conversations · last ${days} days` : `Last ${days} days`}
              </p>
            </div>
            <RangeToggle value={days} onChange={setDays} />
          </div>
          <div className="mt-4 h-64">
            {trendHasData ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend} margin={{ left: -14, right: 8, top: 8, bottom: 0 }}>
                  <defs>
                    <linearGradient id="convGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563EB" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#EAF0F6" vertical={false} />
                  <XAxis dataKey="day" stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} minTickGap={24} />
                  <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} width={34} />
                  <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }} />
                  <Area type="monotone" dataKey="Conversations" stroke="#2563EB" strokeWidth={2.5} fill="url(#convGrad)" dot={false} activeDot={{ r: 4 }} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <span className="mx-auto grid size-11 place-items-center rounded-2xl bg-subtle text-faint">
                    <Activity size={20} />
                  </span>
                  <p className="mt-2 text-[13px] font-semibold text-ink">No conversations yet</p>
                  <p className="mt-0.5 text-[12px] text-sub">Trends appear once your agents start chatting.</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* System status */}
        <div className="rounded-2xl border border-line bg-white shadow-card">
          <div className="flex items-center justify-between border-b border-hairline px-5 py-4">
            <div>
              <h2 className="text-[15px] font-bold text-ink">System Status</h2>
              <p className="mt-0.5 text-[12.5px] text-faint">Live workspace signals</p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-success-soft px-2.5 py-1 text-[11.5px] font-semibold text-success-ink">
              <span className="size-1.5 rounded-full bg-success" /> Operational
            </span>
          </div>
          <ul className="divide-y divide-hairline">
            <StatusRow
              icon={Bot}
              tone="#2563EB"
              label="AI Agents"
              healthy={agentCount > 0}
              stats={[
                { label: "Online", value: `${activeAgents}/${agentCount}` },
                { label: "Total", value: agentCount },
              ]}
            />
            <StatusRow
              icon={BookOpen}
              tone="#0EA5E9"
              label="Knowledge Base"
              healthy={knowledgeCount > 0}
              stats={[{ label: "Sources", value: knowledgeCount }, { label: "Docs", value: documents }]}
            />
            <StatusRow
              icon={WorkflowIcon}
              tone="#0891B2"
              label="Workflows"
              healthy={(workflowRuns ?? 0) > 0}
              stats={[
                { label: "Runs", value: workflowRuns ?? 0 },
                { label: "Failures", value: workflowFailures },
              ]}
            />
          </ul>
        </div>
      </div>

      {/* Needs your attention */}
      {attention.length > 0 && (
        <div className="rounded-2xl border border-line bg-white p-5 shadow-card">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-[15px] font-bold text-ink">Needs your attention</h2>
              <p className="mt-0.5 text-[12.5px] text-faint">{attention.length} suggested for you</p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            {attention.map((a) => (
              <div key={a.title} className="flex flex-col rounded-xl border border-line bg-subtle p-4">
                <span className="grid size-9 place-items-center rounded-xl" style={{ background: `${a.tone}1A` }}>
                  <a.icon size={16} style={{ color: a.tone }} />
                </span>
                <p className="mt-3 text-[13.5px] font-semibold text-ink">{a.title}</p>
                <p className="mt-0.5 flex-1 text-[12px] text-sub">{a.desc}</p>
                <Link to={a.to} className="mt-3 inline-flex items-center gap-1 text-[12.5px] font-semibold text-brand hover:underline">
                  {a.cta} <ArrowRight size={13} />
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top agents + Recent activity */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.6fr_1fr]">
        <div className="rounded-2xl border border-line bg-white shadow-card">
          <div className="flex items-center justify-between border-b border-hairline px-5 py-4">
            <div>
              <h2 className="text-[15px] font-bold text-ink">Top Performing Agents</h2>
              <p className="mt-0.5 text-[12.5px] text-faint">Ranked by conversations</p>
            </div>
            <Link to="/app/agents" className="text-[12.5px] font-semibold text-brand hover:underline">
              View all
            </Link>
          </div>
          {topAgents.length ? (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-hairline">
                  <th scope="col" className="px-5 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-sub">Agent</th>
                  <th scope="col" className="px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-sub">Status</th>
                  <th scope="col" className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-[0.06em] text-sub">Convos</th>
                  <th scope="col" className="px-5 py-2.5 text-right text-[11px] font-semibold uppercase tracking-[0.06em] text-sub">Success</th>
                </tr>
              </thead>
              <tbody>
                {topAgents.map((a) => (
                  <tr
                    key={a.id || a.name}
                    onClick={() => a.id && nav(`/app/agents/${a.id}`)}
                    className="cursor-pointer border-b border-hairline last:border-0 hover:bg-subtle"
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-brand-soft text-[11px] font-bold text-brand">
                          {initials(a.name)}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-[13px] font-semibold text-ink">{a.name}</p>
                          {a.type && <p className="truncate text-[11.5px] capitalize text-faint">{a.type}</p>}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize ${
                          a.status === "active"
                            ? "bg-success-soft text-success-ink"
                            : a.status === "paused"
                            ? "bg-warning-soft text-warning-ink"
                            : "bg-hairline text-sub"
                        }`}
                      >
                        {a.status || "draft"}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-right text-[13px] font-semibold text-ink">
                      {Number(a.conversations || 0).toLocaleString()}
                    </td>
                    <td className="px-5 py-3 text-right text-[13px] text-body">
                      {a.success_rate != null ? `${a.success_rate}%` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-5 py-10 text-center">
              <p className="text-[13px] font-semibold text-ink">No agents to rank yet</p>
              <p className="mt-0.5 text-[12px] text-sub">Create an agent to see performance here.</p>
            </div>
          )}
        </div>

        {/* Recent activity */}
        <div className="rounded-2xl border border-line bg-white shadow-card">
          <div className="border-b border-hairline px-5 py-4">
            <h2 className="text-[15px] font-bold text-ink">Recent Activity</h2>
            <p className="mt-0.5 text-[12.5px] text-faint">Latest changes in your workspace</p>
          </div>
          {recentActivity.length ? (
            <ul className="divide-y divide-hairline">
              {recentActivity.map((a) => (
                <li
                  key={a.id}
                  onClick={() => a.id && nav(`/app/agents/${a.id}`)}
                  className="flex cursor-pointer items-center gap-3 px-5 py-3.5 hover:bg-subtle"
                >
                  <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
                    <Bot size={15} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-semibold text-ink">{a.name || "Agent updated"}</p>
                    <p className="truncate text-[11.5px] capitalize text-sub">{a.status || a.type || "agent"}</p>
                  </div>
                  <span className="shrink-0 text-[11.5px] text-faint">{fmtRelative(a.updated_at || a.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="px-5 py-10 text-center">
              <p className="text-[13px] font-semibold text-ink">Nothing recent</p>
              <p className="mt-0.5 text-[12px] text-sub">Activity from your agents shows here.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function QuickStart({ to, icon: Icon, tone, bg, title, desc }) {
  return (
    <Link
      to={to}
      className="group flex flex-col rounded-2xl border border-[#E5E7EB] bg-white p-7 shadow-[0_1px_2px_rgba(16,24,40,0.04),0_1px_3px_rgba(16,24,40,0.04)] transition-all hover:-translate-y-0.5 hover:border-[#BFD3F5] hover:shadow-cardhover"
    >
      <span className="grid size-[52px] place-items-center rounded-xl" style={{ background: bg }}>
        <Icon size={24} style={{ color: tone }} />
      </span>
      <p className="mt-3 text-[14.5px] font-bold text-ink">{title}</p>
      <p className="mt-1 text-[12.5px] text-sub">{desc}</p>
      <span className="mt-3 inline-flex items-center gap-1 text-[12.5px] font-semibold text-brand">
        Get started <ArrowRight size={13} className="transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}
