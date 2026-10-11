import React from "react";
import { Server, Cpu, MemoryStick, HardDrive, CheckCircle2, AlertTriangle, RefreshCw } from "lucide-react";
import {
  PageHeader, StatCard, Glass, Badge, Btn, LoadingState, ErrorState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";

const statusTone = { operational: "green", degraded: "amber", down: "red" };

export default function AdminInfrastructure() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.infrastructure(), []);

  return (
    <div>
      <PageHeader icon={Server} title="Infrastructure" subtitle="Health of every platform service."
        actions={<Btn variant="ghost" size="sm" onClick={reload}><RefreshCw className="h-4 w-4" /> Refresh</Btn>} />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <StatCard label="Services" value={data.summary.total} icon={Server} tone="blue" />
            <StatCard label="Operational" value={data.summary.operational} icon={CheckCircle2} tone="green" />
            <StatCard label="Down" value={data.summary.down} icon={AlertTriangle} tone={data.summary.down ? "red" : "slate"} />
            <StatCard label="CPU" value={data.host.cpu == null ? "—" : `${data.host.cpu}%`} icon={Cpu} tone="slate" />
            <StatCard label="RAM" value={data.host.ram == null ? "—" : `${data.host.ram}%`} icon={MemoryStick} tone="slate" />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.services.map((s) => (
              <Glass key={s.name} className="flex items-center justify-between p-4" hover>
                <div>
                  <div className="font-medium" style={{ color: t.ink }}>{s.name}</div>
                  <div className="text-xs capitalize" style={{ color: t.muted }}>{s.category}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full rounded-full opacity-60"
                      style={{ background: s.status === "operational" ? "#16A34A" : s.status === "down" ? "#DC2626" : "#D97706" }} />
                  </span>
                  <Badge tone={statusTone[s.status] || "slate"}>{s.status}</Badge>
                </div>
              </Glass>
            ))}
          </div>

          <p className="mt-4 text-[11px]" style={{ color: t.muted }}>{data.note}</p>
        </>
      )}
    </div>
  );
}
