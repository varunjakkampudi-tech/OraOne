import React, { useEffect, useMemo, useState } from "react";
import { Sparkles, Loader2, Wand2, ArrowRight } from "lucide-react";
import {
  PageHeader,
  Card,
  Badge,
  PrimaryButton,
  EmptyState,
  INK,
  SUB,
  LINE,
} from "@/components/dashboard/kit";
import { assistantsApi } from "@/lib/assistants";
import { formatApiError } from "@/lib/api";

// Per-assistant input fields (keys match the backend builders).
const FIELDS = {
  meeting: [
    { key: "transcript", label: "Transcript", type: "textarea", required: true, placeholder: "Paste the call or meeting transcript…" },
    { key: "context", label: "Context", type: "text", placeholder: "e.g. Sales call with Acme Inc." },
  ],
  qa: [
    { key: "transcript", label: "Transcript", type: "textarea", required: true, placeholder: "Paste the conversation to review…" },
    { key: "goal", label: "Call goal", type: "text", placeholder: "e.g. resolve a billing issue" },
  ],
  forecast: [
    { key: "metric", label: "Metric", type: "text", placeholder: "e.g. weekly interactions" },
    { key: "history", label: "Recent values", type: "text", required: true, placeholder: "e.g. 820, 905, 980, 1040, 1120" },
    { key: "horizon", label: "Horizon", type: "text", placeholder: "e.g. next 4 weeks" },
  ],
  personalize: [
    { key: "customer", label: "Customer", type: "text", required: true, placeholder: "e.g. Priya, returning customer" },
    { key: "context", label: "Context / history", type: "textarea", placeholder: "Recent activity, preferences, past purchases…" },
    { key: "channel", label: "Channel", type: "text", placeholder: "email / chat" },
    { key: "goal", label: "Goal", type: "text", placeholder: "e.g. upsell premium plan" },
    { key: "tone", label: "Tone", type: "text", placeholder: "warm and professional" },
  ],
  experiment: [
    { key: "goal", label: "Goal / metric", type: "text", required: true, placeholder: "e.g. email open rate" },
    { key: "variant_a", label: "Variant A", type: "textarea", required: true, placeholder: "First option…" },
    { key: "variant_b", label: "Variant B", type: "textarea", required: true, placeholder: "Second option…" },
  ],
  copilot: [
    { key: "question", label: "Your question", type: "textarea", required: true, placeholder: "Ask anything about OraOne…" },
  ],
};

function ResultView({ result }) {
  const entries = Object.entries(result || {});
  if (entries.length === 0) return null;
  return (
    <div className="space-y-3">
      {entries.map(([key, value]) => (
        <div key={key}>
          <div className="text-xs font-semibold uppercase tracking-wide" style={{ color: SUB }}>
            {key.replace(/_/g, " ")}
          </div>
          {Array.isArray(value) ? (
            value.length === 0 ? (
              <p className="text-sm" style={{ color: SUB }}>—</p>
            ) : (
              <ul className="mt-1 list-disc space-y-1 pl-5 text-sm" style={{ color: INK }}>
                {value.map((v, i) => (
                  <li key={i}>{typeof v === "object" ? JSON.stringify(v) : String(v)}</li>
                ))}
              </ul>
            )
          ) : (
            <p className="mt-0.5 whitespace-pre-wrap text-sm" style={{ color: INK }}>
              {typeof value === "object" ? JSON.stringify(value) : String(value)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

export default function AssistantsHub() {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);
  const [form, setForm] = useState({});
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    assistantsApi
      .list()
      .then((data) => setList(data))
      .catch((e) => setError(formatApiError(e?.response?.data?.detail) || "Failed to load assistants."))
      .finally(() => setLoading(false));
  }, []);

  const fields = useMemo(() => (active ? FIELDS[active.key] || [] : []), [active]);

  function open(a) {
    setActive(a);
    setForm({});
    setResult(null);
    setError("");
  }

  async function run() {
    const missing = fields.filter((f) => f.required && !(form[f.key] || "").trim());
    if (missing.length) {
      setError(`Please fill: ${missing.map((m) => m.label).join(", ")}`);
      return;
    }
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const res = await assistantsApi.run(active.key, form);
      setResult(res);
    } catch (e) {
      setError(formatApiError(e?.response?.data?.detail) || "Run failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Sparkles}
        eyebrow="AI Assistants"
        title="AI Assistants"
        subtitle="Specialised AI helpers for meetings, quality, forecasting, personalisation and more."
      />

      {error && !active ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="flex items-center justify-center py-20" style={{ color: SUB }}>
          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading…
        </div>
      ) : list.length === 0 ? (
        <EmptyState icon={Sparkles} title="No assistants available" hint="Check back soon." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((a) => (
            <Card key={a.key} hover className="flex flex-col p-5">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl text-2xl" style={{ background: "#EFF4FF" }}>
                {a.icon}
              </div>
              <h3 className="mt-3 text-base font-semibold" style={{ color: INK }}>
                {a.label}
              </h3>
              <p className="mt-1 flex-1 text-sm leading-relaxed" style={{ color: SUB }}>
                {a.description}
              </p>
              <div className="mt-4">
                <PrimaryButton onClick={() => open(a)}>
                  <Wand2 className="mr-1.5 h-4 w-4" /> Open
                </PrimaryButton>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Runner modal */}
      {active ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b px-6 py-4" style={{ borderColor: LINE }}>
              <div className="flex items-center gap-3">
                <span className="text-2xl">{active.icon}</span>
                <div>
                  <h3 className="text-lg font-semibold" style={{ color: INK }}>{active.label}</h3>
                  <p className="text-xs" style={{ color: SUB }}>{active.description}</p>
                </div>
              </div>
              <button
                onClick={() => setActive(null)}
                className="rounded-lg px-2 py-1 text-sm font-medium text-[#64748B] hover:bg-[#F1F5F9]"
              >
                Close
              </button>
            </div>

            <div className="grid flex-1 grid-cols-1 gap-0 overflow-auto md:grid-cols-2">
              {/* Inputs */}
              <div className="space-y-3 border-b p-6 md:border-b-0 md:border-r" style={{ borderColor: LINE }}>
                {fields.map((f) => (
                  <div key={f.key}>
                    <label className="block text-xs font-semibold uppercase tracking-wide" style={{ color: SUB }}>
                      {f.label}{f.required ? " *" : ""}
                    </label>
                    {f.type === "textarea" ? (
                      <textarea
                        rows={5}
                        value={form[f.key] || ""}
                        onChange={(e) => setForm((p) => ({ ...p, [f.key]: e.target.value }))}
                        placeholder={f.placeholder}
                        className="mt-1 w-full resize-y rounded-xl border px-3 py-2 text-sm outline-none focus:border-[#2563EB]"
                        style={{ borderColor: LINE }}
                      />
                    ) : (
                      <input
                        value={form[f.key] || ""}
                        onChange={(e) => setForm((p) => ({ ...p, [f.key]: e.target.value }))}
                        placeholder={f.placeholder}
                        className="mt-1 w-full rounded-xl border px-3 py-2 text-sm outline-none focus:border-[#2563EB]"
                        style={{ borderColor: LINE }}
                      />
                    )}
                  </div>
                ))}
                {error && active ? (
                  <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                    {error}
                  </div>
                ) : null}
                <PrimaryButton onClick={run} disabled={running}>
                  {running ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <ArrowRight className="mr-1.5 h-4 w-4" />}
                  Run assistant
                </PrimaryButton>
              </div>

              {/* Output */}
              <div className="p-6">
                {running ? (
                  <div className="flex h-full items-center justify-center" style={{ color: SUB }}>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Thinking…
                  </div>
                ) : result ? (
                  <div className="space-y-3">
                    {!result.generated ? (
                      <Badge tone="amber">Offline fallback</Badge>
                    ) : (
                      <Badge tone="green">AI generated</Badge>
                    )}
                    <ResultView result={result.result} />
                  </div>
                ) : (
                  <div className="flex h-full items-center justify-center text-center text-sm" style={{ color: SUB }}>
                    Fill in the form and run to see results here.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
