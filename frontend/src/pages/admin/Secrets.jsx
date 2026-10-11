import React from "react";
import { Lock, CheckCircle2, XCircle, ShieldAlert } from "lucide-react";
import {
  PageHeader, Glass, Badge, LoadingState, ErrorState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";

const catTone = {
  ai: "purple", telephony: "blue", billing: "green", auth: "indigo", cloud: "amber",
  database: "blue", cache: "slate", vector: "purple", storage: "slate", messaging: "blue", platform: "red",
};

export default function AdminSecrets() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.secrets(), []);

  const groups = (data?.items || []).reduce((acc, it) => {
    (acc[it.category] = acc[it.category] || []).push(it);
    return acc;
  }, {});

  return (
    <div>
      <PageHeader icon={Lock} title="Secrets Manager" subtitle="Masked, read-only inventory of platform secrets." />

      <Glass className="mb-5 flex items-start gap-3 p-4">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" style={{ color: "#D97706" }} />
        <p className="text-sm" style={{ color: t.sub }}>
          For security, secret values are never returned to the browser — only set/unset status and a masked tail.
          Rotate secrets through your secrets manager or deploy pipeline.
        </p>
      </Glass>

      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <div className="space-y-6">
          {Object.entries(groups).map(([cat, items]) => (
            <div key={cat}>
              <div className="mb-2 flex items-center gap-2">
                <Badge tone={catTone[cat] || "slate"}>{cat}</Badge>
              </div>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {items.map((s) => (
                  <Glass key={s.key} className="flex items-center justify-between p-3.5">
                    <div className="min-w-0">
                      <div className="truncate font-medium" style={{ color: t.ink }}>{s.label}</div>
                      <div className="mt-0.5 font-mono text-xs" style={{ color: t.muted }}>
                        {s.key} · {s.is_set ? s.masked : "not set"}
                      </div>
                    </div>
                    {s.is_set ? (
                      <CheckCircle2 className="h-5 w-5 shrink-0" style={{ color: "#16A34A" }} />
                    ) : (
                      <XCircle className="h-5 w-5 shrink-0" style={{ color: t.muted }} />
                    )}
                  </Glass>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
