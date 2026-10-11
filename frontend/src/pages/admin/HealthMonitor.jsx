import React from "react";
import { HeartPulse, CheckCircle2, XCircle, MinusCircle, RefreshCw } from "lucide-react";
import {
  PageHeader, StatCard, Glass, Badge, Btn, LoadingState, ErrorState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";

const statusMeta = {
  operational: { tone: "green", Icon: CheckCircle2, label: "Operational" },
  down: { tone: "red", Icon: XCircle, label: "Down" },
  not_configured: { tone: "slate", Icon: MinusCircle, label: "Not configured" },
};
const overallTone = { operational: "green", degraded: "amber", critical: "red" };

export default function AdminHealthMonitor() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.healthMonitor(), []);

  if (loading) return <div><PageHeader icon={HeartPulse} title="AI Health Monitor" /><LoadingState /></div>;
  if (error) return <div><PageHeader icon={HeartPulse} title="AI Health Monitor" /><ErrorState message={error} onRetry={reload} /></div>;

  return (
    <div>
      <PageHeader icon={HeartPulse} title="AI Health Monitor"
        subtitle="Continuous checks of every critical dependency · founders alerted before customers feel it"
        actions={<div className="flex items-center gap-2">
          <Badge tone={overallTone[data.overall] || "slate"}>{data.overall}</Badge>
          <Btn variant="ghost" size="sm" onClick={reload}><RefreshCw className="h-4 w-4" /> Re-check</Btn>
        </div>} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Checks" value={data.summary.total} icon={HeartPulse} tone="blue" />
        <StatCard label="Operational" value={data.summary.operational} icon={CheckCircle2} tone="green" />
        <StatCard label="Down" value={data.summary.down} icon={XCircle} tone={data.summary.down ? "red" : "slate"} />
        <StatCard label="Not configured" value={data.summary.not_configured} icon={MinusCircle} tone="slate" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data.checks.map((c) => {
          const m = statusMeta[c.status] || statusMeta.not_configured;
          return (
            <Glass key={c.name} className="flex items-center justify-between p-4" hover>
              <div className="flex items-center gap-3">
                <m.Icon className="h-5 w-5" style={{ color: m.tone === "green" ? "#16A34A" : m.tone === "red" ? "#DC2626" : t.muted }} />
                <div>
                  <div className="font-medium" style={{ color: t.ink }}>{c.name}</div>
                  <div className="text-xs capitalize" style={{ color: t.muted }}>{c.category}</div>
                </div>
              </div>
              <Badge tone={m.tone}>{m.label}</Badge>
            </Glass>
          );
        })}
      </div>

      <p className="mt-4 text-[11px]" style={{ color: t.muted }}>{data.note}</p>
    </div>
  );
}
