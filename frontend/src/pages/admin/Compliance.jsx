import React from "react";
import { FileCheck, CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Badge, LoadingState, ErrorState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";

const statusMeta = {
  pass: { tone: "green", Icon: CheckCircle2 },
  partial: { tone: "amber", Icon: AlertCircle },
  fail: { tone: "red", Icon: XCircle },
};

export default function AdminCompliance() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.compliance(), []);

  if (loading) return <div><PageHeader icon={FileCheck} title="AI Compliance" /><LoadingState /></div>;
  if (error) return <div><PageHeader icon={FileCheck} title="AI Compliance" /><ErrorState message={error} onRetry={reload} /></div>;

  return (
    <div>
      <PageHeader icon={FileCheck} title="AI Compliance"
        subtitle="Control posture across SOC 2, ISO 27001, GDPR, CCPA, HIPAA & PCI DSS" />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Compliance score" value={`${data.score}%`} icon={FileCheck}
          tone={data.score >= 80 ? "green" : data.score >= 60 ? "amber" : "red"} />
        <StatCard label="Audit records" value={data.audit_records.toLocaleString()} icon={CheckCircle2} tone="blue" />
        <StatCard label="Controls passing" value={data.controls.filter((c) => c.status === "pass").length} tone="green" />
        <StatCard label="Needs work" value={data.controls.filter((c) => c.status !== "pass").length} tone="amber" />
      </div>

      <div className="mt-6">
        <SectionTitle>Framework readiness</SectionTitle>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          {data.frameworks.map((f) => (
            <Glass key={f.name} className="p-4 text-center">
              <div className="text-sm font-semibold" style={{ color: t.ink }}>{f.name}</div>
              <div className="mx-auto my-2 grid h-16 w-16 place-items-center rounded-full"
                style={{ background: `conic-gradient(${f.readiness >= 80 ? "#16A34A" : f.readiness >= 50 ? "#D97706" : "#DC2626"} ${f.readiness * 3.6}deg, ${t.line} 0deg)` }}>
                <div className="grid h-12 w-12 place-items-center rounded-full" style={{ background: t.glassSolid }}>
                  <span className="text-sm font-semibold" style={{ color: t.ink }}>{f.readiness}%</span>
                </div>
              </div>
            </Glass>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <SectionTitle>Controls</SectionTitle>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {data.controls.map((c) => {
            const m = statusMeta[c.status] || statusMeta.partial;
            return (
              <Glass key={c.control} className="flex items-start gap-3 p-4">
                <m.Icon className="mt-0.5 h-5 w-5 shrink-0" style={{ color: m.tone === "green" ? "#16A34A" : m.tone === "red" ? "#DC2626" : "#D97706" }} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium" style={{ color: t.ink }}>{c.control}</span>
                    <Badge tone={m.tone}>{c.status}</Badge>
                  </div>
                  <p className="mt-0.5 text-xs" style={{ color: t.sub }}>{c.detail}</p>
                </div>
              </Glass>
            );
          })}
        </div>
      </div>
    </div>
  );
}
