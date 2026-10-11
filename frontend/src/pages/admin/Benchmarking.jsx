import React from "react";
import { TrendingUp, ArrowUpRight, ArrowDownRight, Minus, Trophy } from "lucide-react";
import {
  PageHeader, Glass, SectionTitle, Badge, Table, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtNum } from "@/components/admin/format";

function Delta({ value, suffix = "" }) {
  const { t } = useAdminTheme();
  if (value == null) return <span style={{ color: t.muted }}>—</span>;
  const up = value > 0, flat = value === 0;
  const c = flat ? t.muted : up ? "#16A34A" : "#DC2626";
  const Icon = flat ? Minus : up ? ArrowUpRight : ArrowDownRight;
  return <span className="inline-flex items-center gap-0.5 text-sm font-semibold" style={{ color: c }}>
    <Icon className="h-3.5 w-3.5" />{value > 0 ? "+" : ""}{value}{suffix}</span>;
}

export default function AdminBenchmarking() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.benchmarking(), []);

  if (loading) return <div><PageHeader icon={TrendingUp} title="AI Benchmarking" /><LoadingState /></div>;
  if (error) return <div><PageHeader icon={TrendingUp} title="AI Benchmarking" /><ErrorState message={error} onRetry={reload} /></div>;

  const agentCols = [
    { key: "rank", label: "#", render: (r, i) => <span style={{ color: t.muted }}>{(data.top_agents.indexOf(r)) + 1}</span> },
    { key: "name", label: "Agent", render: (r) => <span className="font-medium" style={{ color: t.ink }}>{r.name}</span> },
    { key: "organization_name", label: "Customer", render: (r) => r.organization_name || "—" },
    { key: "conversations", label: "Conversations", render: (r) => fmtNum(r.conversations) },
  ];

  return (
    <div>
      <PageHeader icon={TrendingUp} title="AI Benchmarking"
        subtitle="Performance vs industry baseline, last month and top performers" />

      <SectionTitle>Key metrics</SectionTitle>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {data.metrics.map((m) => (
          <Glass key={m.metric} className="p-4">
            <div className="text-xs uppercase tracking-wide" style={{ color: t.sub }}>{m.metric}</div>
            <div className="mt-1 text-2xl font-semibold" style={{ color: t.ink }}>{m.value}{m.unit}</div>
            <div className="mt-3 space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span style={{ color: t.muted }}>vs industry ({m.industry}{m.unit})</span>
                <Delta value={m.vs_industry} suffix={m.unit} />
              </div>
              <div className="flex items-center justify-between">
                <span style={{ color: t.muted }}>vs last month{m.last_month != null ? ` (${m.last_month}${m.unit})` : ""}</span>
                <Delta value={m.vs_last_month} suffix={m.unit} />
              </div>
            </div>
          </Glass>
        ))}
      </div>

      <div className="mt-6">
        <SectionTitle right={<Badge tone="amber"><Trophy className="h-3.5 w-3.5" /> Leaderboard</Badge>}>Top performing agents</SectionTitle>
        <Table columns={agentCols} rows={data.top_agents}
          empty={<EmptyState icon={Trophy} title="No agent activity yet" hint="Rankings appear as agents handle conversations." />} />
      </div>
    </div>
  );
}
