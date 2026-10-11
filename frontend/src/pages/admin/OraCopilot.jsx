import React, { useState } from "react";
import { Wand2, Sparkles, ArrowRight, Send, Lightbulb } from "lucide-react";
import {
  PageHeader, Glass, Badge, Btn, SectionTitle, LoadingState, useAdminTheme,
} from "@/components/admin/adminKit";
import { superAdminApi } from "@/lib/superAdmin";

const SUGGESTIONS = [
  "Why did revenue change this month?",
  "Show my largest customers",
  "What is my gross margin and burn?",
  "Where can I cut AI cost?",
  "How healthy is the platform right now?",
  "Generate a weekly summary",
];

// Minimal markdown: headings (#/##), bullets (-/*), bold (**x**).
function MarkdownLite({ text, t }) {
  const lines = String(text || "").split("\n");
  const fmt = (s) =>
    s.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith("**") && part.endsWith("**")
        ? <strong key={i} style={{ color: t.ink }}>{part.slice(2, -2)}</strong>
        : <span key={i}>{part}</span>
    );
  return (
    <div className="space-y-1.5 text-sm leading-relaxed" style={{ color: t.sub }}>
      {lines.map((ln, i) => {
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

export default function AdminOraCopilot() {
  const { t } = useAdminTheme();
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState(null);
  const [error, setError] = useState(null);

  const ask = async (question) => {
    const text = (question ?? q).trim();
    if (!text) return;
    setQ(text);
    setLoading(true); setError(null);
    try {
      const res = await superAdminApi.copilot(text);
      setResp(res);
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Copilot failed");
    } finally {
      setLoading(false);
    }
  };

  const result = resp?.result;

  return (
    <div>
      <PageHeader icon={Wand2} title="Ora Copilot"
        subtitle="Ask the platform anything — grounded in live cross-tenant data" />

      <Glass className="mb-5 p-3">
        <div className="flex items-center gap-2">
          <Sparkles className="ml-1 h-4 w-4 shrink-0" style={{ color: t.brand }} />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="Ask about revenue, costs, customers, health…"
            className="w-full bg-transparent py-1.5 text-sm outline-none"
            style={{ color: t.ink }}
          />
          <Btn size="sm" onClick={() => ask()} disabled={loading || !q.trim()}>
            <Send className="h-4 w-4" /> Ask
          </Btn>
        </div>
      </Glass>

      {!resp && !loading && (
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => ask(s)}
              className="rounded-full px-3 py-1.5 text-xs transition hover:opacity-80"
              style={{ background: t.chipBg, color: t.sub, border: `1px solid ${t.line}` }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {loading && <LoadingState label="Thinking…" />}
      {error && <Glass className="p-4 text-sm" style={{ color: "#DC2626" }}>{error}</Glass>}

      {result && !loading && (
        <div className="space-y-4">
          <Glass className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <SectionTitle>Answer</SectionTitle>
              <Badge tone={resp.generated ? "green" : "slate"}>
                {resp.generated ? "AI generated" : "Data summary (offline)"}
              </Badge>
            </div>
            <MarkdownLite text={result.answer} t={t} />
          </Glass>

          {Array.isArray(result.highlights) && result.highlights.length > 0 && (
            <Glass className="p-5">
              <SectionTitle>Highlights</SectionTitle>
              <div className="mt-2 space-y-2">
                {result.highlights.map((h, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm" style={{ color: t.sub }}>
                    <Lightbulb className="mt-0.5 h-4 w-4 shrink-0" style={{ color: t.brand }} />
                    <span>{h}</span>
                  </div>
                ))}
              </div>
            </Glass>
          )}

          {Array.isArray(result.follow_ups) && result.follow_ups.length > 0 && (
            <div>
              <SectionTitle>Follow up</SectionTitle>
              <div className="mt-2 flex flex-wrap gap-2">
                {result.follow_ups.map((f, i) => (
                  <button key={i} onClick={() => ask(f)}
                    className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs transition hover:opacity-80"
                    style={{ background: t.chipBg, color: t.sub, border: `1px solid ${t.line}` }}>
                    {f} <ArrowRight className="h-3 w-3" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
