import React from "react";
import { BarChart3, Users, MessageSquare, UserPlus, FileText, Workflow, Boxes } from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Table, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtNum } from "@/components/admin/format";

export default function AdminAnalytics() {
  const { t } = useAdminTheme();
  const overview = useAdminData(() => superAdminApi.overview(), []);
  const usage = useAdminData(() => superAdminApi.usage(), []);

  if (overview.loading || usage.loading) return <div><PageHeader icon={BarChart3} title="Analytics" /><LoadingState /></div>;
  if (overview.error) return <div><PageHeader icon={BarChart3} title="Analytics" /><ErrorState message={overview.error} onRetry={overview.reload} /></div>;

  const c = overview.data.counts;
  const cards = [
    { label: "Conversations", value: c.conversations, icon: MessageSquare, tone: "blue" },
    { label: "Leads", value: c.leads, icon: UserPlus, tone: "green" },
    { label: "Agents", value: c.agents, icon: Boxes, tone: "purple" },
    { label: "Documents", value: c.documents, icon: FileText, tone: "indigo" },
    { label: "Workflows", value: c.workflows, icon: Workflow, tone: "amber" },
    { label: "Users", value: c.users, icon: Users, tone: "slate" },
  ];

  const orgCols = [
    { key: "name", label: "Customer", render: (r) => <span style={{ color: t.ink }}>{r.name}</span> },
    { key: "value", label: "Usage", render: (r) => <span className="font-semibold" style={{ color: t.ink }}>{fmtNum(r.value)}</span> },
  ];

  return (
    <div>
      <PageHeader icon={BarChart3} title="Analytics" subtitle="Aggregate platform performance and adoption." />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        {cards.map((x) => <StatCard key={x.label} label={x.label} value={fmtNum(x.value)} icon={x.icon} tone={x.tone} />)}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Glass className="p-5">
          <SectionTitle>Usage by metric</SectionTitle>
          {(usage.data?.totals || []).length === 0 ? <EmptyState title="No usage yet" /> : (
            <div className="space-y-2">
              {usage.data.totals.map((m) => (
                <div key={m.metric} className="flex items-center justify-between rounded-lg px-3 py-2" style={{ background: t.hover }}>
                  <span className="text-sm" style={{ color: t.sub }}>{m.metric.replace(/_/g, " ")}</span>
                  <span className="text-sm font-semibold" style={{ color: t.ink }}>{fmtNum(m.value)}</span>
                </div>
              ))}
            </div>
          )}
        </Glass>
        <div>
          <SectionTitle>Top customers by usage</SectionTitle>
          <Table columns={orgCols} rows={usage.data?.top_organizations || []} empty={<EmptyState title="No usage yet" />} />
        </div>
      </div>
    </div>
  );
}
