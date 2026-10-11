import React from "react";
import { useLocation } from "react-router-dom";
import {
  LifeBuoy, Database, ListOrdered, BellRing, Brain, Save, ShieldAlert,
  Settings, Code2, Sparkles, CheckCircle2,
} from "lucide-react";
import {
  PageHeader, Glass, Badge, SectionTitle, Table, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { timeAgo } from "@/components/admin/format";

const statusTone = { operational: "green", degraded: "amber", down: "red" };
const sevTone = { critical: "red", high: "red", medium: "amber", low: "blue", info: "slate" };

// Descriptor per module route.
const MODULES = {
  support: {
    icon: LifeBuoy, title: "Support Desk", subtitle: "Customer tickets and escalations.",
    capabilities: ["Unified ticket inbox", "SLA timers & priority", "Impersonate (audited) sessions", "Macro replies & CSAT"],
  },
  databases: {
    icon: Database, title: "Databases", subtitle: "Primary datastores and their health.",
    source: "infra", categories: ["database", "cache", "vector", "storage"],
  },
  queues: {
    icon: ListOrdered, title: "Queues & Workers", subtitle: "Background jobs and message queues.",
    source: "infra", categories: ["messaging", "queue", "worker"],
  },
  alerts: {
    icon: BellRing, title: "Alerts", subtitle: "Active platform alerts and incidents.",
    source: "alerts",
  },
  "ai-operations": {
    icon: Brain, title: "AI Operations", subtitle: "LLM providers, model routing and spend.",
    capabilities: ["Model routing & fallbacks", "Per-provider latency & spend", "Token budgets & rate limits", "Prompt & eval registry"],
  },
  backups: {
    icon: Save, title: "Backups", subtitle: "Automated backup status and restore points.",
    capabilities: ["Daily snapshots & retention", "Point-in-time recovery", "Restore drills & verification", "Cross-region replication"],
  },
  "disaster-recovery": {
    icon: ShieldAlert, title: "Disaster Recovery", subtitle: "Failover readiness and runbooks.",
    capabilities: ["RTO / RPO targets", "Failover runbooks", "Region health & DNS failover", "DR drill scheduling"],
  },
  settings: {
    icon: Settings, title: "Platform Settings", subtitle: "Global configuration for the platform.",
    capabilities: ["Branding & domains", "Default plan limits", "Email & notification config", "Compliance & data residency"],
  },
  developer: {
    icon: Code2, title: "Developer Tools", subtitle: "API explorer, webhooks and diagnostics.",
    capabilities: ["API explorer & playground", "Webhook delivery logs", "Sandbox tokens", "System diagnostics"],
  },
};

function Roadmap({ desc }) {
  const { t } = useAdminTheme();
  const Icon = desc.icon;
  return (
    <Glass className="p-8">
      <div className="mx-auto max-w-lg text-center">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl"
          style={{ background: `linear-gradient(135deg,${t.brand}1A,${t.brand2}1A)`, color: t.brand }}>
          <Icon className="h-7 w-7" />
        </div>
        <div className="mt-4 flex items-center justify-center gap-2">
          <h3 className="text-lg font-semibold" style={{ color: t.ink }}>{desc.title}</h3>
          <Badge tone="purple"><Sparkles className="h-3.5 w-3.5" /> Coming online</Badge>
        </div>
        <p className="mt-1 text-sm" style={{ color: t.sub }}>
          This module is wired into the control center and will light up as the backend service is connected.
        </p>
      </div>
      <div className="mx-auto mt-6 grid max-w-xl grid-cols-1 gap-2 sm:grid-cols-2">
        {desc.capabilities.map((c) => (
          <div key={c} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm" style={{ background: t.hover, color: t.sub }}>
            <CheckCircle2 className="h-4 w-4 shrink-0" style={{ color: t.brand }} />
            {c}
          </div>
        ))}
      </div>
    </Glass>
  );
}

function InfraModule({ desc }) {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.infrastructure(), []);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const services = (data.services || []).filter((s) => desc.categories.includes(s.category));
  if (services.length === 0) return <EmptyState icon={desc.icon} title={`No ${desc.title.toLowerCase()} reporting`} />;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {services.map((s) => (
        <Glass key={s.name} className="flex items-center justify-between p-4" hover>
          <div>
            <div className="font-medium" style={{ color: t.ink }}>{s.name}</div>
            <div className="text-xs capitalize" style={{ color: t.muted }}>{s.category}{s.latency_ms != null ? ` · ${s.latency_ms}ms` : ""}</div>
          </div>
          <Badge tone={statusTone[s.status] || "slate"}>{s.status}</Badge>
        </Glass>
      ))}
    </div>
  );
}

function AlertsModule({ desc }) {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.security(), []);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const cols = [
    { key: "severity", label: "Severity", render: (r) => <Badge tone={sevTone[r.severity] || "slate"}>{r.severity}</Badge> },
    { key: "title", label: "Alert", render: (r) => r.title },
    { key: "event_type", label: "Type", render: (r) => (r.event_type || "").replace(/_/g, " ") },
    { key: "organization_name", label: "Customer", render: (r) => r.organization_name || "Platform" },
    { key: "created_at", label: "When", render: (r) => timeAgo(r.created_at) },
  ];
  return <Table columns={cols} rows={data.recent || []}
    empty={<EmptyState icon={BellRing} title="No active alerts" hint="All clear — nothing requires attention." />} />;
}

export default function ModulePage({ moduleKey }) {
  const location = useLocation();
  const key = moduleKey || location.pathname.split("/").pop();
  const desc = MODULES[key];
  if (!desc) return <div><PageHeader title="Not found" subtitle={key} /><EmptyState title="Unknown module" /></div>;

  return (
    <div>
      <PageHeader icon={desc.icon} title={desc.title} subtitle={desc.subtitle} />
      {desc.source === "infra" ? <InfraModule desc={desc} />
        : desc.source === "alerts" ? <AlertsModule desc={desc} />
        : <Roadmap desc={desc} />}
    </div>
  );
}
