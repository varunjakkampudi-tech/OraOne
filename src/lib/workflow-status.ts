// Plain-language labels for workflow data. Each map covers only the values the API stores;
// anything else is shown as "Unknown" rather than guessed at.

const WORKFLOW_STATUS_LABEL: Record<string, string> = {
  active: "On",
  paused: "Off",
  draft: "Draft",
};

const RUN_STATUS_LABEL: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  awaiting_approval: "Waiting for approval",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

const STEP_STATUS_LABEL: Record<string, string> = {
  pending: "Not started",
  running: "Running",
  awaiting_approval: "Waiting for approval",
  completed: "Completed",
  failed: "Failed",
  skipped: "Skipped",
};

/** The step kinds the New workflow form offers, keyed by the type the API accepts on create. */
export const STEP_KIND_LABEL: Record<string, string> = {
  wait: "Wait",
  send_message: "Send a message",
  create_task: "Create a task",
  condition: "Check a condition",
};

function labelFrom(map: Record<string, string>, value: string): string {
  return map[value] ?? "Unknown";
}

export function workflowStatusLabel(status: string): string {
  return labelFrom(WORKFLOW_STATUS_LABEL, status);
}

export function runStatusLabel(status: string): string {
  return labelFrom(RUN_STATUS_LABEL, status);
}

export function stepStatusLabel(status: string): string {
  return labelFrom(STEP_STATUS_LABEL, status);
}

/**
 * The API stores some steps as an existing step type plus config.action:
 * wait is stored as "delay", send_message as "notification" and create_task as "transform".
 * This maps the stored pair back to the kind the author chose.
 */
export function stepKind(type: string, config: Record<string, unknown>): string {
  const action = typeof config["action"] === "string" ? config["action"] : null;
  if (type === "delay") return "wait";
  if (type === "notification" && action === "send_message") return "send_message";
  if (type === "transform" && action === "create_task") return "create_task";
  return type;
}

export function stepLabel(type: string, config: Record<string, unknown>): string {
  const kind = stepKind(type, config);
  return STEP_KIND_LABEL[kind] ?? "Other step";
}

/**
 * Why a step did what it did, as the API records it. Prefers the step's own error message,
 * then the reason written into its output. Never invents a reason.
 */
export function stepReason(step: {
  error_message: string | null;
  output: Record<string, unknown>;
}): string {
  if (step.error_message) return step.error_message;
  const reason = step.output["reason"];
  if (typeof reason === "string" && reason.trim()) return reason;
  return "No reason was recorded.";
}

const TRIGGER_EVERY_LABEL: Record<string, string> = {
  hourly: "every hour",
  daily: "every day",
  weekly: "every week",
  monthly: "every month",
};

export function triggerLabel(triggerType: string, config: Record<string, unknown>): string {
  if (triggerType === "manual") return "Started by hand";
  if (triggerType === "schedule") {
    const every = typeof config["every"] === "string" ? config["every"] : "";
    const phrase = TRIGGER_EVERY_LABEL[every];
    return phrase ? `Runs ${phrase}` : "Runs on a schedule";
  }
  if (triggerType === "event") {
    const event = config["event"];
    if (event === "lead.created") return "When a lead is created";
    if (event === "message.received") return "When a message is received";
  }
  return "Unknown trigger";
}
