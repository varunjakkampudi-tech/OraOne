import React from "react";
import { ShieldAlert, ShieldCheck, Ban } from "lucide-react";
import {
  PageHeader, StatCard, Glass, Badge, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtNum } from "@/components/admin/format";

const sevTone = { high: "red", medium: "amber", low: "blue" };
const riskTone = { high: "red", medium: "amber", low: "green" };

export default function AdminFraud() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.fraud(), []);

  if (loading) return <div><PageHeader icon={ShieldAlert} title="AI Fraud Detection" /><LoadingState /></div>;
  if (error) return <div><PageHeader icon={ShieldAlert} title="AI Fraud Detection" /><ErrorState message={error} onRetry={reload} /></div>;

  return (
    <div>
      <PageHeader icon={ShieldAlert} title="AI Fraud Detection"
        subtitle="Spam, bots, prompt injection, abuse & credential attacks — last 7 days"
        actions={<Badge tone={riskTone[data.risk_level] || "slate"}>risk: {data.risk_level}</Badge>} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <StatCard label="Total signals" value={fmtNum(data.total_signals)} icon={ShieldAlert}
          tone={data.total_signals ? "amber" : "green"} />
        <StatCard label="High severity" value={fmtNum(data.high_severity)} icon={Ban}
          tone={data.high_severity ? "red" : "green"} />
        <StatCard label="Risk level" value={data.risk_level} icon={ShieldCheck} tone={riskTone[data.risk_level] || "slate"} />
      </div>

      <div className="mt-6">
        {data.signals.length === 0 ? (
          <EmptyState icon={ShieldCheck} title="No fraud signals detected" hint="No spam, injection or abuse seen in the last 7 days." />
        ) : (
          <div className="space-y-2">
            {data.signals.map((s, i) => (
              <Glass key={i} className="flex items-center justify-between p-4" hover>
                <div className="min-w-0 pr-4">
                  <div className="flex items-center gap-2">
                    <span className="font-medium" style={{ color: t.ink }}>{s.label}</span>
                    <Badge tone={sevTone[s.severity] || "slate"}>{s.severity}</Badge>
                  </div>
                  <p className="mt-0.5 text-xs" style={{ color: t.sub }}>{s.detail}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-lg font-semibold" style={{ color: t.ink }}>{fmtNum(s.count)}</span>
                  <Badge tone="indigo">{s.action}</Badge>
                </div>
              </Glass>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
