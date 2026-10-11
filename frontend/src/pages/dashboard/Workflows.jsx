import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Workflow as WorkflowIcon,
  Plus,
  Play,
  Loader2,
  X,
  Trash2,
  Clock,
  CheckCircle2,
  XCircle,
  ChevronRight,
  Sparkles,
  BookOpen,
  Bot,
  GitBranch,
  Wand2,
  Bell,
  Timer,
  Webhook,
  RefreshCw,
  PauseCircle,
  PlayCircle,
  Tags,
  ScanText,
  FileText,
  Gauge,
  Languages,
  ShieldCheck,
  BarChart3,
  History,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import WorkflowCanvas from "./WorkflowCanvas";

/* ── Step type catalog ── */
const STEP_TYPES = [
  { type: "ai_prompt", label: "AI Prompt", icon: Sparkles, hint: "Ask the LLM with a templated prompt." },
  { type: "ai_classify", label: "AI Classify", icon: Tags, hint: "Classify text into one of your categories." },
  { type: "ai_extract", label: "AI Extract", icon: ScanText, hint: "Extract structured fields into variables." },
  { type: "ai_summarize", label: "AI Summarize", icon: FileText, hint: "Summarize long text." },
  { type: "ai_sentiment", label: "AI Sentiment", icon: Gauge, hint: "Detect positive / negative / neutral." },
  { type: "ai_translate", label: "AI Translate", icon: Languages, hint: "Translate text to a target language." },
  { type: "kb_query", label: "Knowledge Base", icon: BookOpen, hint: "Retrieve relevant context from your KB." },
  { type: "agent_run", label: "Run Agent", icon: Bot, hint: "Run one of your configured agents." },
  { type: "transform", label: "Transform", icon: Wand2, hint: "Render a template into a new variable." },
  { type: "condition", label: "Condition", icon: GitBranch, hint: "Stop the run unless a predicate holds." },
  { type: "approval", label: "Human Approval", icon: ShieldCheck, hint: "Pause for a human to approve or reject." },
  { type: "notification", label: "Notify", icon: Bell, hint: "Emit a notification (logged)." },
  { type: "delay", label: "Delay", icon: Timer, hint: "Wait a bounded number of seconds." },
  { type: "webhook", label: "Webhook", icon: Webhook, hint: "POST to an external URL." },
];

const STEP_META = Object.fromEntries(STEP_TYPES.map((s) => [s.type, s]));

/* Lookup used by the visual canvas (icon + label per step type). */
const getStepMeta = (type) => STEP_META[type] || STEP_TYPES[0];

const TRIGGERS = [
  { value: "manual", label: "Manual" },
  { value: "schedule", label: "Schedule" },
  { value: "event", label: "Event" },
  { value: "integration", label: "Integration sync" },
];

const STATUS_STYLES = {
  draft: "bg-[#F1F5F9] text-[#475569]",
  active: "bg-[#ECFDF5] text-[#047857]",
  paused: "bg-[#FEF3C7] text-[#B45309]",
};

const RUN_STATUS_STYLES = {
  queued: { cls: "bg-[#F1F5F9] text-[#475569]", icon: Clock },
  running: { cls: "bg-[#EFF6FF] text-[#2563EB]", icon: Loader2 },
  awaiting_approval: { cls: "bg-[#FEF3C7] text-[#B45309]", icon: ShieldCheck },
  completed: { cls: "bg-[#ECFDF5] text-[#047857]", icon: CheckCircle2 },
  failed: { cls: "bg-[#FEF2F2] text-[#B91C1C]", icon: XCircle },
  cancelled: { cls: "bg-[#F1F5F9] text-[#64748B]", icon: XCircle },
};

function emptyStep(type = "ai_prompt") {
  return { type, name: STEP_META[type]?.label || "Step", config: {} };
}

/* ───────────────────────── page ───────────────────────── */

export default function Workflows() {
  const [items, setItems] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, stats] = await Promise.allSettled([
        api.get("/workflows", { params: { limit: 100 } }),
        api.get("/workflows/analytics"),
      ]);
      if (list.status === "fulfilled") setItems(list.value.data.items || []);
      else toast.error(formatApiError(list.reason));
      if (stats.status === "fulfilled") setAnalytics(stats.value.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-8" data-testid="workflows-dashboard">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[12px] font-semibold tracking-[0.18em] text-[#2563EB] uppercase">
            Workflows
          </p>
          <h1 className="mt-1 text-2xl sm:text-3xl font-black text-[#0F172A]">
            Automate work across your AI stack.
          </h1>
          <p className="mt-1 text-sm text-[#64748B]">
            Chain your AI, knowledge bases and agents into repeatable, multi-step automations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[#E2E8F0] bg-white hover:bg-[#F8FAFC] text-[#0F172A] text-sm font-semibold"
          >
            <RefreshCw size={13} /> Refresh
          </button>
          <button
            onClick={() => setCreateOpen(true)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold"
          >
            <Plus size={15} /> New Workflow
          </button>
        </div>
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center py-24 text-[#64748B]">
          <Loader2 className="animate-spin" size={22} />
        </div>
      ) : items.length === 0 ? (
        <EmptyState onCreate={() => setCreateOpen(true)} />
      ) : (
        <>
          <AnalyticsStrip data={analytics} />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((wf) => (
              <WorkflowCard key={wf.id} workflow={wf} onOpen={() => setSelected(wf)} />
            ))}
          </div>
        </>
      )}

      <AnimatePresence>
        {createOpen && (
          <WorkflowEditor
            onClose={() => setCreateOpen(false)}
            onSaved={() => {
              setCreateOpen(false);
              load();
            }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {selected && (
          <WorkflowDrawer
            workflowId={selected.id}
            onClose={() => setSelected(null)}
            onChanged={load}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function EmptyState({ onCreate }) {
  return (
    <div className="rounded-2xl border border-dashed border-[#CBD5E1] bg-white py-16 text-center">
      <div className="mx-auto w-12 h-12 rounded-2xl bg-[#EFF6FF] flex items-center justify-center">
        <WorkflowIcon className="text-[#2563EB]" size={22} />
      </div>
      <h3 className="mt-4 text-lg font-bold text-[#0F172A]">No workflows yet</h3>
      <p className="mt-1 text-sm text-[#64748B]">
        Build your first automation — retrieve, reason, and act in one flow.
      </p>
      <button
        onClick={onCreate}
        className="mt-5 inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold"
      >
        <Plus size={15} /> New Workflow
      </button>
    </div>
  );
}

function AnalyticsStrip({ data }) {
  if (!data) return null;
  const cards = [
    { label: "Workflows", value: data.total_workflows, sub: `${data.active_workflows} active` },
    { label: "Total runs", value: data.total_runs, sub: `${data.completed_runs} completed` },
    { label: "Success rate", value: `${data.success_rate ?? 0}%`, sub: `${data.failed_runs} failed` },
    {
      label: "Avg duration",
      value: data.avg_duration_seconds != null ? `${data.avg_duration_seconds}s` : "—",
      sub: data.awaiting_approval ? `${data.awaiting_approval} awaiting` : "all clear",
    },
  ];
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map((c) => (
        <div key={c.label} className="p-4 rounded-2xl border border-[#E2E8F0] bg-white">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold tracking-wide text-[#64748B] uppercase">
            <BarChart3 size={12} className="text-[#2563EB]" /> {c.label}
          </div>
          <div className="mt-1.5 text-2xl font-black text-[#0F172A]">{c.value}</div>
          <div className="text-[12px] text-[#94A3B8]">{c.sub}</div>
        </div>
      ))}
    </div>
  );
}

function WorkflowCard({ workflow, onOpen }) {
  const rate =
    workflow.run_count > 0
      ? Math.round((workflow.success_count / workflow.run_count) * 100)
      : null;
  return (
    <button
      onClick={onOpen}
      className="text-left p-5 rounded-2xl border border-[#E2E8F0] bg-white hover:shadow-premium transition-all"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#EFF6FF] flex items-center justify-center">
          <WorkflowIcon className="text-[#2563EB]" size={18} />
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize ${STATUS_STYLES[workflow.status] || STATUS_STYLES.draft}`}>
          {workflow.status}
        </span>
      </div>
      <h3 className="mt-3 font-bold text-[#0F172A] truncate">{workflow.name}</h3>
      <p className="mt-1 text-sm text-[#64748B] line-clamp-2 min-h-[40px]">
        {workflow.description || "No description."}
      </p>
      <div className="mt-3 flex items-center gap-4 text-[12px] text-[#64748B]">
        <span>{workflow.run_count} runs</span>
        {rate !== null && <span>{rate}% success</span>}
        <span className="ml-auto inline-flex items-center gap-1 text-[#2563EB] font-semibold">
          Open <ChevronRight size={13} />
        </span>
      </div>
    </button>
  );
}

/* ───────────────────────── editor (create) ───────────────────────── */

function WorkflowEditor({ onClose, onSaved }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState("manual");
  const [intervalMinutes, setIntervalMinutes] = useState(60);
  const [steps, setSteps] = useState([emptyStep("ai_prompt")]);
  const [saving, setSaving] = useState(false);
  const [agents, setAgents] = useState([]);
  const [kbs, setKbs] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const [a, k] = await Promise.allSettled([
          api.get("/agents", { params: { limit: 100 } }),
          api.get("/knowledge-bases", { params: { limit: 100 } }),
        ]);
        if (a.status === "fulfilled") setAgents(a.value.data.items || a.value.data || []);
        if (k.status === "fulfilled") setKbs(k.value.data.items || k.value.data || []);
      } catch {
        /* optional helpers */
      }
    })();
  }, []);

  const addStep = (type) => setSteps((s) => [...s, emptyStep(type)]);
  const removeStep = (i) => setSteps((s) => s.filter((_, idx) => idx !== i));
  const updateStep = (i, patch) =>
    setSteps((s) => s.map((st, idx) => (idx === i ? { ...st, ...patch } : st)));
  const setStepConfig = (i, key, value) =>
    setSteps((s) =>
      s.map((st, idx) => (idx === i ? { ...st, config: { ...st.config, [key]: value } } : st))
    );

  const save = async () => {
    if (!name.trim()) return toast.error("Give your workflow a name.");
    if (steps.length === 0) return toast.error("Add at least one step.");
    setSaving(true);
    try {
      await api.post("/workflows", {
        name: name.trim(),
        description: description.trim() || null,
        trigger_type: triggerType,
        trigger_config:
          triggerType === "schedule"
            ? { interval_minutes: Math.max(1, Number(intervalMinutes) || 60) }
            : {},
        steps: steps.map((s, i) => ({
          type: s.type,
          name: s.name.trim() || STEP_META[s.type].label,
          config: s.config,
          order_index: i,
        })),
      });
      toast.success("Workflow created.");
      onSaved();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Overlay onClose={onClose}>
      <div className="p-6 border-b border-[#E2E8F0] flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-[#0F172A]">New Workflow</h2>
          <p className="text-sm text-[#64748B]">Define the trigger and an ordered list of steps.</p>
        </div>
        <button onClick={onClose} className="p-2 rounded-lg hover:bg-[#F1F5F9]">
          <X size={18} className="text-[#64748B]" />
        </button>
      </div>

      <div className="p-6 space-y-6 overflow-y-auto">
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Name">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Weekly support digest"
              className="w-full px-3 py-2 rounded-xl border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
            />
          </Field>
          <Field label="Trigger">
            <select
              value={triggerType}
              onChange={(e) => setTriggerType(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-[#E2E8F0] text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
            >
              {TRIGGERS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {triggerType === "schedule" && (
          <Field label="Run every (minutes)">
            <input
              type="number"
              min={1}
              value={intervalMinutes}
              onChange={(e) => setIntervalMinutes(Number(e.target.value))}
              placeholder="60"
              className="w-full px-3 py-2 rounded-xl border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
            />
            <span className="mt-1 block text-[11px] text-[#94A3B8]">
              The workflow must be Active for the scheduler to run it.
            </span>
          </Field>
        )}
        <Field label="Description">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="What does this automation do?"
            className="w-full px-3 py-2 rounded-xl border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
          />
        </Field>

        {/* Steps */}
        <div>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-[#0F172A]">Steps</h3>
            <span className="text-[12px] text-[#94A3B8]">
              Reference earlier outputs with <code className="px-1 bg-[#F1F5F9] rounded">{"{{var}}"}</code>
            </span>
          </div>

          {/* Visual flow preview — updates live as steps are added/edited */}
          <div className="mt-3">
            <WorkflowCanvas
              steps={steps}
              getMeta={getStepMeta}
              triggerLabel={TRIGGERS.find((t) => t.value === triggerType)?.label || "Manual"}
            />
          </div>

          <div className="mt-3 space-y-3">
            {steps.map((step, i) => (
              <StepEditor
                key={i}
                index={i}
                step={step}
                agents={agents}
                kbs={kbs}
                onName={(v) => updateStep(i, { name: v })}
                onType={(v) => updateStep(i, { type: v, name: STEP_META[v].label, config: {} })}
                onConfig={(key, val) => setStepConfig(i, key, val)}
                onRemove={() => removeStep(i)}
              />
            ))}
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {STEP_TYPES.map((s) => (
              <button
                key={s.type}
                onClick={() => addStep(s.type)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[#E2E8F0] bg-white hover:bg-[#F8FAFC] text-[12px] font-semibold text-[#334155]"
              >
                <s.icon size={13} className="text-[#2563EB]" /> {s.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="p-6 border-t border-[#E2E8F0] flex items-center justify-end gap-2">
        <button onClick={onClose} className="px-4 py-2 rounded-xl border border-[#E2E8F0] text-sm font-semibold text-[#334155] hover:bg-[#F8FAFC]">
          Cancel
        </button>
        <button
          onClick={save}
          disabled={saving}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-60 text-white text-sm font-semibold"
        >
          {saving ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle2 size={15} />}
          Create Workflow
        </button>
      </div>
    </Overlay>
  );
}

function StepEditor({ index, step, agents, kbs, onName, onType, onConfig, onRemove }) {
  const meta = STEP_META[step.type] || STEP_TYPES[0];
  const Icon = meta.icon;
  const c = step.config || {};
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-[#FBFCFE]">
      <div className="p-3 flex items-center gap-2 border-b border-[#EEF2F7]">
        <span className="w-6 h-6 rounded-md bg-[#EFF6FF] text-[#2563EB] text-[11px] font-bold flex items-center justify-center">
          {index + 1}
        </span>
        <Icon size={15} className="text-[#2563EB]" />
        <select
          value={step.type}
          onChange={(e) => onType(e.target.value)}
          className="text-sm font-semibold bg-transparent focus:outline-none text-[#0F172A]"
        >
          {STEP_TYPES.map((s) => (
            <option key={s.type} value={s.type}>
              {s.label}
            </option>
          ))}
        </select>
        <input
          value={step.name}
          onChange={(e) => onName(e.target.value)}
          className="ml-auto w-44 px-2 py-1 rounded-lg border border-[#E2E8F0] text-[12px] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
          placeholder="Step name"
        />
        <button onClick={onRemove} className="p-1.5 rounded-lg hover:bg-[#FEF2F2]">
          <Trash2 size={14} className="text-[#EF4444]" />
        </button>
      </div>
      <div className="p-3 space-y-2">
        <p className="text-[12px] text-[#94A3B8]">{meta.hint}</p>
        <StepConfig step={step} agents={agents} kbs={kbs} onConfig={onConfig} />
        <details className="mt-1 group">
          <summary className="cursor-pointer text-[11px] font-semibold text-[#64748B] hover:text-[#2563EB] select-none">
            Error handling
          </summary>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <label className="block">
              <span className="block text-[11px] text-[#64748B] mb-1">Retries</span>
              <input
                type="number"
                min={0}
                max={5}
                value={c.retry ?? 0}
                onChange={(e) => onConfig("retry", Number(e.target.value))}
                className="w-full px-2 py-1.5 rounded-lg border border-[#E2E8F0] text-[12px] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
              />
            </label>
            <label className="block">
              <span className="block text-[11px] text-[#64748B] mb-1">Retry delay (s)</span>
              <input
                type="number"
                min={0}
                max={30}
                value={c.retry_delay ?? 2}
                onChange={(e) => onConfig("retry_delay", Number(e.target.value))}
                className="w-full px-2 py-1.5 rounded-lg border border-[#E2E8F0] text-[12px] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
              />
            </label>
            <label className="col-span-2 inline-flex items-center gap-2 text-[12px] text-[#334155]">
              <input
                type="checkbox"
                checked={!!c.continue_on_error}
                onChange={(e) => onConfig("continue_on_error", e.target.checked)}
              />
              Continue the run even if this step fails
            </label>
          </div>
        </details>
      </div>
    </div>
  );
}

function StepConfig({ step, agents, kbs, onConfig }) {
  const c = step.config || {};
  const ta = (key, ph, rows = 2) => (
    <textarea
      value={c[key] || ""}
      onChange={(e) => onConfig(key, e.target.value)}
      rows={rows}
      placeholder={ph}
      className="w-full px-3 py-2 rounded-lg border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
    />
  );
  const inp = (key, ph, type = "text") => (
    <input
      type={type}
      value={c[key] ?? ""}
      onChange={(e) => onConfig(key, type === "number" ? Number(e.target.value) : e.target.value)}
      placeholder={ph}
      className="w-full px-3 py-2 rounded-lg border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
    />
  );

  switch (step.type) {
    case "ai_prompt":
      return (
        <div className="space-y-2">
          {ta("system", "System prompt (optional)")}
          {ta("prompt", "User prompt. Use {{input}} or earlier {{vars}}.", 3)}
          {inp("output_var", "Output variable name (default: ai_output)")}
        </div>
      );
    case "ai_classify":
      return (
        <div className="space-y-2">
          {ta("input", "Text to classify. Supports {{vars}}.")}
          {inp("categories", "Categories, comma-separated (e.g. Sales, Support, Spam)")}
          {inp("output_var", "Output variable (default: classification)")}
        </div>
      );
    case "ai_extract":
      return (
        <div className="space-y-2">
          {ta("input", "Text to extract from. Supports {{vars}}.")}
          {inp("fields", "Fields, comma-separated (e.g. name, email, amount)")}
          {inp("output_var", "Output variable (default: extracted)")}
        </div>
      );
    case "ai_summarize":
      return (
        <div className="space-y-2">
          {ta("input", "Text to summarize. Supports {{vars}}.", 3)}
          {inp("max_words", "Max words (default 120)", "number")}
          {inp("output_var", "Output variable (default: summary)")}
        </div>
      );
    case "ai_sentiment":
      return (
        <div className="space-y-2">
          {ta("input", "Text to analyze. Supports {{vars}}.")}
          {inp("output_var", "Output variable (default: sentiment)")}
        </div>
      );
    case "ai_translate":
      return (
        <div className="space-y-2">
          {ta("input", "Text to translate. Supports {{vars}}.")}
          {inp("target_language", "Target language (e.g. French)")}
          {inp("output_var", "Output variable (default: translation)")}
        </div>
      );
    case "approval":
      return (
        <div className="space-y-2">
          {ta("message", "What should the reviewer approve? Supports {{vars}}.", 3)}
          <p className="text-[11px] text-[#94A3B8]">
            The run pauses here until an owner/admin approves or rejects it.
          </p>
        </div>
      );
    case "kb_query":
      return (
        <div className="space-y-2">
          {ta("query", "Search query. Supports {{vars}}.")}
          <select
            multiple
            value={c.knowledge_base_ids || []}
            onChange={(e) =>
              onConfig(
                "knowledge_base_ids",
                Array.from(e.target.selectedOptions).map((o) => o.value)
              )
            }
            className="w-full px-3 py-2 rounded-lg border border-[#E2E8F0] text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
          >
            {kbs.map((k) => (
              <option key={k.id} value={k.id}>
                {k.name}
              </option>
            ))}
          </select>
          {inp("top_k", "Top K (default 5)", "number")}
          {inp("output_var", "Output variable (default: kb_results)")}
        </div>
      );
    case "agent_run":
      return (
        <div className="space-y-2">
          <select
            value={c.agent_id || ""}
            onChange={(e) => onConfig("agent_id", e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-[#E2E8F0] text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
          >
            <option value="">Select an agent…</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          {ta("message", "Message to the agent. Supports {{vars}}.")}
          {inp("output_var", "Output variable (default: agent_output)")}
        </div>
      );
    case "transform":
      return (
        <div className="space-y-2">
          {ta("template", "Template, e.g. Summary: {{ai_output}}", 3)}
          {inp("output_var", "Output variable (default: transform_output)")}
        </div>
      );
    case "condition":
      return (
        <div className="grid grid-cols-3 gap-2">
          {inp("left", "Left ({{var}})")}
          <select
            value={c.op || "contains"}
            onChange={(e) => onConfig("op", e.target.value)}
            className="px-2 py-2 rounded-lg border border-[#E2E8F0] text-sm bg-white focus:outline-none"
          >
            {["contains", "not_contains", "eq", "ne", "gt", "lt", "nonempty"].map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
          {inp("right", "Right")}
        </div>
      );
    case "notification":
      return (
        <div className="space-y-2">
          {inp("channel", "Channel (e.g. log, email)")}
          {ta("message", "Message. Supports {{vars}}.")}
        </div>
      );
    case "delay":
      return <div>{inp("seconds", "Seconds (max 60)", "number")}</div>;
    case "webhook":
      return (
        <div className="space-y-2">
          {inp("url", "https://…")}
          {ta("payload", 'JSON-ish text or "{{var}}" body')}
        </div>
      );
    default:
      return null;
  }
}

/* ───────────────────────── drawer (detail + runs) ───────────────────────── */

function WorkflowDrawer({ workflowId, onClose, onChanged }) {
  const [wf, setWf] = useState(null);
  const [runs, setRuns] = useState([]);
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [activeRun, setActiveRun] = useState(null);
  const [busy, setBusy] = useState(false);
  const [deciding, setDeciding] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [d, r, v] = await Promise.all([
        api.get(`/workflows/${workflowId}`),
        api.get(`/workflows/${workflowId}/runs`, { params: { limit: 25 } }),
        api.get(`/workflows/${workflowId}/versions`),
      ]);
      setWf(d.data);
      setRuns(r.data.items || []);
      setVersions(v.data.items || []);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    load();
  }, [load]);

  const runNow = async () => {
    setRunning(true);
    try {
      const { data } = await api.post(`/workflows/${workflowId}/run`, { input: {} });
      toast.success("Run started.");
      // Poll the run until it finishes.
      pollRun(data.id);
    } catch (e) {
      toast.error(formatApiError(e));
      setRunning(false);
    }
  };

  const pollRun = useCallback(
    async (runId, { resuming = false } = {}) => {
      let tries = 0;
      // When resuming after an approval, the backend transitions out of
      // awaiting_approval asynchronously — keep polling until it moves past
      // the current pause before treating awaiting_approval as a new stop.
      let movedPast = !resuming;
      const tick = async () => {
        tries += 1;
        try {
          const { data } = await api.get(`/workflows/runs/${runId}`);
          setActiveRun(data);
          if (data.status !== "awaiting_approval") movedPast = true;
          if (data.status === "awaiting_approval" && movedPast) {
            // Paused for a human decision — stop polling, show approve/reject.
            setRunning(false);
            load();
            onChanged?.();
            return;
          }
          if (data.status === "completed" || data.status === "failed" || data.status === "cancelled") {
            setRunning(false);
            load();
            onChanged?.();
            return;
          }
        } catch {
          /* keep trying */
        }
        if (tries < 40) setTimeout(tick, 1200);
        else setRunning(false);
      };
      tick();
    },
    [load, onChanged]
  );

  const decide = async (decision) => {
    if (!activeRun) return;
    setDeciding(true);
    try {
      await api.post(`/workflows/runs/${activeRun.id}/decision`, { decision });
      toast.success(decision === "approve" ? "Approved — resuming." : "Rejected.");
      if (decision === "approve") {
        setRunning(true);
        pollRun(activeRun.id, { resuming: true });
      } else {
        load();
        onChanged?.();
      }
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setDeciding(false);
    }
  };

  const rollback = async (version) => {
    if (!window.confirm(`Roll back to version ${version}? Current state is saved first.`)) return;
    setBusy(true);
    try {
      await api.post(`/workflows/${workflowId}/versions/${version}/rollback`);
      toast.success(`Rolled back to v${version}.`);
      load();
      onChanged?.();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const toggleStatus = async () => {
    if (!wf) return;
    const next = wf.status === "active" ? "paused" : "active";
    setBusy(true);
    try {
      await api.patch(`/workflows/${workflowId}`, { status: next });
      toast.success(next === "active" ? "Workflow activated." : "Workflow paused.");
      load();
      onChanged?.();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm("Delete this workflow? This cannot be undone.")) return;
    setBusy(true);
    try {
      await api.delete(`/workflows/${workflowId}`);
      toast.success("Workflow deleted.");
      onChanged?.();
      onClose();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Overlay onClose={onClose}>
      {loading || !wf ? (
        <div className="flex items-center justify-center py-24 text-[#64748B]">
          <Loader2 className="animate-spin" size={22} />
        </div>
      ) : (
        <>
          <div className="p-6 border-b border-[#E2E8F0]">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize ${STATUS_STYLES[wf.status]}`}>
                  {wf.status}
                </span>
                <h2 className="mt-2 text-lg font-bold text-[#0F172A]">{wf.name}</h2>
                <p className="text-sm text-[#64748B]">{wf.description || "No description."}</p>
              </div>
              <button onClick={onClose} className="p-2 rounded-lg hover:bg-[#F1F5F9]">
                <X size={18} className="text-[#64748B]" />
              </button>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <button
                onClick={runNow}
                disabled={running}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-60 text-white text-sm font-semibold"
              >
                {running ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
                {running ? "Running…" : "Run Now"}
              </button>
              <button
                onClick={toggleStatus}
                disabled={busy}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[#E2E8F0] bg-white hover:bg-[#F8FAFC] text-[#0F172A] text-sm font-semibold"
              >
                {wf.status === "active" ? <PauseCircle size={14} /> : <PlayCircle size={14} />}
                {wf.status === "active" ? "Pause" : "Activate"}
              </button>
              <button
                onClick={remove}
                disabled={busy}
                className="ml-auto inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[#FECACA] bg-white hover:bg-[#FEF2F2] text-[#B91C1C] text-sm font-semibold"
              >
                <Trash2 size={14} /> Delete
              </button>
            </div>
          </div>

          <div className="p-6 space-y-6 overflow-y-auto">
            {/* Steps */}
            <div>
              <h3 className="text-sm font-bold text-[#0F172A]">
                Flow ({wf.steps?.length || 0} {wf.steps?.length === 1 ? "step" : "steps"})
                {activeRun && (
                  <span className="ml-2 align-middle text-[11px] font-medium text-[#94A3B8]">
                    · showing latest run
                  </span>
                )}
              </h3>
              <div className="mt-2">
                <WorkflowCanvas
                  steps={wf.steps || []}
                  getMeta={STEP_META && ((t) => STEP_META[t] || STEP_TYPES[0])}
                  triggerLabel={
                    TRIGGERS.find((t) => t.value === wf.trigger_type)?.label || "Manual"
                  }
                  runStatusByOrder={
                    activeRun
                      ? Object.fromEntries(
                          (activeRun.run_steps || []).map((rs) => [
                            rs.order_index,
                            rs.status,
                          ])
                        )
                      : null
                  }
                />
              </div>
            </div>

            {/* Active run timeline */}
            {activeRun && (
              <div>
                <h3 className="text-sm font-bold text-[#0F172A]">Latest run</h3>
                {activeRun.status === "awaiting_approval" && (
                  <div className="mt-2 p-3 rounded-xl border border-[#FDE68A] bg-[#FFFBEB]">
                    <div className="flex items-center gap-2 text-[13px] font-semibold text-[#B45309]">
                      <ShieldCheck size={15} /> Awaiting your approval
                    </div>
                    <div className="mt-2 flex items-center gap-2">
                      <button
                        onClick={() => decide("approve")}
                        disabled={deciding}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#059669] hover:bg-[#047857] disabled:opacity-60 text-white text-[12px] font-semibold"
                      >
                        <ThumbsUp size={13} /> Approve
                      </button>
                      <button
                        onClick={() => decide("reject")}
                        disabled={deciding}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#FECACA] bg-white hover:bg-[#FEF2F2] disabled:opacity-60 text-[#B91C1C] text-[12px] font-semibold"
                      >
                        <ThumbsDown size={13} /> Reject
                      </button>
                    </div>
                  </div>
                )}
                <RunTimeline run={activeRun} />
              </div>
            )}

            {/* Run history */}
            <div>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-[#0F172A]">Run history</h3>
                <button onClick={load} className="text-[12px] text-[#2563EB] font-semibold inline-flex items-center gap-1">
                  <RefreshCw size={12} /> Refresh
                </button>
              </div>
              {runs.length === 0 ? (
                <p className="mt-2 text-sm text-[#94A3B8]">No runs yet.</p>
              ) : (
                <div className="mt-2 space-y-2">
                  {runs.map((r) => (
                    <RunRow key={r.id} run={r} onOpen={() => openRun(r.id, setActiveRun)} />
                  ))}
                </div>
              )}
            </div>

            {/* Version history */}
            {versions.length > 0 && (
              <div>
                <h3 className="text-sm font-bold text-[#0F172A] inline-flex items-center gap-1.5">
                  <History size={14} className="text-[#2563EB]" /> Version history
                </h3>
                <div className="mt-2 space-y-2">
                  {versions.map((v) => (
                    <div
                      key={v.id}
                      className="flex items-center gap-2.5 p-3 rounded-xl border border-[#E2E8F0] bg-white"
                    >
                      <span className="w-7 h-7 rounded-md bg-[#EFF6FF] text-[#2563EB] text-[11px] font-bold flex items-center justify-center">
                        v{v.version}
                      </span>
                      <span className="text-sm font-semibold text-[#0F172A] truncate">
                        {v.snapshot?.name || "Untitled"}
                      </span>
                      <span className="text-[11px] text-[#94A3B8]">
                        {(v.snapshot?.steps?.length ?? 0)} steps
                      </span>
                      <button
                        onClick={() => rollback(v.version)}
                        disabled={busy}
                        className="ml-auto inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-[#E2E8F0] bg-white hover:bg-[#F8FAFC] text-[12px] font-semibold text-[#334155]"
                      >
                        <RotateCcw size={12} /> Restore
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </Overlay>
  );
}

async function openRun(runId, setActiveRun) {
  try {
    const { data } = await api.get(`/workflows/runs/${runId}`);
    setActiveRun(data);
  } catch (e) {
    toast.error(formatApiError(e));
  }
}

function RunRow({ run, onOpen }) {
  const s = RUN_STATUS_STYLES[run.status] || RUN_STATUS_STYLES.queued;
  const Icon = s.icon;
  return (
    <button
      onClick={onOpen}
      className="w-full text-left flex items-center gap-2.5 p-3 rounded-xl border border-[#E2E8F0] bg-white hover:bg-[#F8FAFC]"
    >
      <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize inline-flex items-center gap-1 ${s.cls}`}>
        <Icon size={11} className={run.status === "running" ? "animate-spin" : ""} /> {run.status}
      </span>
      <span className="text-[12px] text-[#64748B]">
        {run.steps_completed}/{run.steps_total} steps
      </span>
      <span className="ml-auto text-[12px] text-[#94A3B8]">
        {new Date(run.created_at).toLocaleString()}
      </span>
    </button>
  );
}

function RunTimeline({ run }) {
  return (
    <div className="mt-2 rounded-xl border border-[#E2E8F0] bg-white divide-y divide-[#EEF2F7]">
      {(run.run_steps || []).map((rs) => {
        const meta = STEP_META[rs.type] || STEP_TYPES[0];
        const st = RUN_STATUS_STYLES[rs.status] || RUN_STATUS_STYLES.queued;
        const Icon = st.icon;
        const out = rs.output || {};
        const preview = out.text || out.value || out.message || out.context || "";
        return (
          <div key={rs.id} className="p-3">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize inline-flex items-center gap-1 ${st.cls}`}>
                <Icon size={11} className={rs.status === "running" ? "animate-spin" : ""} /> {rs.status}
              </span>
              <span className="text-sm font-semibold text-[#0F172A]">{rs.name}</span>
              <span className="ml-auto text-[11px] text-[#94A3B8]">{meta.label}</span>
            </div>
            {rs.error_message && (
              <p className="mt-1.5 text-[12px] text-[#B91C1C]">{rs.error_message}</p>
            )}
            {preview && (
              <p className="mt-1.5 text-[12px] text-[#475569] line-clamp-3 whitespace-pre-wrap">
                {String(preview)}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ───────────────────────── primitives ───────────────────────── */

function Overlay({ children, onClose }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex justify-end"
      onClick={onClose}
    >
      <motion.div
        initial={{ x: 40, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 40, opacity: 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 30 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl h-full bg-white shadow-2xl flex flex-col"
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-[12px] font-semibold text-[#334155] mb-1.5">{label}</span>
      {children}
    </label>
  );
}
