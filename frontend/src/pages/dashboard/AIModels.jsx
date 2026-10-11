import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Cpu,
  Loader2,
  RefreshCw,
  Check,
  Star,
  Lock,
  Layers,
  Eye,
  EyeOff,
  Save,
  Sparkles,
  Gauge,
  DollarSign,
  Timer,
  Scale,
  Zap,
  TrendingDown,
  Trophy,
} from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { usePermissions } from "@/hooks/usePermissions";

const PROVIDER_META = {
  openai: { label: "OpenAI", color: "#10A37F" },
  anthropic: { label: "Anthropic", color: "#D97757" },
  google: { label: "Google", color: "#4285F4" },
  bedrock: { label: "Amazon", color: "#FF9900" },
  mock: { label: "Mock", color: "#64748B" },
};

function fmtCost(v) {
  if (v == null) return "—";
  return `$${v.toFixed(4)}`;
}

function fmtCtx(n) {
  if (!n) return "—";
  if (n >= 1000000) return `${(n / 1000000).toFixed(n % 1000000 ? 1 : 0)}M`;
  if (n >= 1000) return `${Math.round(n / 1000)}K`;
  return `${n}`;
}

function fmtLatency(ms) {
  if (ms == null) return "—";
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms}ms`;
}

const STRATEGIES = [
  { key: "balanced", label: "Balanced", icon: Scale, hint: "Curated default order" },
  { key: "cheapest", label: "Cheapest", icon: TrendingDown, hint: "Lowest cost first" },
  { key: "fastest", label: "Fastest", icon: Zap, hint: "Lowest latency first" },
  { key: "quality", label: "Highest quality", icon: Trophy, hint: "Most capable first" },
];

const RERANKERS = [
  { key: "heuristic", label: "Built-in", hint: "BM25 + lexical cross-scoring (no setup)" },
  { key: "cohere", label: "Cohere", hint: "Rerank API · needs COHERE_API_KEY" },
  { key: "jina", label: "Jina", hint: "Reranker API · needs JINA_API_KEY" },
  { key: "local", label: "Local BGE", hint: "bge-reranker · needs sentence-transformers" },
  { key: "none", label: "Off", hint: "Keep fused vector + BM25 order" },
];

function ProviderBadge({ provider }) {
  const meta = PROVIDER_META[provider] || { label: provider, color: "#64748B" };
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ backgroundColor: `${meta.color}1A`, color: meta.color }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: meta.color }}
      />
      {meta.label}
    </span>
  );
}

export default function AIModels() {
  const { can } = usePermissions();
  const [view, setView] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [defaultModel, setDefaultModel] = useState("");
  const [fallbacks, setFallbacks] = useState([]);
  const [disabled, setDisabled] = useState([]);
  const [strategy, setStrategy] = useState("balanced");
  const [budget, setBudget] = useState("");
  const [maxLatency, setMaxLatency] = useState("");
  const [hybridEnabled, setHybridEnabled] = useState(true);
  const [reranker, setReranker] = useState("heuristic");

  const canManage = can("settings.manage");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/ai/models");
      setView(data);
      setDefaultModel(data.default_model);
      setFallbacks(data.fallback_models || []);
      setDisabled(data.disabled_models || []);
      setStrategy(data.routing_strategy || "balanced");
      setBudget(data.monthly_budget_usd != null ? String(data.monthly_budget_usd) : "");
      setMaxLatency(data.max_latency_ms != null ? String(data.max_latency_ms) : "");
      setHybridEnabled(data.retrieval?.hybrid_enabled !== false);
      setReranker(data.retrieval?.reranker || "heuristic");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const models = view?.models || [];

  const dirty = useMemo(() => {
    if (!view) return false;
    const a = JSON.stringify({
      d: defaultModel,
      f: [...fallbacks].sort(),
      x: [...disabled].sort(),
      s: strategy,
      b: budget,
      l: maxLatency,
      h: hybridEnabled,
      r: reranker,
    });
    const b = JSON.stringify({
      d: view.default_model,
      f: [...(view.fallback_models || [])].sort(),
      x: [...(view.disabled_models || [])].sort(),
      s: view.routing_strategy || "balanced",
      b: view.monthly_budget_usd != null ? String(view.monthly_budget_usd) : "",
      l: view.max_latency_ms != null ? String(view.max_latency_ms) : "",
      h: view.retrieval?.hybrid_enabled !== false,
      r: view.retrieval?.reranker || "heuristic",
    });
    return a !== b;
  }, [view, defaultModel, fallbacks, disabled, strategy, budget, maxLatency, hybridEnabled, reranker]);

  const setAsDefault = (id) => {
    setDefaultModel(id);
    setFallbacks((prev) => prev.filter((f) => f !== id));
    setDisabled((prev) => prev.filter((d) => d !== id));
  };

  const toggleFallback = (id) => {
    if (id === defaultModel) return;
    setFallbacks((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]
    );
    setDisabled((prev) => prev.filter((d) => d !== id));
  };

  const toggleDisabled = (id) => {
    if (id === defaultModel) return;
    setDisabled((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
    setFallbacks((prev) => prev.filter((f) => f !== id));
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put("/ai/models/policy", {
        default_model: defaultModel,
        fallback_models: fallbacks,
        disabled_models: disabled,
        routing_strategy: strategy,
        monthly_budget_usd: budget === "" ? null : Number(budget),
        max_latency_ms: maxLatency === "" ? null : Number(maxLatency),
        hybrid_enabled: hybridEnabled,
        reranker: reranker,
      });
      setView(data);
      setDefaultModel(data.default_model);
      setFallbacks(data.fallback_models || []);
      setDisabled(data.disabled_models || []);
      setStrategy(data.routing_strategy || "balanced");
      setBudget(data.monthly_budget_usd != null ? String(data.monthly_budget_usd) : "");
      setMaxLatency(data.max_latency_ms != null ? String(data.max_latency_ms) : "");
      setHybridEnabled(data.retrieval?.hybrid_enabled !== false);
      setReranker(data.retrieval?.reranker || "heuristic");
      toast.success("Model routing policy saved");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="grid h-[60vh] place-items-center">
        <Loader2 className="h-6 w-6 animate-spin text-[#4F46E5]" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-6xl space-y-8 p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#EEF2FF] text-[#4F46E5]">
            <Cpu className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#0F172A]">AI Model Router</h1>
            <p className="text-sm text-[#64748B]">
              Choose the default model, set fallbacks, and control which
              models your agents may use.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            data-testid="aimodels-refresh"
            className="inline-flex items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
          >
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
          {canManage && (
            <button
              onClick={save}
              disabled={!dirty || saving}
              data-testid="aimodels-save"
              className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-50"
            >
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save changes
            </button>
          )}
        </div>
      </div>

      {/* Routing summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5">
          <div className="flex items-center gap-2 text-[#4F46E5]">
            <Star className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-wide">
              Default model
            </span>
          </div>
          <p className="mt-2 text-lg font-bold text-[#0F172A]">
            {view?.models.find((m) => m.id === defaultModel)?.label ||
              defaultModel}
          </p>
        </div>
        <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5">
          <div className="flex items-center gap-2 text-[#0EA5E9]">
            <Layers className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-wide">
              Fallback chain
            </span>
          </div>
          <p className="mt-2 text-sm font-medium text-[#0F172A]">
            {fallbacks.length
              ? fallbacks
                  .map(
                    (f) => view?.models.find((m) => m.id === f)?.label || f
                  )
                  .join(" → ")
              : "None configured"}
          </p>
        </div>
        <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5">
          <div className="flex items-center gap-2 text-[#64748B]">
            <Sparkles className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-wide">
              Plan
            </span>
          </div>
          <p className="mt-2 text-lg font-bold capitalize text-[#0F172A]">
            {view?.plan_code}
          </p>
          <Link
            to="/app/billing"
            className="text-xs font-medium text-[#4F46E5]"
          >
            Upgrade to unlock more models →
          </Link>
        </div>
      </div>

      {/* Routing rules */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5">
        <div className="flex items-center gap-2 text-[#0F172A]">
          <Gauge className="h-4 w-4 text-[#4F46E5]" />
          <h2 className="text-sm font-bold">Routing rules</h2>
        </div>
        <p className="mt-1 text-xs text-[#64748B]">
          Bias how the router picks among the models your agents may use, and
          cap spend &amp; latency.
        </p>

        {/* Strategy */}
        <div className="mt-4">
          <span className="text-xs font-semibold uppercase tracking-wide text-[#94A3B8]">
            Strategy
          </span>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {STRATEGIES.map((s) => {
              const Icon = s.icon;
              const active = strategy === s.key;
              return (
                <button
                  key={s.key}
                  type="button"
                  disabled={!canManage}
                  onClick={() => setStrategy(s.key)}
                  data-testid={`strategy-${s.key}`}
                  className={`flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition ${
                    active
                      ? "border-[#4F46E5] bg-[#EEF2FF]"
                      : "border-[#E2E8F0] bg-white hover:bg-[#F8FAFC]"
                  } ${!canManage ? "cursor-not-allowed opacity-60" : ""}`}
                >
                  <Icon
                    className={`h-4 w-4 ${active ? "text-[#4F46E5]" : "text-[#64748B]"}`}
                  />
                  <span
                    className={`text-sm font-semibold ${
                      active ? "text-[#4F46E5]" : "text-[#0F172A]"
                    }`}
                  >
                    {s.label}
                  </span>
                  <span className="text-[11px] text-[#94A3B8]">{s.hint}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Limits + spend */}
        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="block">
            <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[#94A3B8]">
              <DollarSign className="h-3.5 w-3.5" /> Monthly budget (USD)
            </span>
            <input
              type="number"
              min="0"
              step="0.01"
              disabled={!canManage}
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="No limit"
              data-testid="policy-budget"
              className="mt-1.5 w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm text-[#0F172A] focus:border-[#4F46E5] focus:outline-none disabled:bg-[#F8FAFC]"
            />
            <span className="mt-1 block text-[11px] text-[#94A3B8]">
              Over budget → routes to the cheapest model.
            </span>
          </label>
          <label className="block">
            <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[#94A3B8]">
              <Timer className="h-3.5 w-3.5" /> Max latency (ms)
            </span>
            <input
              type="number"
              min="0"
              step="50"
              disabled={!canManage}
              value={maxLatency}
              onChange={(e) => setMaxLatency(e.target.value)}
              placeholder="No limit"
              data-testid="policy-latency"
              className="mt-1.5 w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm text-[#0F172A] focus:border-[#4F46E5] focus:outline-none disabled:bg-[#F8FAFC]"
            />
            <span className="mt-1 block text-[11px] text-[#94A3B8]">
              Skip models slower than this typical latency.
            </span>
          </label>
          <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-3">
            <span className="text-xs font-semibold uppercase tracking-wide text-[#94A3B8]">
              This month's spend
            </span>
            <p
              className={`mt-1 text-lg font-bold ${
                view?.budget_exceeded ? "text-[#DC2626]" : "text-[#0F172A]"
              }`}
              data-testid="policy-spend"
            >
              ${(view?.current_month_spend_usd ?? 0).toFixed(2)}
              {view?.monthly_budget_usd != null && (
                <span className="text-sm font-medium text-[#94A3B8]">
                  {" "}
                  / ${view.monthly_budget_usd.toFixed(2)}
                </span>
              )}
            </p>
            {view?.monthly_budget_usd != null && (
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#E2E8F0]">
                <div
                  className={`h-full rounded-full ${
                    view.budget_exceeded ? "bg-[#DC2626]" : "bg-[#4F46E5]"
                  }`}
                  style={{
                    width: `${Math.min(
                      100,
                      ((view.current_month_spend_usd ?? 0) /
                        (view.monthly_budget_usd || 1)) *
                        100
                    )}%`,
                  }}
                />
              </div>
            )}
            {view?.budget_exceeded && (
              <p className="mt-1.5 text-[11px] font-medium text-[#DC2626]">
                Budget exceeded — routing to cheapest model.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Retrieval & reranking */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5" data-testid="retrieval-panel">
        <div className="flex items-center gap-2 text-[#0F172A]">
          <Layers className="h-4 w-4 text-[#4F46E5]" />
          <h2 className="text-sm font-bold">Knowledge retrieval</h2>
        </div>
        <p className="mt-1 text-xs text-[#64748B]">
          Answers use hybrid search — dense vectors fused with BM25 keyword
          ranking — then a cross-encoder reranker re-scores the top passages
          for sharper grounding.
        </p>

        <label
          className={`mt-4 flex items-center justify-between gap-3 rounded-xl border p-3 ${
            hybridEnabled ? "border-[#4F46E5] bg-[#EEF2FF]" : "border-[#E2E8F0] bg-white"
          } ${!canManage ? "opacity-60" : "cursor-pointer"}`}
        >
          <span>
            <span className="block text-sm font-semibold text-[#0F172A]">
              Cross-encoder reranking
            </span>
            <span className="block text-xs text-[#64748B]">
              Re-rank fused candidates for higher answer precision.
            </span>
          </span>
          <input
            type="checkbox"
            disabled={!canManage}
            checked={hybridEnabled}
            onChange={(e) => setHybridEnabled(e.target.checked)}
            data-testid="retrieval-rerank-toggle"
            className="h-4 w-4 accent-[#4F46E5]"
          />
        </label>

        <div className="mt-4">
          <span className="text-xs font-semibold uppercase tracking-wide text-[#94A3B8]">
            Reranker engine
          </span>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-5">
            {RERANKERS.map((r) => {
              const active = reranker === r.key;
              return (
                <button
                  key={r.key}
                  type="button"
                  disabled={!canManage || (!hybridEnabled && r.key !== "none")}
                  onClick={() => setReranker(r.key)}
                  data-testid={`reranker-${r.key}`}
                  title={r.hint}
                  className={`flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition ${
                    active
                      ? "border-[#4F46E5] bg-[#EEF2FF]"
                      : "border-[#E2E8F0] bg-white hover:bg-[#F8FAFC]"
                  } ${
                    !canManage || (!hybridEnabled && r.key !== "none")
                      ? "cursor-not-allowed opacity-60"
                      : ""
                  }`}
                >
                  <span
                    className={`text-sm font-semibold ${
                      active ? "text-[#4F46E5]" : "text-[#0F172A]"
                    }`}
                  >
                    {r.label}
                  </span>
                  <span className="text-[11px] leading-tight text-[#64748B]">
                    {r.hint}
                  </span>
                </button>
              );
            })}
          </div>
          <p className="mt-2 text-[11px] text-[#94A3B8]">
            Remote engines fall back to the built-in reranker automatically if
            their API key is missing or unreachable.
          </p>
        </div>
      </div>

      {/* Model catalogue */}
      <div className="overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#E2E8F0] bg-[#F8FAFC] text-left text-xs uppercase tracking-wide text-[#94A3B8]">
              <th className="px-5 py-3 font-semibold">Model</th>
              <th className="px-5 py-3 font-semibold">Provider</th>
              <th className="px-5 py-3 font-semibold">Context</th>
              <th className="px-5 py-3 font-semibold">Cost / 1K (in / out)</th>
              <th className="px-5 py-3 font-semibold">Latency</th>
              <th className="px-5 py-3 font-semibold">Status</th>
              {canManage && <th className="px-5 py-3 text-right font-semibold">Routing</th>}
            </tr>
          </thead>
          <tbody>
            {models.map((m) => {
              const isDefault = m.id === defaultModel;
              const isFallback = fallbacks.includes(m.id);
              const isDisabled = disabled.includes(m.id);
              return (
                <tr
                  key={m.id}
                  data-testid={`model-row-${m.id}`}
                  className={`border-b border-[#F1F5F9] last:border-0 ${
                    !m.entitled ? "opacity-60" : ""
                  }`}
                >
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-[#0F172A]">
                        {m.label}
                      </span>
                      {m.tier === "premium" && (
                        <span className="rounded bg-[#FEF3C7] px-1.5 py-0.5 text-[10px] font-semibold uppercase text-[#B45309]">
                          Premium
                        </span>
                      )}
                    </div>
                    <span className="font-mono text-[11px] text-[#94A3B8]">
                      {m.id}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <ProviderBadge provider={m.provider} />
                  </td>
                  <td className="px-5 py-4 text-[#475569]">
                    {fmtCtx(m.context_window)}
                  </td>
                  <td className="px-5 py-4 text-[#475569]">
                    {fmtCost(m.input_per_1k)} / {fmtCost(m.output_per_1k)}
                  </td>
                  <td className="px-5 py-4 text-[#475569]">
                    {fmtLatency(m.typical_latency_ms)}
                  </td>
                  <td className="px-5 py-4">
                    {!m.entitled ? (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-[#94A3B8]">
                        <Lock className="h-3.5 w-3.5" /> Requires {m.min_plan}
                      </span>
                    ) : isDefault ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-[#EEF2FF] px-2 py-0.5 text-xs font-semibold text-[#4F46E5]">
                        <Star className="h-3.5 w-3.5" /> Default
                      </span>
                    ) : isDisabled ? (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-[#DC2626]">
                        <EyeOff className="h-3.5 w-3.5" /> Disabled
                      </span>
                    ) : isFallback ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-[#E0F2FE] px-2 py-0.5 text-xs font-semibold text-[#0369A1]">
                        <Layers className="h-3.5 w-3.5" /> Fallback
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-[#16A34A]">
                        <Check className="h-3.5 w-3.5" /> Available
                      </span>
                    )}
                  </td>
                  {canManage && (
                    <td className="px-5 py-4">
                      {m.entitled ? (
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => setAsDefault(m.id)}
                            disabled={isDefault}
                            data-testid={`model-default-${m.id}`}
                            title="Set as default"
                            className={`rounded-lg p-1.5 ${
                              isDefault
                                ? "text-[#CBD5E1]"
                                : "text-[#475569] hover:bg-[#EEF2FF] hover:text-[#4F46E5]"
                            }`}
                          >
                            <Star className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => toggleFallback(m.id)}
                            disabled={isDefault}
                            data-testid={`model-fallback-${m.id}`}
                            title="Toggle fallback"
                            className={`rounded-lg p-1.5 ${
                              isFallback
                                ? "bg-[#E0F2FE] text-[#0369A1]"
                                : "text-[#475569] hover:bg-[#F1F5F9]"
                            } ${isDefault ? "opacity-40" : ""}`}
                          >
                            <Layers className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => toggleDisabled(m.id)}
                            disabled={isDefault}
                            data-testid={`model-disable-${m.id}`}
                            title="Toggle disabled"
                            className={`rounded-lg p-1.5 ${
                              isDisabled
                                ? "bg-[#FEE2E2] text-[#DC2626]"
                                : "text-[#475569] hover:bg-[#F1F5F9]"
                            } ${isDefault ? "opacity-40" : ""}`}
                          >
                            {isDisabled ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </button>
                        </div>
                      ) : (
                        <div className="text-right">
                          <Link
                            to="/app/billing"
                            className="text-xs font-medium text-[#4F46E5]"
                          >
                            Upgrade
                          </Link>
                        </div>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-[#94A3B8]">
        The router picks an agent's model in this order: the agent's
        requested model (if allowed) → your default → fallbacks → first
        available model. Disabled models are never used.
      </p>
    </motion.div>
  );
}
