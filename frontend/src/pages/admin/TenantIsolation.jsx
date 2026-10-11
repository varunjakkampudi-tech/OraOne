import React from "react";
import { Network, ShieldCheck, Lock } from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Badge, LoadingState, ErrorState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";

const statusTone = { enforced: "green", available: "blue", partial: "amber" };

export default function AdminTenantIsolation() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.tenantIsolation(), []);

  if (loading) return <div><PageHeader icon={Network} title="Tenant Isolation" /><LoadingState /></div>;
  if (error) return <div><PageHeader icon={Network} title="Tenant Isolation" /><ErrorState message={error} onRetry={reload} /></div>;

  return (
    <div>
      <PageHeader icon={Network} title="Tenant Isolation"
        subtitle="How every customer's data is kept separate across the stack" />

      <Glass className="mb-5 flex items-start gap-3 p-4">
        <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0" style={{ color: "#16A34A" }} />
        <p className="text-sm" style={{ color: t.sub }}>{data.guarantee}</p>
      </Glass>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Active tenants" value={data.tenants.toLocaleString()} icon={Network} tone="blue" />
        <StatCard label="Dimensions enforced" value={`${data.summary.enforced}/${data.summary.total}`} icon={Lock} tone="green" />
        <Glass className="col-span-2 p-4">
          <div className="text-xs uppercase tracking-wide" style={{ color: t.sub }}>Isolation model</div>
          <div className="mt-1 text-sm font-medium" style={{ color: t.ink }}>{data.isolation_model}</div>
        </Glass>
      </div>

      <div className="mt-6">
        <SectionTitle>Isolation by layer</SectionTitle>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {data.dimensions.map((d) => (
            <Glass key={d.dimension} className="p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium" style={{ color: t.ink }}>{d.dimension}</span>
                <Badge tone={statusTone[d.status] || "slate"}>{d.status}</Badge>
              </div>
              <div className="mt-0.5 text-xs font-medium" style={{ color: t.brand }}>{d.isolation}</div>
              <p className="mt-1 text-xs" style={{ color: t.sub }}>{d.detail}</p>
            </Glass>
          ))}
        </div>
      </div>
    </div>
  );
}
