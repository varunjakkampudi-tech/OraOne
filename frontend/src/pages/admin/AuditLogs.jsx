import React, { useState } from "react";
import { FileClock, ScrollText, Search } from "lucide-react";
import {
  PageHeader, Badge, Table, SearchInput, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { timeAgo } from "@/components/admin/format";

const actionTone = { create: "green", update: "blue", delete: "red", read: "slate", install: "purple", run: "indigo" };

export default function AdminAuditLogs({ variant = "audit" }) {
  const { t } = useAdminTheme();
  const [q, setQ] = useState("");
  const { data, loading, error, reload } = useAdminData(
    () => superAdminApi.auditLogs({ q: q || undefined, limit: 300 }),
    [q]
  );

  const isLogs = variant === "logs";
  const columns = [
    { key: "action", label: "Action", render: (r) => <Badge tone={actionTone[r.action] || "slate"}>{r.action}</Badge> },
    { key: "resource", label: "Resource", render: (r) => <span style={{ color: t.ink }}>{r.resource}{r.resource_id ? <span style={{ color: t.muted }}> · {String(r.resource_id).slice(0, 8)}</span> : ""}</span> },
    { key: "organization_name", label: "Customer", render: (r) => r.organization_name || "Platform" },
    { key: "actor_email", label: "Actor", render: (r) => r.actor_email || "system" },
    { key: "created_at", label: "When", render: (r) => timeAgo(r.created_at) },
  ];

  return (
    <div>
      <PageHeader
        icon={isLogs ? ScrollText : FileClock}
        title={isLogs ? "Logs" : "Audit Logs"}
        subtitle={isLogs ? "Central request & system event log across the platform." : "Immutable, cross-tenant audit trail of every privileged action."}
        actions={<div className="w-64"><SearchInput value={q} onChange={setQ} placeholder="Filter action / resource…" /></div>}
      />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <Table columns={columns} rows={data}
          empty={<EmptyState icon={Search} title="No log entries" hint="Nothing matches your filter yet." />} />
      )}
    </div>
  );
}
