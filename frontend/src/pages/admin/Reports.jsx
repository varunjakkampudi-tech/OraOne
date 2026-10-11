import React, { useState } from "react";
import { FileBarChart2, Download, RefreshCw, Sparkles, CheckCircle2 } from "lucide-react";
import {
  PageHeader, Glass, Badge, Btn, StatCard, SectionTitle, LoadingState, useAdminTheme,
} from "@/components/admin/adminKit";
import { superAdminApi } from "@/lib/superAdmin";

const PERIODS = [
  { key: "daily", label: "Daily" },
  { key: "weekly", label: "Weekly" },
  { key: "monthly", label: "Monthly" },
  { key: "quarterly", label: "Quarterly" },
];

function MarkdownLite({ text, t }) {
  const fmt = (s) =>
    s.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
      p.startsWith("**") && p.endsWith("**")
        ? <strong key={i} style={{ color: t.ink }}>{p.slice(2, -2)}</strong>
        : <span key={i}>{p}</span>
    );
  return (
    <div className="space-y-1.5 text-sm leading-relaxed" style={{ color: t.sub }}>
      {String(text || "").split("\n").map((ln, i) => {
        const s = ln.trim();
        if (!s) return <div key={i} className="h-1" />;
        if (s.startsWith("## ")) return <h3 key={i} className="pt-1 text-base font-semibold" style={{ color: t.ink }}>{s.slice(3)}</h3>;
        if (s.startsWith("# ")) return <h2 key={i} className="pt-1 text-lg font-semibold" style={{ color: t.ink }}>{s.slice(2)}</h2>;
        if (s.startsWith("- ") || s.startsWith("* "))
          return <div key={i} className="flex gap-2"><span style={{ color: t.brand }}>•</span><span>{fmt(s.slice(2))}</span></div>;
        return <p key={i}>{fmt(s)}</p>;
      })}
    </div>
  );
}

export default function AdminReports() {
  const { t } = useAdminTheme();
  const [period, setPeriod] = useState("weekly");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generate = async (p) => {
    const period_ = p || period;
    setPeriod(period_);
    setLoading(true); setError(null);
    try {
      setData(await superAdminApi.report(period_));
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Report failed");
    } finally {
      setLoading(false);
    }
  };

  const downloadCsv = () => {
    if (!data?.csv) return;
    const blob = new Blob([data.csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `oraone-${data.period}-report.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <PageHeader icon={FileBarChart2} title="AI Report Generator"
        subtitle="Auto-assembled platform reports from live data — daily, weekly, monthly, quarterly"
        actions={data ? (
          <Btn variant="ghost" size="sm" onClick={downloadCsv}><Download className="h-4 w-4" /> CSV</Btn>
        ) : null} />

      <Glass className="mb-5 flex flex-wrap items-center gap-2 p-3">
        {PERIODS.map((p) => (
          <button key={p.key} onClick={() => setPeriod(p.key)}
            className="rounded-full px-3 py-1.5 text-xs font-medium transition"
            style={p.key === period
              ? { background: t.brand, color: "#fff" }
              : { background: t.chipBg, color: t.sub, border: `1px solid ${t.line}` }}>
            {p.label}
          </button>
        ))}
        <div className="ml-auto">
          <Btn size="sm" onClick={() => generate()} disabled={loading}>
            <RefreshCw className="h-4 w-4" /> Generate
          </Btn>
        </div>
      </Glass>

      {loading && <LoadingState label="Assembling report…" />}
      {error && <Glass className="p-4 text-sm" style={{ color: "#DC2626" }}>{error}</Glass>}

      {data && !loading && (
        <div className="space-y-5">
          {data.sections.map((sec) => (
            <div key={sec.title}>
              <SectionTitle>{sec.title}</SectionTitle>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {sec.metrics.map((m) => (
                  <StatCard key={m.label} label={m.label}
                    value={m.value === null || m.value === undefined ? "—" : m.value} />
                ))}
              </div>
            </div>
          ))}

          <Glass className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <SectionTitle>{data.period_label} narrative</SectionTitle>
              <Badge tone={data.generated ? "green" : "slate"}>
                {data.generated ? "AI generated" : "Data summary (offline)"}
              </Badge>
            </div>
            <MarkdownLite text={data.narrative} t={t} />
          </Glass>

          {data.recommendations?.length > 0 && (
            <Glass className="p-5">
              <SectionTitle>Recommended actions</SectionTitle>
              <div className="mt-2 space-y-2">
                {data.recommendations.map((r, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm" style={{ color: t.sub }}>
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" style={{ color: t.brand }} />
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            </Glass>
          )}
        </div>
      )}

      {!data && !loading && !error && (
        <Glass className="flex flex-col items-center gap-3 p-10 text-center">
          <Sparkles className="h-8 w-8" style={{ color: t.brand }} />
          <div className="text-sm" style={{ color: t.sub }}>
            Pick a period and generate a fresh report from live platform data.
          </div>
          <Btn size="sm" onClick={() => generate()}><RefreshCw className="h-4 w-4" /> Generate {PERIODS.find((p) => p.key === period)?.label} report</Btn>
        </Glass>
      )}
    </div>
  );
}
