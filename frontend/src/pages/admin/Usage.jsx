import React from "react";
import { Gauge } from "lucide-react";
import {
  PageHeader, Glass, SectionTitle, Table, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtNum } from "@/components/admin/format";

export default function AdminUsage() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.usage(), []);

  const orgCols = [
    { key: "name", label: "Customer", render: (r) => <span style={{ color: t.ink }}>{r.name}</span> },
    { key: "value", label: "Total usage", render: (r) => <span className="font-semibold" style={{ color: t.ink }}>{fmtNum(r.value)}</span> },
  ];

  return (
    <div>
      <PageHeader icon={Gauge} title="Usage" subtitle="Consumption across chats, tokens, storage and API." />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Glass className="p-5">
            <SectionTitle>Platform totals by metric</SectionTitle>
            {(data.totals || []).length === 0 ? <EmptyState title="No usage recorded yet" /> : (
              <div className="space-y-2">
                {data.totals.map((m) => (
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
            <Table columns={orgCols} rows={data.top_organizations} empty={<EmptyState title="No usage yet" />} />
          </div>
        </div>
      )}
    </div>
  );
}
