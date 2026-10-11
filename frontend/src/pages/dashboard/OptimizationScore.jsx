import React, { useEffect, useState } from "react";
import { Gauge, Loader2, RefreshCw, AlertTriangle, CheckCircle2, ArrowRight } from "lucide-react";
import {
  PageHeader,
  Card,
  Badge,
  SectionTitle,
  PrimaryButton,
  GhostButton,
  EmptyState,
  INK,
  SUB,
  LINE,
  BRAND,
} from "@/components/dashboard/kit";
import { workspaceIntelApi } from "@/lib/workspaceIntel";
import { formatApiError } from "@/lib/api";

const SEV = {
  high: { tone: "red", label: "High" },
  medium: { tone: "amber", label: "Medium" },
  low: { tone: "slate", label: "Low" },
};

function scoreColor(v) {
  if (v >= 85) return "#16A34A";
  if (v >= 70) return "#2563EB";
  if (v >= 55) return "#D97706";
  return "#DC2626";
}

function ScoreRing({ value, grade }) {
  const r = 78;
  const c = 2 * Math.PI * r;
  const off = c - (Math.max(0, Math.min(100, value)) / 100) * c;
  const col = scoreColor(value);
  return (
    <div className="relative grid place-items-center" style={{ width: 200, height: 200 }}>
      <svg width="200" height="200" className="-rotate-90">
        <circle cx="100" cy="100" r={r} fill="none" stroke={LINE} strokeWidth="14" />
        <circle
          cx="100" cy="100" r={r} fill="none" stroke={col} strokeWidth="14"
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset .8s ease" }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-5xl font-bold" style={{ color: INK }}>{Math.round(value)}</div>
        <div className="mt-1 text-sm font-semibold" style={{ color: col }}>Grade {grade}</div>
      </div>
    </div>
  );
}

function CategoryBar({ label, score, weight }) {
  const col = scoreColor(score);
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium" style={{ color: INK }}>{label}</span>
        <span style={{ color: SUB }}>{Math.round(score)} · {weight}%</span>
      </div>
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full" style={{ background: LINE }}>
        <div className="h-full rounded-full" style={{ width: `${score}%`, background: col, transition: "width .6s ease" }} />
      </div>
    </div>
  );
}

export default function OptimizationScore() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    workspaceIntelApi
      .optimizationScore()
      .then(setData)
      .catch((e) => setError(formatApiError(e?.response?.data?.detail) || "Failed to load score"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        icon={Gauge}
        eyebrow="Workspace Intelligence"
        title="AI Optimization Score"
        subtitle="A live health score for your workspace with one-click ways to improve."
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
          <EmptyState icon={AlertTriangle} title="Couldn't load your score" hint={error}
            action={<PrimaryButton onClick={load}>Try again</PrimaryButton>} />
        </Card>
      ) : !data ? null : (
        <div className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
            <Card className="flex flex-col items-center justify-center p-6">
              <ScoreRing value={data.overall} grade={data.grade} />
              <p className="mt-4 text-center text-sm" style={{ color: SUB }}>
                Weighted across {data.categories?.length || 0} signals
              </p>
            </Card>
            <Card className="p-6">
              <SectionTitle title="Category breakdown" subtitle="Each signal and its weight" />
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {(data.categories || []).map((c) => (
                  <CategoryBar key={c.key} label={c.label} score={c.score} weight={c.weight} />
                ))}
              </div>
            </Card>
          </div>

          <Card className="p-6">
            <SectionTitle title="Recommendations" subtitle="Prioritized actions to raise your score" />
            <div className="mt-4 space-y-3">
              {(data.recommendations || []).map((r, i) => {
                const sev = SEV[r.severity] || SEV.low;
                const ok = r.area === "General";
                return (
                  <div key={i} className="flex items-start gap-3 rounded-xl border p-4" style={{ borderColor: LINE }}>
                    {ok ? (
                      <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" style={{ color: "#16A34A" }} />
                    ) : (
                      <ArrowRight className="mt-0.5 h-5 w-5 shrink-0" style={{ color: BRAND }} />
                    )}
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold" style={{ color: INK }}>{r.title}</span>
                        <Badge tone={sev.tone}>{r.area}</Badge>
                      </div>
                      <p className="mt-0.5 text-sm" style={{ color: SUB }}>{r.detail}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
