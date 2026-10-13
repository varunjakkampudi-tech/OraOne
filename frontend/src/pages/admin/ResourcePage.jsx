import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  Boxes,
  FolderKanban,
  UserPlus,
  BookOpen,
  Workflow,
  Plug,
  KeyRound,
  Radio,
  Users,
  Search,
} from "lucide-react";
import {
  PageHeader,
  Glass,
  Badge,
  Table,
  SearchInput,
  LoadingState,
  ErrorState,
  EmptyState,
  useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { timeAgo } from "@/components/admin/format";

const statusTone = (s) => {
  const v = String(s || "").toLowerCase();
  if (
    ["active", "connected", "published", "live", "ready", "completed"].includes(
      v,
    )
  )
    return "green";
  if (["draft", "inactive", "archived", "disabled"].includes(v)) return "slate";
  if (["error", "failed", "disconnected", "suspended"].includes(v))
    return "red";
  if (["pending", "processing", "training"].includes(v)) return "amber";
  return "blue";
};

// kind -> page descriptor
export const RESOURCE_KINDS = {
  agents: {
    icon: Boxes,
    title: "Agents",
    subtitle: "Every AI agent deployed across all tenants.",
    columns: (t) => [
      nameCol(t),
      {
        key: "type",
        label: "Type",
        render: (r) => <Badge tone="indigo">{r.type}</Badge>,
      },
      orgCol(t),
      statusCol(),
      createdCol(),
    ],
  },
  workspaces: {
    icon: FolderKanban,
    title: "Workspaces",
    subtitle: "Customer projects and workspaces.",
    columns: (t) => [nameCol(t), orgCol(t), statusCol(), createdCol()],
  },
  leads: {
    icon: UserPlus,
    title: "Leads",
    subtitle: "Captured leads across the entire platform.",
    columns: (t) => [
      nameCol(t),
      { key: "email", label: "Email", render: (r) => r.email || "—" },
      orgCol(t),
      {
        key: "score",
        label: "Score",
        render: (r) => (r.score == null ? "—" : r.score),
      },
      statusCol(),
      createdCol(),
    ],
  },
  knowledge: {
    icon: BookOpen,
    title: "Knowledge Bases",
    subtitle: "All knowledge bases across tenants.",
    columns: (t) => [nameCol(t), orgCol(t), statusCol(), createdCol()],
  },
  workflows: {
    icon: Workflow,
    title: "Workflows",
    subtitle: "Automation workflows across tenants.",
    columns: (t) => [nameCol(t), orgCol(t), statusCol(), createdCol()],
  },
  integrations: {
    icon: Plug,
    title: "Integrations",
    subtitle: "Third-party integrations connected by customers.",
    columns: (t) => [
      nameCol(t, "Provider"),
      {
        key: "type",
        label: "Type",
        render: (r) => <Badge tone="indigo">{r.type}</Badge>,
      },
      orgCol(t),
      statusCol(),
      createdCol(),
    ],
  },
  api_keys: {
    icon: KeyRound,
    title: "API Keys",
    subtitle: "Issued API keys across all customers.",
    columns: (t) => [
      nameCol(t),
      {
        key: "prefix",
        label: "Prefix",
        render: (r) => (
          <span className="font-mono text-xs" style={{ color: t.muted }}>
            {r.prefix}…
          </span>
        ),
      },
      orgCol(t),
      {
        key: "last_used_at",
        label: "Last used",
        render: (r) => (r.last_used_at ? timeAgo(r.last_used_at) : "never"),
      },
      createdCol(),
    ],
  },
  channels: {
    icon: Radio,
    title: "Channels",
    subtitle: "Deployed widgets and channels.",
    columns: (t) => [
      nameCol(t),
      {
        key: "type",
        label: "Type",
        render: (r) => <Badge tone="indigo">{r.type}</Badge>,
      },
      orgCol(t),
      statusCol(),
      createdCol(),
    ],
  },
  users: {
    icon: Users,
    title: "Users",
    subtitle: "Every user account across the platform.",
    columns: (t) => [
      nameCol(t),
      { key: "email", label: "Email", render: (r) => r.email },
      statusCol(),
      {
        key: "last_login_at",
        label: "Last login",
        render: (r) => (r.last_login_at ? timeAgo(r.last_login_at) : "never"),
      },
      createdCol(),
    ],
  },
};

function nameCol(t, label = "Name") {
  return {
    key: "name",
    label,
    render: (r) => (
      <span className="font-medium" style={{ color: t.ink }}>
        {r.name || "—"}
      </span>
    ),
  };
}
function orgCol(t) {
  return {
    key: "organization_name",
    label: "Customer",
    render: (r) => (
      <span style={{ color: t.sub }}>{r.organization_name || "—"}</span>
    ),
  };
}
function statusCol() {
  return {
    key: "status",
    label: "Status",
    render: (r) =>
      r.status ? <Badge tone={statusTone(r.status)}>{r.status}</Badge> : "—",
  };
}
function createdCol() {
  return {
    key: "created_at",
    label: "Created",
    render: (r) => (r.created_at ? timeAgo(r.created_at) : "—"),
  };
}

export default function ResourcePage({ kind, initialQuery = "" }) {
  const { t } = useAdminTheme();
  const location = useLocation();
  // Resolve kind from prop or from the trailing route segment.
  const resolvedKind =
    kind || location.pathname.split("/").pop().replace(/-/g, "_");
  const desc = RESOURCE_KINDS[resolvedKind] || RESOURCE_KINDS.agents;
  const [q, setQ] = useState(initialQuery);

  useEffect(() => {
    setQ(initialQuery);
  }, [initialQuery]);

  const { data, loading, error, reload } = useAdminData(
    () =>
      superAdminApi.resources(resolvedKind, { q: q || undefined, limit: 200 }),
    [resolvedKind, q],
  );

  const Icon = desc.icon;
  return (
    <div className="space-y-1">
      <PageHeader icon={Icon} title={desc.title} subtitle={desc.subtitle} />
      <Glass className="overflow-hidden">
        <div
          className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3.5 sm:px-5"
          style={{ borderColor: t.line, background: t.tableHead }}
        >
          <div>
            <div
              className="text-xs font-semibold uppercase tracking-[0.14em]"
              style={{ color: t.sub }}
            >
              Live records
            </div>
            <div className="mt-1 text-xs" style={{ color: t.muted }}>
              {data?.total ?? data?.items?.length ?? 0}{" "}
              {desc.title.toLowerCase()} returned
            </div>
          </div>
          <div className="w-full sm:w-64">
            <SearchInput
              value={q}
              onChange={setQ}
              placeholder={`Search ${desc.title.toLowerCase()}…`}
            />
          </div>
        </div>
        <div className="p-4 sm:p-5">
          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} onRetry={reload} />
          ) : (
            <Table
              contained
              columns={desc.columns(t)}
              rows={data?.items || []}
              empty={
                <EmptyState
                  icon={Search}
                  title={`No ${desc.title.toLowerCase()}`}
                  hint="Nothing matches yet."
                />
              }
            />
          )}
        </div>
      </Glass>
    </div>
  );
}
