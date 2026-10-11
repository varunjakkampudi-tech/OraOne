import React from "react";
import { Award, AlertTriangle } from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Badge, Table, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { timeAgo } from "@/components/admin/format";

const qTone = (q) => (q >= 85 ? "green" : q >= 70 ? "blue" : q >= 50 ? "amber" : "red");

function Metric({ label, value, suffix = "/100" }) {
  const { t } = useAdminTheme();
  return (
    <Glass className="p-3.5">
      <div className="text-xs uppercase tracking-wide" style={{ color: t.sub }}>{label}</div>
      <div className="mt-1 flex items-end gap-1">
        <span className="text-xl font-semibold" style={{ color: t.ink }}>{value}</span>
        <span className="text-xs" style={{ color: t.muted }}>{suffix}</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full" style={{ background: t.line }}>
        <div className="h-full rounded-full" style={{ width: `${value}%`, background: `linear-gradient(90deg,${t.brand},${t.brand2})` }} />
      </div>
    </Glass>
  );
}

export default function AdminQuality() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.quality(), []);

  if (loading) return <div><PageHeader icon={Award} title="AI Quality Monitoring" /><LoadingState /></div>;
  if (error) return <div><PageHeader icon={Award} title="AI Quality Monitoring" /><ErrorState message={error} onRetry={reload} /></div>;

  const a = data.averages;
  const cols = [
    { key: "quality", label: "Quality", render: (r) => <Badge tone={qTone(r.quality)}>{r.quality}</Badge> },
    { key: "organization_name", label: "Customer", render: (r) => r.organization_name || "—" },
    { key: "agent_name", label: "Agent", render: (r) => r.agent_name || "—" },
    { key: "channel", label: "Channel", render: (r) => <Badge tone="blue">{r.channel}</Badge> },
    { key: "csat", label: "CSAT", render: (r) => `${r.csat}%` },
    { key: "confidence", label: "Confidence", render: (r) => `${r.confidence}%` },
    { key: "escalation_recommended", label: "Escalate", render: (r) => r.escalation_recommended ? <Badge tone="red">yes</Badge> : <Badge tone="slate">no</Badge> },
    { key: "started_at", label: "When", render: (r) => timeAgo(r.started_at) },
  ];

  return (
    <div>
      <PageHeader icon={Award} title="AI Quality Monitoring"
        subtitle={`Scored ${data.sample_size} recent conversations across all tenants`} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Avg quality" value={a.quality} icon={Award} tone={qTone(a.quality)} />
        <StatCard label="Escalations" value={data.escalations_recommended} icon={AlertTriangle}
          tone={data.escalations_recommended ? "red" : "green"} />
        <StatCard label="Excellent" value={data.distribution.excellent} tone="green" />
        <StatCard label="Poor" value={data.distribution.poor} tone={data.distribution.poor ? "red" : "slate"} />
      </div>

      <div className="mt-6">
        <SectionTitle>Quality dimensions (fleet average)</SectionTitle>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <Metric label="Accuracy" value={a.accuracy} />
          <Metric label="Hallucination-safe" value={a.hallucination} />
          <Metric label="Knowledge match" value={a.knowledge} />
          <Metric label="Confidence" value={a.confidence} />
          <Metric label="Grammar" value={a.grammar} />
          <Metric label="CSAT (pred.)" value={a.csat} suffix="%" />
        </div>
      </div>

      <div className="mt-6">
        <SectionTitle>Lowest-scoring conversations (need attention)</SectionTitle>
        <Table columns={cols} rows={data.lowest_quality}
          empty={<EmptyState icon={Award} title="No conversations scored" hint="Quality scores appear as conversations happen." />} />
      </div>
    </div>
  );
}
