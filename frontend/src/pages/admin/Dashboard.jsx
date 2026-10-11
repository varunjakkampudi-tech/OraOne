import React from "react";
import {
  LayoutDashboard, Users, Building2, Crown, FlaskConical, DollarSign, TrendingUp,
  UserPlus, Radio, MessagesSquare, Activity, Cpu, MemoryStick, HardDrive,
  Database, CheckCircle2, AlertTriangle, RefreshCw, Bot, Sparkles,
} from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Badge, Btn, LoadingState, ErrorState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtNum, fmtMoney, fmtBytes, timeAgo } from "@/components/admin/format";

function HealthPill({ health }) {
  const tone = health?.status === "operational" ? "green" : health?.status === "watch" ? "amber" : "red";
  const label = health?.status === "operational" ? "All systems operational" : health?.status === "watch" ? "Watching" : "Degraded";
  return <Badge tone={tone}>{tone === "green" ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertTriangle className="h-3.5 w-3.5" />}{label}</Badge>;
}

function ActivityFeed() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.activity(40), []);
  return (
    <Glass className="p-5">
      <SectionTitle right={<Btn variant="ghost" size="sm" onClick={reload}><RefreshCw className="h-3.5 w-3.5" /></Btn>}>Real-time activity</SectionTitle>
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (data || []).length === 0 ? (
        <p className="py-8 text-center text-sm" style={{ color: t.sub }}>No recent activity.</p>
      ) : (
        <div className="max-h-[460px] space-y-1 overflow-y-auto scrollbar-thin">
          {data.map((a) => (
            <div key={a.id} className="flex items-center gap-3 rounded-lg px-2 py-2" style={{ borderBottom: `1px solid ${t.line}` }}>
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg" style={{ background: t.chipBg }}>
                <Activity className="h-4 w-4" style={{ color: t.brand }} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm" style={{ color: t.ink }}>{a.label}</div>
                <div className="truncate text-xs" style={{ color: t.muted }}>
                  {a.organization_name || "Platform"}{a.actor_email ? ` · ${a.actor_email}` : ""}
                </div>
              </div>
              <span className="shrink-0 text-xs" style={{ color: t.muted }}>{timeAgo(a.created_at)}</span>
            </div>
          ))}
        </div>
      )}
    </Glass>
  );
}

export default function AdminDashboard() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.overview(), []);

  return (
    <div>
      <PageHeader
        icon={LayoutDashboard}
        title="Platform Dashboard"
        subtitle="Global, real-time view across every OraOne tenant."
        actions={
          <div className="flex items-center gap-2">
            {data?.health ? <HealthPill health={data.health} /> : null}
            <Btn variant="ghost" size="sm" onClick={reload}><RefreshCw className="h-4 w-4" /> Refresh</Btn>
          </div>
        }
      />

      {loading ? <LoadingState label="Loading platform metrics…" /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
            <StatCard label="Total Customers" value={fmtNum(data.customers.total)} icon={Users} tone="blue" />
            <StatCard label="Active" value={fmtNum(data.customers.active)} icon={Building2} tone="green" sub="30-day active" />
            <StatCard label="Enterprise" value={fmtNum(data.customers.enterprise)} icon={Crown} tone="purple" />
            <StatCard label="Trials" value={fmtNum(data.customers.trial)} icon={FlaskConical} tone="amber" />
            <StatCard label="New Signups" value={fmtNum(data.customers.new_signups_7d)} icon={UserPlus} tone="blue" sub="last 7 days" />
            <StatCard label="MRR" value={fmtMoney(data.revenue.mrr)} icon={DollarSign} tone="green" />
            <StatCard label="ARR" value={fmtMoney(data.revenue.arr)} icon={TrendingUp} tone="green" />
            <StatCard label="Online Users" value={fmtNum(data.live.online_users)} icon={Radio} tone="blue" sub="last 15 min" />
            <StatCard label="Concurrent Chats" value={fmtNum(data.live.concurrent_chats)} icon={MessagesSquare} tone="indigo" />
            <StatCard label="API req/sec" value={fmtNum(data.live.api_requests_per_sec)} icon={Activity} tone="blue" />
            <StatCard label="LLM Tokens" value={fmtNum(data.live.llm_tokens_24h)} icon={Sparkles} tone="purple" sub="last 24h" />
            <StatCard label="Error Rate" value={`${data.reliability.error_rate}%`} icon={AlertTriangle} tone={data.reliability.error_rate >= 1 ? "red" : "green"} sub="24h" />
            <StatCard label="Success Rate" value={`${data.reliability.success_rate}%`} icon={CheckCircle2} tone="green" sub="24h" />
            <StatCard label="CPU" value={data.system.cpu == null ? "—" : `${data.system.cpu}%`} icon={Cpu} tone="slate" />
            <StatCard label="RAM" value={data.system.ram == null ? "—" : `${data.system.ram}%`} icon={MemoryStick} tone="slate" />
            <StatCard label="Disk" value={data.system.disk == null ? "—" : `${data.system.disk}%`} icon={HardDrive} tone="slate" />
            <StatCard label="Storage" value={fmtBytes(data.storage.bytes)} icon={Database} tone="blue" />
            <StatCard label="Agents" value={fmtNum(data.counts.agents)} icon={Bot} tone="indigo" />
            <StatCard label="Conversations" value={fmtNum(data.counts.conversations)} icon={MessagesSquare} tone="blue" />
            <StatCard label="Leads" value={fmtNum(data.counts.leads)} icon={Users} tone="green" />
            <StatCard label="Documents" value={fmtNum(data.counts.documents)} icon={Database} tone="slate" />
            <StatCard label="Workflows" value={fmtNum(data.counts.workflows)} icon={Activity} tone="purple" />
            <StatCard label="Users" value={fmtNum(data.counts.users)} icon={Users} tone="blue" />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
            <div className="lg:col-span-2"><ActivityFeed /></div>
            <Glass className="p-5">
              <SectionTitle>Platform footprint</SectionTitle>
              <div className="space-y-3">
                {[
                  ["Knowledge bases", data.counts.knowledge_bases],
                  ["Widgets / channels", data.counts.widgets],
                  ["Integrations", data.counts.integrations],
                  ["Projects", data.counts.projects],
                  ["API requests (24h)", data.reliability.api_requests_24h],
                ].map(([label, val]) => (
                  <div key={label} className="flex items-center justify-between">
                    <span className="text-sm" style={{ color: t.sub }}>{label}</span>
                    <span className="text-sm font-semibold" style={{ color: t.ink }}>{fmtNum(val)}</span>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-[11px]" style={{ color: t.muted }}>
                Updated {timeAgo(data.generated_at)} · host metrics via {data.system.source}
              </p>
            </Glass>
          </div>
        </>
      )}
    </div>
  );
}
