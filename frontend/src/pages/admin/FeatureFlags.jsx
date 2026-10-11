import React, { useState } from "react";
import { Flag } from "lucide-react";
import { toast } from "sonner";
import {
  PageHeader, Glass, Toggle, Badge, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { formatApiError } from "@/lib/api";

export default function AdminFeatureFlags() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload, setData } = useAdminData(() => superAdminApi.featureFlags(), []);
  const [busy, setBusy] = useState("");

  async function toggle(flag) {
    setBusy(flag.key);
    const next = !flag.enabled;
    // Optimistic update.
    setData((prev) => (prev || []).map((f) => (f.key === flag.key ? { ...f, enabled: next } : f)));
    try {
      await superAdminApi.setFeatureFlag(flag.key, { enabled: next });
      toast.success(`${flag.label} ${next ? "enabled" : "disabled"} globally`);
    } catch (e) {
      setData((prev) => (prev || []).map((f) => (f.key === flag.key ? { ...f, enabled: flag.enabled } : f)));
      toast.error(formatApiError(e?.response?.data?.detail) || "Failed to update flag.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div>
      <PageHeader icon={Flag} title="Feature Flags" subtitle="Toggle platform capabilities on or off globally." />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (data || []).length === 0 ? (
        <EmptyState icon={Flag} title="No feature flags" />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {data.map((flag) => (
            <Glass key={flag.key} className="flex items-center justify-between p-4">
              <div className="min-w-0 pr-4">
                <div className="flex items-center gap-2">
                  <span className="font-medium" style={{ color: t.ink }}>{flag.label}</span>
                  <Badge tone={flag.enabled ? "green" : "slate"}>{flag.enabled ? "On" : "Off"}</Badge>
                </div>
                <p className="mt-0.5 text-xs" style={{ color: t.sub }}>{flag.description}</p>
                <p className="mt-1 text-[11px]" style={{ color: t.muted }}>{flag.environment} · {flag.rollout_percentage}% rollout</p>
              </div>
              <Toggle checked={flag.enabled} onChange={() => toggle(flag)} disabled={busy === flag.key} />
            </Glass>
          ))}
        </div>
      )}
    </div>
  );
}
