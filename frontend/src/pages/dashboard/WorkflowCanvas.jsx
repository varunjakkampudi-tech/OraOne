import React from "react";
import {
  Zap,
  Flag,
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  ShieldCheck,
  CircleSlash,
} from "lucide-react";

/**
 * WorkflowCanvas — a dependency-free, n8n/Langflow-style visual graph of a
 * workflow's steps. Steps execute top-to-bottom, so the canvas lays nodes out
 * in a vertical flow connected by SVG edges, with a Trigger start node and a
 * Done end node. When `runStatusByOrder` is supplied each node is tinted with
 * its live run-step status so operators can watch a run progress visually.
 *
 * Props:
 *   steps              [{ type, name, id? }]
 *   getMeta(type)      -> { label, icon }    (passed from Workflows STEP_META)
 *   triggerLabel       string                (e.g. "Manual", "Schedule")
 *   runStatusByOrder   { [orderIndex]: RunStepStatus }  (optional overlay)
 *   selectedIndex      number | null         (highlights one node, optional)
 *   onSelectStep(i)    callback              (optional — makes nodes clickable)
 */

/* Group each step type into a visual family so the canvas reads at a glance. */
const TYPE_FAMILY = {
  ai_prompt: "ai",
  ai_classify: "ai",
  ai_extract: "ai",
  ai_summarize: "ai",
  ai_sentiment: "ai",
  ai_translate: "ai",
  kb_query: "data",
  agent_run: "data",
  transform: "logic",
  condition: "logic",
  approval: "approval",
  notification: "io",
  delay: "io",
  webhook: "io",
};

const FAMILY_STYLES = {
  ai: { ring: "#C7D2FE", accent: "#4F46E5", chip: "#EEF2FF", icon: "#4F46E5" },
  data: { ring: "#BFDBFE", accent: "#2563EB", chip: "#EFF6FF", icon: "#2563EB" },
  logic: { ring: "#FDE68A", accent: "#D97706", chip: "#FFFBEB", icon: "#D97706" },
  approval: { ring: "#FBCFE8", accent: "#DB2777", chip: "#FDF2F8", icon: "#DB2777" },
  io: { ring: "#CBD5E1", accent: "#475569", chip: "#F1F5F9", icon: "#475569" },
  default: { ring: "#E2E8F0", accent: "#64748B", chip: "#F8FAFC", icon: "#64748B" },
};

const RUN_STATUS = {
  pending: { border: "#E2E8F0", badge: "#F1F5F9", text: "#64748B", icon: Clock, label: "Pending", spin: false },
  running: { border: "#2563EB", badge: "#EFF6FF", text: "#2563EB", icon: Loader2, label: "Running", spin: true },
  awaiting_approval: { border: "#D97706", badge: "#FFFBEB", text: "#B45309", icon: ShieldCheck, label: "Awaiting approval", spin: false },
  completed: { border: "#059669", badge: "#ECFDF5", text: "#047857", icon: CheckCircle2, label: "Completed", spin: false },
  failed: { border: "#DC2626", badge: "#FEF2F2", text: "#B91C1C", icon: XCircle, label: "Failed", spin: false },
  skipped: { border: "#CBD5E1", badge: "#F1F5F9", text: "#94A3B8", icon: CircleSlash, label: "Skipped", spin: false },
};

function familyFor(type) {
  return FAMILY_STYLES[TYPE_FAMILY[type]] || FAMILY_STYLES.default;
}

/* The downward connector between two nodes, with a tiny arrowhead. */
function Connector({ active }) {
  return (
    <div className="flex justify-center" aria-hidden="true">
      <svg width="24" height="34" viewBox="0 0 24 34" className="overflow-visible">
        <line
          x1="12"
          y1="0"
          x2="12"
          y2="26"
          stroke={active ? "#2563EB" : "#CBD5E1"}
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path
          d="M7 24 L12 31 L17 24"
          fill="none"
          stroke={active ? "#2563EB" : "#CBD5E1"}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function TerminalNode({ kind, label }) {
  const isStart = kind === "start";
  const Icon = isStart ? Zap : Flag;
  return (
    <div className="flex justify-center">
      <div
        className="inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-[12px] font-semibold"
        style={{
          borderColor: isStart ? "#C7D2FE" : "#BBF7D0",
          backgroundColor: isStart ? "#EEF2FF" : "#ECFDF5",
          color: isStart ? "#4338CA" : "#047857",
        }}
        data-testid={isStart ? "canvas-trigger-node" : "canvas-end-node"}
      >
        <Icon size={13} />
        {label}
      </div>
    </div>
  );
}

export default function WorkflowCanvas({
  steps = [],
  getMeta,
  triggerLabel = "Manual",
  runStatusByOrder = null,
  selectedIndex = null,
  onSelectStep = null,
}) {
  const clickable = typeof onSelectStep === "function";

  if (!steps.length) {
    return (
      <div
        className="rounded-2xl border border-dashed border-[#CBD5E1] bg-[#F8FAFC] px-6 py-10 text-center"
        data-testid="workflow-canvas-empty"
      >
        <p className="text-sm font-semibold text-[#475569]">No steps yet</p>
        <p className="mt-1 text-[12px] text-[#94A3B8]">
          Add steps below — they'll appear here as connected nodes.
        </p>
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl border border-[#E2E8F0] bg-[#FAFBFF] p-4 [background-image:radial-gradient(#E2E8F0_1px,transparent_1px)] [background-size:18px_18px]"
      data-testid="workflow-canvas"
    >
      <div className="mx-auto max-w-md">
        <TerminalNode kind="start" label={`Trigger · ${triggerLabel}`} />
        <Connector active={Boolean(runStatusByOrder)} />

        {steps.map((step, i) => {
          const meta = (getMeta && getMeta(step.type)) || { label: step.type, icon: Zap };
          const Icon = meta.icon || Zap;
          const fam = familyFor(step.type);
          const status = runStatusByOrder ? runStatusByOrder[i] : null;
          const rs = status ? RUN_STATUS[status] : null;
          const selected = selectedIndex === i;
          const branch =
            step.type === "condition"
              ? "Stops the run if the predicate is false"
              : step.type === "approval"
              ? "Pauses until a human approves"
              : null;

          const NodeTag = clickable ? "button" : "div";

          return (
            <div key={step.id || i}>
              <div className="flex items-stretch justify-center gap-2">
                <NodeTag
                  type={clickable ? "button" : undefined}
                  onClick={clickable ? () => onSelectStep(i) : undefined}
                  data-testid={`canvas-node-${i}`}
                  className={`group relative w-full rounded-xl border bg-white px-3 py-2.5 text-left shadow-sm transition ${
                    clickable ? "cursor-pointer hover:shadow-md" : ""
                  }`}
                  style={{
                    borderColor: rs ? rs.border : selected ? fam.accent : fam.ring,
                    boxShadow: selected ? `0 0 0 2px ${fam.accent}33` : undefined,
                  }}
                >
                  <span
                    className="absolute left-0 top-2 bottom-2 w-1 rounded-full"
                    style={{ backgroundColor: fam.accent }}
                    aria-hidden="true"
                  />
                  <div className="flex items-center gap-2.5 pl-1.5">
                    <span
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[11px] font-bold"
                      style={{ backgroundColor: fam.chip, color: fam.accent }}
                    >
                      {i + 1}
                    </span>
                    <Icon size={15} style={{ color: fam.icon }} className="shrink-0" />
                    <span className="min-w-0 flex-1 truncate text-sm font-semibold text-[#0F172A]">
                      {step.name || meta.label}
                    </span>
                    {rs ? (
                      <span
                        className="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                        style={{ backgroundColor: rs.badge, color: rs.text }}
                        data-testid={`canvas-node-status-${i}`}
                      >
                        <rs.icon size={10} className={rs.spin ? "animate-spin" : ""} />
                        {rs.label}
                      </span>
                    ) : (
                      <span
                        className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                        style={{ backgroundColor: fam.chip, color: fam.accent }}
                      >
                        {meta.label}
                      </span>
                    )}
                  </div>
                  {branch && (
                    <p className="mt-1.5 pl-1.5 text-[11px] italic text-[#94A3B8]">
                      ⤷ {branch}
                    </p>
                  )}
                </NodeTag>
              </div>
              <Connector active={Boolean(rs && (rs.label === "Completed"))} />
            </div>
          );
        })}

        <TerminalNode kind="end" label="Done" />
      </div>
    </div>
  );
}
