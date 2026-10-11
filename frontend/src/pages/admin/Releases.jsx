import React from "react";
import { GitBranch, Rocket, CheckCircle2, XCircle, RotateCcw, Clock } from "lucide-react";
import {
  PageHeader, Glass, Badge, Table, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { timeAgo } from "@/components/admin/format";

const statusTone = { succeeded: "green", failed: "red", rolled_back: "amber", in_progress: "blue", pending: "slate" };
const statusIcon = { succeeded: CheckCircle2, failed: XCircle, rolled_back: RotateCcw, in_progress: Clock, pending: Clock };

export default function AdminReleases({ variant = "releases" }) {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.releases(), []);
  const isDeploy = variant === "deployments";

  const cols = [
    { key: "version", label: "Version", render: (r) => <span className="font-mono font-medium" style={{ color: t.ink }}>{r.version}</span> },
    { key: "environment", label: "Environment", render: (r) => <Badge tone="indigo">{r.environment}</Badge> },
    { key: "status", label: "Status", render: (r) => {
      const Icon = statusIcon[r.status] || Clock;
      return <Badge tone={statusTone[r.status] || "slate"}><Icon className="h-3.5 w-3.5" />{r.status.replace(/_/g, " ")}</Badge>;
    } },
    { key: "notes", label: "Notes", render: (r) => <span style={{ color: t.sub }}>{r.notes || "—"}</span> },
    { key: "created_at", label: "When", render: (r) => timeAgo(r.created_at) },
  ];

  return (
    <div>
      <PageHeader icon={isDeploy ? Rocket : GitBranch} title={isDeploy ? "Deployments" : "Release Center"}
        subtitle={isDeploy ? "Deployment history across environments." : "Releases, rollbacks and CI/CD status."} />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <Table columns={cols} rows={data}
          empty={<EmptyState icon={GitBranch} title="No deployments recorded" hint="Release records will appear here as the pipeline runs." />} />
      )}
    </div>
  );
}
