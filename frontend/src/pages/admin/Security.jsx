import React from "react";
import { ShieldCheck, AlertTriangle } from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Badge, Table, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { timeAgo, fmtNum } from "@/components/admin/format";

const sevTone = { critical: "red", high: "red", medium: "amber", low: "blue", info: "slate" };

export default function AdminSecurity() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.security(), []);

  const cols = [
    { key: "severity", label: "Severity", render: (r) => <Badge tone={sevTone[r.severity] || "slate"}>{r.severity}</Badge> },
    { key: "event_type", label: "Type", render: (r) => <span style={{ color: t.ink }}>{(r.event_type || "").replace(/_/g, " ")}</span> },
    { key: "title", label: "Title", render: (r) => r.title },
    { key: "organization_name", label: "Customer", render: (r) => r.organization_name || "Platform" },
    { key: "ip_address", label: "IP", render: (r) => r.ip_address || "—" },
    { key: "created_at", label: "When", render: (r) => timeAgo(r.created_at) },
  ];

  const score = data?.security_score ?? null;
  const scoreTone = score == null ? "slate" : score >= 90 ? "green" : score >= 70 ? "amber" : "red";

  return (
    <div>
      <PageHeader icon={ShieldCheck} title="Security Center" subtitle="Threat detections, auth anomalies and platform security posture." />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <StatCard label="Security Score" value={score == null ? "—" : `${score}/100`} icon={ShieldCheck} tone={scoreTone} />
            {(data.by_severity || []).slice(0, 4).map((s) => (
              <StatCard key={s.severity} label={s.severity} value={fmtNum(s.count)} icon={AlertTriangle} tone={sevTone[s.severity] || "slate"} />
            ))}
          </div>

          <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-3">
            <Glass className="p-5">
              <SectionTitle>By event type</SectionTitle>
              {(data.by_type || []).length === 0 ? <p className="text-sm" style={{ color: t.muted }}>No events.</p> : (
                <div className="space-y-2">
                  {data.by_type.map((x) => (
                    <div key={x.type} className="flex items-center justify-between text-sm">
                      <span style={{ color: t.sub }}>{(x.type || "").replace(/_/g, " ")}</span>
                      <span className="font-semibold" style={{ color: t.ink }}>{fmtNum(x.count)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Glass>
            <div className="lg:col-span-2">
              <SectionTitle>Recent security events</SectionTitle>
              <Table columns={cols} rows={data.recent} empty={<EmptyState icon={ShieldCheck} title="No security events" hint="The platform is quiet — nothing flagged." />} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
