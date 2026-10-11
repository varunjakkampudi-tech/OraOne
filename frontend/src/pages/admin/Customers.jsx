import React, { useState } from "react";
import { Users, X, Search, Building2, Bot, MessagesSquare, FileText, KeyRound, Plug } from "lucide-react";
import {
  PageHeader, Glass, Badge, Btn, Table, SearchInput, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtDate, fmtNum, timeAgo } from "@/components/admin/format";

const planTone = { free: "slate", starter: "blue", growth: "indigo", business: "indigo", enterprise: "purple" };

function CustomerDrawer({ id, onClose }) {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.customer(id), [id]);
  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative h-full w-full max-w-lg overflow-y-auto p-6 scrollbar-thin"
        onClick={(e) => e.stopPropagation()}
        style={{ background: t.glassSolid, borderLeft: `1px solid ${t.line}` }}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold" style={{ color: t.ink }}>Customer detail</h2>
          <button onClick={onClose} aria-label="Close panel" style={{ color: t.sub }}><X className="h-5 w-5" /></button>
        </div>
        {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : !data ? <EmptyState /> : (
          <div className="space-y-5">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-semibold" style={{ color: t.ink }}>{data.name}</h3>
                <Badge tone={planTone[data.plan] || "slate"}>{data.plan}</Badge>
              </div>
              <p className="text-sm" style={{ color: t.sub }}>{data.slug} · joined {fmtDate(data.created_at)}</p>
              {data.owner ? <p className="mt-1 text-sm" style={{ color: t.sub }}>Owner: {data.owner.email}{data.owner.last_login_at ? ` · last login ${timeAgo(data.owner.last_login_at)}` : ""}</p> : null}
            </div>

            <div className="grid grid-cols-3 gap-2">
              {[
                ["Agents", data.counts.agents, Bot],
                ["Convos", data.counts.conversations, MessagesSquare],
                ["Leads", data.counts.leads, Users],
                ["Docs", data.counts.documents, FileText],
                ["API keys", data.counts.api_keys, KeyRound],
                ["Integrations", data.counts.integrations, Plug],
              ].map(([label, val, Icon]) => (
                <Glass key={label} className="p-3">
                  <Icon className="h-4 w-4" style={{ color: t.brand }} />
                  <div className="mt-1.5 text-lg font-semibold" style={{ color: t.ink }}>{fmtNum(val)}</div>
                  <div className="text-[11px]" style={{ color: t.muted }}>{label}</div>
                </Glass>
              ))}
            </div>

            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: t.sub }}>Members ({data.members.length})</h4>
              <div className="space-y-1">
                {data.members.map((m, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg px-3 py-2" style={{ background: t.hover }}>
                    <span className="truncate text-sm" style={{ color: t.ink }}>{m.full_name || m.email}</span>
                    <Badge tone={m.role === "owner" ? "purple" : "slate"}>{m.role}</Badge>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide" style={{ color: t.sub }}>Recent conversations</h4>
              {data.recent_conversations.length === 0 ? <p className="text-sm" style={{ color: t.muted }}>None.</p> : (
                <div className="space-y-1">
                  {data.recent_conversations.map((c) => (
                    <div key={c.id} className="flex items-center justify-between rounded-lg px-3 py-2" style={{ background: t.hover }}>
                      <span className="truncate text-sm" style={{ color: t.ink }}>{c.customer_name || "Anonymous"} · {c.channel}</span>
                      <span className="text-xs" style={{ color: t.muted }}>{timeAgo(c.started_at)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-xl p-3 text-xs" style={{ background: t.chipBg, color: t.sub }}>
              Operator actions (impersonate, suspend, reset keys) are gated behind step-up approval and are intentionally
              not one-click in this view.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminCustomers() {
  const { t } = useAdminTheme();
  const [q, setQ] = useState("");
  const [active, setActive] = useState("");
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.customers({ q: q || undefined, limit: 100 }), [q]);

  const columns = [
    { key: "name", label: "Customer", render: (r) => (
      <div className="flex items-center gap-2">
        <div className="grid h-7 w-7 place-items-center rounded-lg text-[11px] font-semibold text-white" style={{ background: `linear-gradient(135deg,${t.brand},${t.brand2})` }}>{(r.name || "?").slice(0, 1).toUpperCase()}</div>
        <div>
          <div className="font-medium" style={{ color: t.ink }}>{r.name}</div>
          <div className="text-xs" style={{ color: t.muted }}>{r.owner_email || r.slug}</div>
        </div>
      </div>
    ) },
    { key: "plan", label: "Plan", render: (r) => <Badge tone={planTone[r.plan] || "slate"}>{r.plan}</Badge> },
    { key: "members", label: "Members", render: (r) => fmtNum(r.members) },
    { key: "agents", label: "Agents", render: (r) => fmtNum(r.agents) },
    { key: "conversations", label: "Convos", render: (r) => fmtNum(r.conversations) },
    { key: "subscription_status", label: "Sub", render: (r) => r.subscription_status ? <Badge tone={r.subscription_status === "active" ? "green" : "amber"}>{r.subscription_status}</Badge> : "—" },
    { key: "created_at", label: "Joined", render: (r) => fmtDate(r.created_at) },
  ];

  return (
    <div>
      <PageHeader icon={Users} title="Customers" subtitle="Every organization on the platform."
        actions={<div className="w-64"><SearchInput value={q} onChange={setQ} placeholder="Search customers…" /></div>} />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <>
          <div className="mb-3 text-sm" style={{ color: t.sub }}>{fmtNum(data?.total)} customers</div>
          <Table columns={columns} rows={data?.items} onRowClick={(r) => setActive(r.id)}
            empty={<EmptyState icon={Search} title="No customers found" hint="Try a different search term." />} />
        </>
      )}
      {active ? <CustomerDrawer id={active} onClose={() => setActive("")} /> : null}
    </div>
  );
}
