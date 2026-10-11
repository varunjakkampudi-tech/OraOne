import React, { useState } from "react";
import { MessagesSquare, Search } from "lucide-react";
import {
  PageHeader, Badge, Table, SearchInput, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { timeAgo } from "@/components/admin/format";

const CHANNELS = ["", "chat"];

function dur(s) {
  if (!s) return "—";
  const m = Math.floor(s / 60);
  const r = s % 60;
  return m ? `${m}m ${r}s` : `${r}s`;
}

export default function AdminConversations() {
  const { t } = useAdminTheme();
  const [q, setQ] = useState("");
  const [channel, setChannel] = useState("");
  const { data, loading, error, reload } = useAdminData(
    () => superAdminApi.conversations({ q: q || undefined, channel: channel || undefined, limit: 150 }),
    [q, channel]
  );

  const columns = [
    { key: "customer_name", label: "Customer", render: (r) => (
      <div>
        <div className="font-medium" style={{ color: t.ink }}>{r.customer_name || "Anonymous"}</div>
        <div className="text-xs" style={{ color: t.muted }}>{r.customer_email || r.customer_phone || "—"}</div>
      </div>
    ) },
    { key: "organization_name", label: "Customer org", render: (r) => r.organization_name || "—" },
    { key: "agent_name", label: "Agent", render: (r) => r.agent_name || "—" },
    { key: "channel", label: "Channel", render: (r) => <Badge tone="blue">{r.channel}</Badge> },
    { key: "status", label: "Status", render: (r) => <Badge tone={r.status === "active" ? "green" : r.status === "qualified" ? "purple" : "slate"}>{r.status}</Badge> },
    { key: "duration_seconds", label: "Duration", render: (r) => dur(r.duration_seconds) },
    { key: "started_at", label: "Started", render: (r) => timeAgo(r.started_at) },
  ];

  return (
    <div>
      <PageHeader icon={MessagesSquare} title="Conversations" subtitle="Search every conversation across all tenants."
        actions={<div className="w-64"><SearchInput value={q} onChange={setQ} placeholder="Name, email or phone…" /></div>} />

      <div className="mb-4 flex flex-wrap gap-1.5">
        {CHANNELS.map((c) => (
          <button key={c || "all"} onClick={() => setChannel(c)}
            className="rounded-full px-3 py-1 text-xs font-medium transition"
            style={{
              background: channel === c ? `linear-gradient(135deg,${t.brand},${t.brand2})` : t.glassSolid,
              color: channel === c ? "#fff" : t.sub,
              border: `1px solid ${t.line}`,
            }}>
            {c || "All"}
          </button>
        ))}
      </div>

      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <Table columns={columns} rows={data}
          empty={<EmptyState icon={Search} title="No conversations" hint="Adjust your filters or search." />} />
      )}
    </div>
  );
}
