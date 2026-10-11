import React, { useEffect, useState } from "react";
import {
  FlaskConical, Loader2, Play, AlertTriangle, CheckCircle2, XCircle,
  Activity, Search,
} from "lucide-react";
import {
  PageHeader,
  Card,
  Badge,
  SectionTitle,
  Segmented,
  PrimaryButton,
  EmptyState,
  INK,
  SUB,
  LINE,
  BRAND,
} from "@/components/dashboard/kit";
import { api, formatApiError } from "@/lib/api";
import { workspaceIntelApi } from "@/lib/workspaceIntel";

function confColor(v) {
  if (v >= 80) return "#16A34A";
  if (v >= 60) return "#2563EB";
  if (v >= 40) return "#D97706";
  return "#DC2626";
}

function Metric({ label, value, suffix = "" }) {
  return (
    <div className="rounded-xl border p-3 text-center" style={{ borderColor: LINE }}>
      <div className="text-xl font-bold" style={{ color: INK }}>{value}{suffix}</div>
      <div className="text-xs" style={{ color: SUB }}>{label}</div>
    </div>
  );
}

// ── Simulator tab ─────────────────────────────────────────────────────────
function SimulatorTab() {
  const [agents, setAgents] = useState([]);
  const [agentId, setAgentId] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/agents").then(({ data }) => {
      const list = Array.isArray(data) ? data : data?.items || [];
      setAgents(list);
      if (list[0]) setAgentId(list[0].id);
    }).catch(() => setAgents([]));
  }, []);

  const run = () => {
    if (!agentId) return;
    setRunning(true);
    setError("");
    workspaceIntelApi
      .runSimulator(agentId)
      .then(setResult)
      .catch((e) => setError(formatApiError(e?.response?.data?.detail) || "Simulation failed"))
      .finally(() => setRunning(false));
  };

  const s = result?.summary || {};

  return (
    <div className="space-y-6">
      <Card className="p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[220px]">
            <label className="text-xs font-semibold uppercase tracking-wide" style={{ color: SUB }}>Agent</label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="mt-1.5 w-full rounded-xl border py-2.5 px-3 text-sm outline-none"
              style={{ borderColor: LINE, color: INK }}
            >
              {agents.length === 0 && <option value="">No agents yet</option>}
              {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <PrimaryButton onClick={run} disabled={running || !agentId}>
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Run simulation
          </PrimaryButton>
        </div>
        <p className="mt-3 text-xs" style={{ color: SUB }}>
          Runs your agent through 11 real-world scenarios (happy, angry, pricing, refund, booking, multilingual, invalid input…) and scores each.
        </p>
      </Card>

      {error ? (
        <Card className="p-8">
          <EmptyState icon={AlertTriangle} title="Simulation failed" hint={error} />
        </Card>
      ) : running ? (
        <div className="grid place-items-center py-16" style={{ color: SUB }}>
          <Loader2 className="h-6 w-6 animate-spin" />
          <p className="mt-2 text-sm">Running scenarios…</p>
        </div>
      ) : !result ? (
        <Card className="p-8">
          <EmptyState icon={FlaskConical} title="Test before you publish"
            hint="Pick an agent and run the simulator to see how it handles tricky conversations." />
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Metric label="Success rate" value={s.success_rate ?? 0} suffix="%" />
            <Metric label="Accuracy" value={s.accuracy ?? 0} suffix="%" />
            <Metric label="Hallucination" value={s.hallucination ?? 0} suffix="%" />
            <Metric label="Knowledge use" value={s.knowledge_usage ?? 0} suffix="%" />
            <Metric label="Avg latency" value={s.latency_ms ?? 0} suffix="ms" />
          </div>

          {!result.generated && (
            <Card className="p-4">
              <div className="flex items-center gap-2 text-sm" style={{ color: "#D97706" }}>
                <AlertTriangle className="h-4 w-4" />
                AI provider is offline — results use a deterministic fallback. Connect a provider for live replies.
              </div>
            </Card>
          )}

          <Card className="p-6">
            <SectionTitle title="Scenario results" />
            <div className="mt-4 space-y-3">
              {(result.results || []).map((r) => (
                <div key={r.scenario} className="rounded-xl border p-4" style={{ borderColor: LINE }}>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      {r.verdict === "pass"
                        ? <CheckCircle2 className="h-5 w-5" style={{ color: "#16A34A" }} />
                        : <XCircle className="h-5 w-5" style={{ color: "#DC2626" }} />}
                      <span className="font-semibold" style={{ color: INK }}>{r.label}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs" style={{ color: SUB }}>
                      <Badge tone="blue">Acc {r.accuracy}%</Badge>
                      <Badge tone={r.hallucination > 25 ? "red" : "slate"}>Hall {r.hallucination}%</Badge>
                      <span>{r.latency_ms}ms</span>
                    </div>
                  </div>
                  <p className="mt-2 text-sm italic" style={{ color: SUB }}>"{r.opening}"</p>
                  <p className="mt-1 whitespace-pre-wrap text-sm" style={{ color: INK }}>{r.reply}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6">
            <SectionTitle title="Recommendations" />
            <div className="mt-4 space-y-3">
              {(result.recommendations || []).map((r, i) => (
                <div key={i} className="flex items-start gap-3 rounded-xl border p-4" style={{ borderColor: LINE }}>
                  <Activity className="mt-0.5 h-5 w-5 shrink-0" style={{ color: BRAND }} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold" style={{ color: INK }}>{r.title}</span>
                      <Badge tone={r.severity === "high" ? "red" : r.severity === "medium" ? "amber" : "slate"}>{r.severity}</Badge>
                    </div>
                    <p className="mt-0.5 text-sm" style={{ color: SUB }}>{r.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

// ── Heatmap tab ───────────────────────────────────────────────────────────
function HeatmapTab() {
  const [cid, setCid] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const run = (e) => {
    e?.preventDefault?.();
    const id = cid.trim();
    if (!id) return;
    setLoading(true);
    setError("");
    setSearched(true);
    workspaceIntelApi
      .confidenceHeatmap(id)
      .then(setData)
      .catch((e) => setError(formatApiError(e?.response?.data?.detail) || "Failed to load heatmap"))
      .finally(() => setLoading(false));
  };

  return (
    <div className="space-y-6">
      <Card className="p-4">
        <form onSubmit={run} className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: SUB }} />
            <input
              value={cid}
              onChange={(e) => setCid(e.target.value)}
              placeholder="Conversation ID (from Conversations page)"
              className="w-full rounded-xl border py-2.5 pl-10 pr-3 text-sm outline-none"
              style={{ borderColor: LINE, color: INK }}
            />
          </div>
          <PrimaryButton type="submit" disabled={loading || !cid.trim()}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Activity className="h-4 w-4" />}
            Analyze
          </PrimaryButton>
        </form>
      </Card>

      {loading ? (
        <div className="grid place-items-center py-16" style={{ color: SUB }}>
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : error ? (
        <Card className="p-8"><EmptyState icon={AlertTriangle} title="Couldn't analyze" hint={error} /></Card>
      ) : !searched ? (
        <Card className="p-8">
          <EmptyState icon={Activity} title="Visualize AI confidence"
            hint="Paste a conversation ID to see where the AI was confident or uncertain, turn by turn." />
        </Card>
      ) : !data?.found ? (
        <Card className="p-8">
          <EmptyState icon={Activity} title="Conversation not found"
            hint="Check the conversation ID and try again." />
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Overall confidence" value={data.overall ?? 0} suffix="%" />
            <Metric label="Agent turns" value={data.turns ?? 0} />
            <Metric label="Channel" value={data.channel || "—"} />
            <Metric label="Phases" value={(data.phases || []).filter((p) => p.confidence != null).length} />
          </div>

          <Card className="p-6">
            <SectionTitle title="Confidence by phase" />
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {(data.phases || []).map((ph) => (
                <div key={ph.phase}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium" style={{ color: INK }}>{ph.phase}</span>
                    <span style={{ color: SUB }}>{ph.confidence == null ? "—" : `${ph.confidence}%`}</span>
                  </div>
                  <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full" style={{ background: LINE }}>
                    <div className="h-full rounded-full"
                      style={{ width: `${ph.confidence || 0}%`, background: confColor(ph.confidence || 0), transition: "width .6s ease" }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6">
            <SectionTitle title="Turn-by-turn heatmap" />
            <div className="mt-4 space-y-2">
              {(data.timeline || []).map((seg) => (
                <div key={seg.index} className="flex items-center gap-3">
                  <div className="h-9 w-9 shrink-0 rounded-lg" title={`${seg.confidence}%`}
                    style={{ background: confColor(seg.confidence) }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge tone="slate">{seg.phase}</Badge>
                      <span className="text-xs font-semibold" style={{ color: confColor(seg.confidence) }}>{seg.confidence}%</span>
                      {seg.has_sources && <Badge tone="green">grounded</Badge>}
                    </div>
                    <p className="truncate text-sm" style={{ color: SUB }}>{seg.preview}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

export default function AgentQualityLab() {
  const [tab, setTab] = useState("simulator");
  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        icon={FlaskConical}
        eyebrow="Workspace Intelligence"
        title="Agent Quality Lab"
        subtitle="Simulate tricky conversations and visualize AI confidence before you ship."
        actions={
          <Segmented
            value={tab}
            onChange={setTab}
            options={[{ value: "simulator", label: "Simulator" }, { value: "heatmap", label: "Confidence Heatmap" }]}
          />
        }
      />
      {tab === "simulator" ? <SimulatorTab /> : <HeatmapTab />}
    </div>
  );
}
