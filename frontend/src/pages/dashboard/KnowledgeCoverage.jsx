import React, { useEffect, useState } from "react";
import { BookOpen, Loader2, RefreshCw, AlertTriangle, CheckCircle2, FileWarning } from "lucide-react";
import {
  PageHeader,
  Card,
  Badge,
  SectionTitle,
  StatCard,
  PrimaryButton,
  GhostButton,
  EmptyState,
  INK,
  SUB,
  LINE,
} from "@/components/dashboard/kit";
import { workspaceIntelApi } from "@/lib/workspaceIntel";
import { formatApiError } from "@/lib/api";

const SEV = { high: "red", medium: "amber", low: "slate" };

function Donut({ value, label }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const off = c - (Math.max(0, Math.min(100, value)) / 100) * c;
  const col = value >= 80 ? "#16A34A" : value >= 50 ? "#2563EB" : "#DC2626";
  return (
    <div className="flex flex-col items-center">
      <div className="relative grid place-items-center" style={{ width: 140, height: 140 }}>
        <svg width="140" height="140" className="-rotate-90">
          <circle cx="70" cy="70" r={r} fill="none" stroke={LINE} strokeWidth="12" />
          <circle cx="70" cy="70" r={r} fill="none" stroke={col} strokeWidth="12"
            strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}
            style={{ transition: "stroke-dashoffset .8s ease" }} />
        </svg>
        <div className="absolute text-2xl font-bold" style={{ color: INK }}>{Math.round(value)}%</div>
      </div>
      <div className="mt-2 text-sm font-medium" style={{ color: SUB }}>{label}</div>
    </div>
  );
}

export default function KnowledgeCoverage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    workspaceIntelApi
      .knowledgeCoverage()
      .then(setData)
      .catch((e) => setError(formatApiError(e?.response?.data?.detail) || "Failed to load coverage"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);
  const t = data?.totals || {};

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        icon={BookOpen}
        eyebrow="Workspace Intelligence"
        title="Knowledge Coverage Analyzer"
        subtitle="See how well your knowledge base grounds your AI — gaps, duplicates and freshness."
        actions={
          <GhostButton onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
          </GhostButton>
        }
      />

      {loading ? (
        <div className="grid place-items-center py-24" style={{ color: SUB }}>
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : error ? (
        <Card className="p-8">
          <EmptyState icon={AlertTriangle} title="Couldn't analyze knowledge" hint={error}
            action={<PrimaryButton onClick={load}>Try again</PrimaryButton>} />
        </Card>
      ) : !data ? null : (
        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex flex-wrap items-center justify-around gap-6">
              <Donut value={data.coverage} label="Coverage" />
              <Donut value={data.freshness} label="Freshness" />
              <Donut value={data.grounded_pct} label="Answers grounded" />
            </div>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={BookOpen} label="Documents" value={t.documents ?? 0} />
            <StatCard icon={CheckCircle2} label="Processed" value={t.processed ?? 0} />
            <StatCard icon={FileWarning} label="Failed" value={t.failed ?? 0} tone="#DC2626" bg="#FEF2F2" />
            <StatCard icon={FileWarning} label="Duplicates" value={t.duplicates ?? 0} tone="#D97706" bg="#FFFBEB" />
          </div>

          <Card className="p-6">
            <SectionTitle title="Findings" subtitle="What to fix to improve grounding" />
            <div className="mt-4 space-y-3">
              {(data.findings || []).map((f, i) => (
                <div key={i} className="flex items-start gap-3 rounded-xl border p-4" style={{ borderColor: LINE }}>
                  {f.type === "ok" ? (
                    <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" style={{ color: "#16A34A" }} />
                  ) : (
                    <FileWarning className="mt-0.5 h-5 w-5 shrink-0" style={{ color: "#D97706" }} />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold" style={{ color: INK }}>{f.label}</span>
                      <Badge tone={SEV[f.severity] || "slate"}>{f.severity}</Badge>
                    </div>
                    <p className="mt-0.5 text-sm" style={{ color: SUB }}>{f.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
