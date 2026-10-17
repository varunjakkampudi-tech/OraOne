import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/client";
import {
  createWorkflow,
  deleteWorkflow,
  getWorkflow,
  getWorkflowRun,
  listWorkflowRuns,
  listWorkflows,
  setWorkflowEnabled,
  type CreateWorkflowInput,
  type Workflow,
  type WorkflowDetail,
  type WorkflowRun,
  type WorkflowRunDetail,
  type WorkflowStep,
  type WorkflowStepInput,
} from "@/lib/api/workflows";
import {
  runStatusLabel,
  STEP_KIND_LABEL,
  stepLabel,
  stepReason,
  stepStatusLabel,
  triggerLabel,
  workflowStatusLabel,
} from "@/lib/workflow-status";
import { useWorkspaceId, when } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";
import { ProductGuide } from "./product-guide";
import { EmptyState, ErrorNotice, ListSkeleton, Loading, Notice, PageHeader } from "./studio-ui";

const FIELD_CLASS = "rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm";

type TriggerChoice = "manual" | "schedule" | "lead.created" | "message.received";

const TRIGGER_CHOICES: ReadonlyArray<{ value: TriggerChoice; label: string; hint: string }> = [
  {
    value: "manual",
    label: "Started by hand",
    hint: "Runs only when someone starts it. Starting a run is not available on this screen yet.",
  },
  {
    value: "schedule",
    label: "On a schedule",
    hint: "Runs again at the interval you choose.",
  },
  { value: "lead.created", label: "When a lead is created", hint: "Runs for each new lead." },
  {
    value: "message.received",
    label: "When a message is received",
    hint: "Runs for each new incoming message.",
  },
];

const SCHEDULE_OPTIONS = [
  { value: "hourly", label: "Every hour" },
  { value: "daily", label: "Every day" },
  { value: "weekly", label: "Every week" },
  { value: "monthly", label: "Every month" },
] as const;

const STEP_KINDS = ["wait", "send_message", "create_task", "condition"] as const;
type StepKind = (typeof STEP_KINDS)[number];

type WaitUnit = "minutes" | "hours" | "days";
const UNIT_SECONDS: Record<WaitUnit, number> = { minutes: 60, hours: 3600, days: 86400 };
const MAX_WAIT_SECONDS = 30 * 86400;

type ConditionOp = "contains" | "not_contains" | "eq" | "ne" | "gt" | "lt" | "nonempty";
const CONDITION_OPS: ReadonlyArray<{ value: ConditionOp; label: string; needsRight: boolean }> = [
  { value: "contains", label: "contains", needsRight: true },
  { value: "not_contains", label: "does not contain", needsRight: true },
  { value: "eq", label: "is equal to", needsRight: true },
  { value: "ne", label: "is not equal to", needsRight: true },
  { value: "gt", label: "is greater than", needsRight: true },
  { value: "lt", label: "is less than", needsRight: true },
  { value: "nonempty", label: "is not empty", needsRight: false },
];

// The four channels the send step can use (backend/app/services/workflow_senders.py).
const CHANNELS = [
  { value: "email", label: "Email" },
  { value: "sms", label: "Text message (SMS)" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "instagram", label: "Instagram" },
] as const;

// One flat draft per step so every field can be edited without type juggling.
type DraftStep = {
  id: number;
  kind: StepKind;
  amount: string;
  unit: WaitUnit;
  channel: string;
  message: string;
  title: string;
  description: string;
  left: string;
  op: ConditionOp;
  right: string;
};

let draftCounter = 0;

function newDraft(kind: StepKind): DraftStep {
  draftCounter += 1;
  return {
    id: draftCounter,
    kind,
    amount: "1",
    unit: "hours",
    channel: "",
    message: "",
    title: "",
    description: "",
    left: "",
    op: "contains",
    right: "",
  };
}

/** Turns one draft into the step the API accepts, or says what is missing. */
function buildStep(draft: DraftStep): { step: WorkflowStepInput } | { error: string } {
  const name = STEP_KIND_LABEL[draft.kind] ?? draft.kind;
  switch (draft.kind) {
    case "wait": {
      const amount = Number(draft.amount.trim());
      if (!Number.isInteger(amount) || amount < 1) {
        return { error: `${name}: enter a whole number of ${draft.unit}, 1 or more.` };
      }
      if (amount * UNIT_SECONDS[draft.unit] > MAX_WAIT_SECONDS) {
        return { error: `${name}: a wait can be at most 30 days.` };
      }
      return { step: { type: "wait", name, config: { [draft.unit]: amount } } };
    }
    case "send_message": {
      const message = draft.message.trim();
      if (!draft.channel) return { error: `${name}: choose a channel.` };
      if (!message) return { error: `${name}: write the message to send.` };
      return { step: { type: "send_message", name, config: { channel: draft.channel, message } } };
    }
    case "create_task": {
      const title = draft.title.trim();
      if (!title) return { error: `${name}: give the task a title.` };
      const description = draft.description.trim();
      return {
        step: {
          type: "create_task",
          name,
          config: description ? { title, description } : { title },
        },
      };
    }
    case "condition": {
      const left = draft.left.trim();
      const right = draft.right.trim();
      const needsRight = CONDITION_OPS.find((o) => o.value === draft.op)?.needsRight ?? true;
      if (!left) return { error: `${name}: enter the value to check.` };
      if (needsRight && !right) return { error: `${name}: enter the value to compare with.` };
      return {
        step: {
          type: "condition",
          name,
          config: { left, op: draft.op, right: needsRight ? right : "", stop_on_false: true },
        },
      };
    }
  }
}

function buildTrigger(
  choice: TriggerChoice,
  every: string,
): { trigger_type: string; trigger_config: Record<string, unknown> } | { error: string } {
  switch (choice) {
    case "manual":
      return { trigger_type: "manual", trigger_config: {} };
    case "schedule":
      return every
        ? { trigger_type: "schedule", trigger_config: { every } }
        : { error: "Choose how often the workflow runs on its schedule." };
    case "lead.created":
      return { trigger_type: "event", trigger_config: { event: "lead.created" } };
    case "message.received":
      return { trigger_type: "event", trigger_config: { event: "message.received" } };
  }
}

/**
 * Run steps do not carry their config, so the kind comes from the workflow step they were
 * copied from (matched by step_id). Falls back to the step name the author gave it.
 */
function runStepLabel(
  step: { step_id: string | null; type: string; name: string },
  definitionSteps: WorkflowStep[],
): string {
  const definition = definitionSteps.find((s) => s.id === step.step_id);
  return definition ? stepLabel(definition.type, definition.config) : step.name;
}

/** Keeps the summary fields of a detail response for the list. */
function toSummary(detail: WorkflowDetail): Workflow {
  const { steps: _steps, ...summary } = detail;
  return summary;
}

type PendingAction = "enable" | "delete" | null;

export function WorkflowsPage() {
  const workspace = useWorkspaceId();
  const [workflows, setWorkflows] = useState<Workflow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [listError, setListError] = useState("");
  const [listKey, setListKey] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [detailError, setDetailError] = useState("");
  const [runs, setRuns] = useState<WorkflowRun[] | null>(null);
  const [runsError, setRunsError] = useState("");
  const [detailKey, setDetailKey] = useState(0);

  const [openRunId, setOpenRunId] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<WorkflowRunDetail | null>(null);
  const [runDetailError, setRunDetailError] = useState("");
  const [runKey, setRunKey] = useState(0);

  const [pending, setPending] = useState<PendingAction>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");

  const [creating, setCreating] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [trigger, setTrigger] = useState<TriggerChoice>("manual");
  const [every, setEvery] = useState("");
  const [drafts, setDrafts] = useState<DraftStep[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Workflow list.
  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    setListError("");
    listWorkflows(workspace.id)
      .then((res) => {
        if (cancelled) return;
        setWorkflows(Array.isArray(res.items) ? res.items : []);
        setTotal(typeof res.total === "number" ? res.total : 0);
      })
      .catch((err) => {
        if (!cancelled) setListError(messageOf(err, "Couldn't load your workflows."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, listKey]);

  // Selected workflow and its run history.
  useEffect(() => {
    if (!workspace.id || !selectedId) return;
    let cancelled = false;
    setDetail(null);
    setDetailError("");
    setRuns(null);
    setRunsError("");
    setPending(null);
    setActionError("");
    setOpenRunId(null);
    getWorkflow(workspace.id, selectedId)
      .then((row) => {
        if (!cancelled) setDetail(row);
      })
      .catch((err) => {
        if (!cancelled) setDetailError(messageOf(err, "Couldn't load this workflow."));
      });
    listWorkflowRuns(workspace.id, selectedId)
      .then((res) => {
        if (!cancelled) setRuns(Array.isArray(res.items) ? res.items : []);
      })
      .catch((err) => {
        if (!cancelled) setRunsError(messageOf(err, "Couldn't load this workflow's runs."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, selectedId, detailKey]);

  // Steps of one open run.
  useEffect(() => {
    if (!workspace.id || !openRunId) return;
    let cancelled = false;
    setRunDetail(null);
    setRunDetailError("");
    getWorkflowRun(workspace.id, openRunId)
      .then((row) => {
        if (!cancelled) setRunDetail(row);
      })
      .catch((err) => {
        if (!cancelled) setRunDetailError(messageOf(err, "Couldn't load this run's steps."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, openRunId, runKey]);

  async function changeEnabled(enable: boolean) {
    if (!workspace.id || !detail) return;
    setBusy(true);
    setActionError("");
    try {
      const updated = await setWorkflowEnabled(workspace.id, detail.id, enable);
      setDetail(updated);
      setWorkflows(
        (rows) => rows?.map((w) => (w.id === updated.id ? toSummary(updated) : w)) ?? rows,
      );
      setPending(null);
    } catch (err) {
      setActionError(
        messageOf(
          err,
          enable
            ? "Couldn't turn this workflow on. Its status was not changed."
            : "Couldn't turn this workflow off. Its status was not changed.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function removeWorkflow() {
    if (!workspace.id || !detail) return;
    setBusy(true);
    setActionError("");
    try {
      await deleteWorkflow(workspace.id, detail.id);
      const removedId = detail.id;
      setWorkflows((rows) => rows?.filter((w) => w.id !== removedId) ?? rows);
      setTotal((count) => Math.max(0, count - 1));
      setSelectedId(null);
      setDetail(null);
      setPending(null);
    } catch (err) {
      setActionError(messageOf(err, "Couldn't delete this workflow. It was not deleted."));
    } finally {
      setBusy(false);
    }
  }

  function patchDraft(id: number, patch: Partial<DraftStep>) {
    setDrafts((list) => list.map((d) => (d.id === id ? { ...d, ...patch } : d)));
  }

  function addDraft(kind: StepKind) {
    setDrafts((list) => [...list, newDraft(kind)]);
  }

  function removeDraft(id: number) {
    setDrafts((list) => list.filter((d) => d.id !== id));
  }

  function resetForm() {
    setDraftName("");
    setTrigger("manual");
    setEvery("");
    setDrafts([]);
    setFormError("");
  }

  async function submitWorkflow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspace.id) return;
    const name = draftName.trim();
    const problems: string[] = [];
    if (!name) problems.push("Give the workflow a name.");
    if (drafts.length === 0) problems.push("Add at least one step.");

    const steps: WorkflowStepInput[] = [];
    for (const draft of drafts) {
      const built = buildStep(draft);
      if ("error" in built) problems.push(built.error);
      else steps.push(built.step);
    }

    const built = buildTrigger(trigger, every);
    if ("error" in built) problems.push(built.error);

    if (problems.length > 0 || "error" in built) {
      setFormError(problems.join(" "));
      return;
    }

    const input: CreateWorkflowInput = {
      name,
      trigger_type: built.trigger_type,
      trigger_config: built.trigger_config,
      steps,
    };
    setSubmitting(true);
    setFormError("");
    try {
      const created = await createWorkflow(workspace.id, input);
      setWorkflows((rows) => [toSummary(created), ...(rows ?? [])]);
      setTotal((count) => count + 1);
      resetForm();
      setCreating(false);
      setSelectedId(created.id);
    } catch (err) {
      setFormError(messageOf(err, "Couldn't create the workflow. Nothing was saved."));
    } finally {
      setSubmitting(false);
    }
  }

  // "Live" only when the workflow query returned data.
  const live = workflows !== null && listError === "";
  const selectedSummary = workflows?.find((w) => w.id === selectedId) ?? null;
  const detailIsOn = detail?.status === "active";
  const detailStatusKnown =
    detail !== null && ["active", "paused", "draft"].includes(detail.status);

  return (
    <StudioFrame>
      <PageHeader
        title="Workflows"
        description="Repeatable steps that run in order when their trigger fires."
        live={live}
        action={
          workspace.id ? (
            <Button
              variant="outline"
              aria-expanded={creating}
              onClick={() => {
                setCreating((open) => !open);
                setFormError("");
              }}
            >
              {creating ? "Close new workflow form" : "New workflow"}
            </Button>
          ) : undefined
        }
      />

      <ProductGuide
        whatItDoes="A workflow is a list of steps that run in order each time its trigger fires. Steps can wait, send a message, create a task or check a condition. Each run records what every step did and why."
        needs={[
          "A workspace. New workflows are saved as drafts and do nothing until you turn them on.",
          "Messaging set up for the channel a Send a message step uses. A step that cannot send records the reason.",
          "Messages still respect consent and calling hours: a contact who has not said yes is not messaged, and no message goes out between 21:00 and 08:00 in the contact's time zone.",
        ]}
        terms={[
          { term: "On", meaning: "The workflow runs when its trigger fires." },
          {
            term: "Off",
            meaning: "The workflow does not run. Its steps and run history are kept.",
          },
          { term: "Draft", meaning: "Saved but not turned on yet." },
          {
            term: "Skipped step",
            meaning:
              "The step chose not to act, for example because consent does not allow a message.",
          },
          { term: "Failed step", meaning: "The step could not do its work. The reason is shown." },
        ]}
        termsHeading="Key terms"
      />

      {workspace.error && (
        <div className="mt-6">
          <Notice kind="error">{workspace.error}</Notice>
        </div>
      )}
      {workspace.loaded && !workspace.id && !workspace.error && (
        <p className="mt-6 text-muted-foreground">
          Create a workspace to start building workflows.
        </p>
      )}

      {creating && workspace.id && (
        <form
          onSubmit={submitWorkflow}
          aria-label="New workflow"
          className="mt-6 grid gap-5 rounded-xl border border-border bg-card p-4"
        >
          <div className="grid gap-1 text-sm">
            <label htmlFor="workflow-name" className="font-medium">
              Workflow name
            </label>
            <input
              id="workflow-name"
              className={FIELD_CLASS}
              value={draftName}
              maxLength={200}
              onChange={(e) => setDraftName(e.target.value)}
              required
            />
          </div>

          <fieldset className="grid gap-2 text-sm">
            <legend className="font-medium">When it starts</legend>
            {TRIGGER_CHOICES.map((choice) => (
              <label
                key={choice.value}
                className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border border-border px-3 py-2"
              >
                <input
                  type="radio"
                  name="workflow-trigger"
                  value={choice.value}
                  checked={trigger === choice.value}
                  onChange={() => setTrigger(choice.value)}
                  className="mt-1 size-4 shrink-0"
                />
                <span className="grid gap-0.5">
                  <span className="font-medium">{choice.label}</span>
                  <span className="text-muted-foreground">{choice.hint}</span>
                </span>
              </label>
            ))}
            {trigger === "schedule" && (
              <div className="grid gap-1">
                <label htmlFor="workflow-schedule" className="font-medium">
                  How often
                </label>
                <select
                  id="workflow-schedule"
                  className={FIELD_CLASS}
                  value={every}
                  onChange={(e) => setEvery(e.target.value)}
                >
                  <option value="">Choose an interval</option>
                  {SCHEDULE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </fieldset>

          <fieldset className="grid gap-3 text-sm">
            <legend className="font-medium">Steps, in order</legend>
            {drafts.length === 0 && (
              <p className="text-muted-foreground">No steps yet. Add the first step below.</p>
            )}
            <ol className="grid gap-3">
              {drafts.map((draft, index) => {
                const label = STEP_KIND_LABEL[draft.kind] ?? draft.kind;
                const fieldId = (name: string) => `step-${draft.id}-${name}`;
                return (
                  <li key={draft.id} className="grid gap-3 rounded-lg border border-border p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium">
                        Step {index + 1}: {label}
                      </span>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        aria-label={`Remove step ${index + 1}, ${label}`}
                        onClick={() => removeDraft(draft.id)}
                      >
                        Remove
                      </Button>
                    </div>

                    {draft.kind === "wait" && (
                      <div className="flex flex-wrap items-end gap-3">
                        <div className="grid gap-1">
                          <label htmlFor={fieldId("amount")} className="font-medium">
                            Wait for
                          </label>
                          <input
                            id={fieldId("amount")}
                            inputMode="numeric"
                            className={`${FIELD_CLASS} w-24`}
                            value={draft.amount}
                            onChange={(e) => patchDraft(draft.id, { amount: e.target.value })}
                          />
                        </div>
                        <div className="grid gap-1">
                          <label htmlFor={fieldId("unit")} className="font-medium">
                            Unit
                          </label>
                          <select
                            id={fieldId("unit")}
                            className={FIELD_CLASS}
                            value={draft.unit}
                            onChange={(e) =>
                              patchDraft(draft.id, { unit: e.target.value as WaitUnit })
                            }
                          >
                            <option value="minutes">minutes</option>
                            <option value="hours">hours</option>
                            <option value="days">days</option>
                          </select>
                        </div>
                      </div>
                    )}

                    {draft.kind === "send_message" && (
                      <>
                        <div className="grid gap-1">
                          <label htmlFor={fieldId("channel")} className="font-medium">
                            Channel
                          </label>
                          <select
                            id={fieldId("channel")}
                            className={FIELD_CLASS}
                            value={draft.channel}
                            onChange={(e) => patchDraft(draft.id, { channel: e.target.value })}
                          >
                            <option value="">Choose a channel</option>
                            {CHANNELS.map((channel) => (
                              <option key={channel.value} value={channel.value}>
                                {channel.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        <div className="grid gap-1">
                          <label htmlFor={fieldId("message")} className="font-medium">
                            Message
                          </label>
                          <textarea
                            id={fieldId("message")}
                            rows={3}
                            maxLength={2000}
                            className={FIELD_CLASS}
                            value={draft.message}
                            onChange={(e) => patchDraft(draft.id, { message: e.target.value })}
                          />
                          <span className="text-muted-foreground">
                            Use {"{{lead.name}}"} to insert the lead's name.
                          </span>
                        </div>
                      </>
                    )}

                    {draft.kind === "create_task" && (
                      <>
                        <div className="grid gap-1">
                          <label htmlFor={fieldId("title")} className="font-medium">
                            Task title
                          </label>
                          <input
                            id={fieldId("title")}
                            className={FIELD_CLASS}
                            value={draft.title}
                            maxLength={200}
                            onChange={(e) => patchDraft(draft.id, { title: e.target.value })}
                          />
                        </div>
                        <div className="grid gap-1">
                          <label htmlFor={fieldId("description")} className="font-medium">
                            Description (optional)
                          </label>
                          <textarea
                            id={fieldId("description")}
                            rows={2}
                            className={FIELD_CLASS}
                            value={draft.description}
                            onChange={(e) => patchDraft(draft.id, { description: e.target.value })}
                          />
                        </div>
                      </>
                    )}

                    {draft.kind === "condition" && (
                      <div className="grid gap-3 sm:grid-cols-3">
                        <div className="grid gap-1">
                          <label htmlFor={fieldId("left")} className="font-medium">
                            Value to check
                          </label>
                          <input
                            id={fieldId("left")}
                            className={FIELD_CLASS}
                            value={draft.left}
                            onChange={(e) => patchDraft(draft.id, { left: e.target.value })}
                          />
                        </div>
                        <div className="grid gap-1">
                          <label htmlFor={fieldId("op")} className="font-medium">
                            Condition
                          </label>
                          <select
                            id={fieldId("op")}
                            className={FIELD_CLASS}
                            value={draft.op}
                            onChange={(e) =>
                              patchDraft(draft.id, { op: e.target.value as ConditionOp })
                            }
                          >
                            {CONDITION_OPS.map((op) => (
                              <option key={op.value} value={op.value}>
                                {op.label}
                              </option>
                            ))}
                          </select>
                        </div>
                        {CONDITION_OPS.find((o) => o.value === draft.op)?.needsRight !== false && (
                          <div className="grid gap-1">
                            <label htmlFor={fieldId("right")} className="font-medium">
                              Compared with
                            </label>
                            <input
                              id={fieldId("right")}
                              className={FIELD_CLASS}
                              value={draft.right}
                              onChange={(e) => patchDraft(draft.id, { right: e.target.value })}
                            />
                          </div>
                        )}
                        <p className="text-muted-foreground sm:col-span-3">
                          If the condition is not met, the run stops here and the remaining steps do
                          not run.
                        </p>
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Add a step">
              {STEP_KINDS.map((kind) => (
                <Button
                  key={kind}
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => addDraft(kind)}
                >
                  {STEP_KIND_LABEL[kind]}
                </Button>
              ))}
            </div>
          </fieldset>

          {formError && <ErrorNotice message={formError} />}
          <p className="text-muted-foreground">
            New workflows are saved as drafts. Turn one on from its page when you are ready.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving…" : "Create workflow"}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={submitting}
              onClick={() => {
                setCreating(false);
                resetForm();
              }}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}

      {listError && (
        <div className="mt-4">
          <ErrorNotice
            message={listError}
            onRetry={workspace.id ? () => setListKey((k) => k + 1) : undefined}
          />
        </div>
      )}

      <div className="mt-8 grid gap-8">
        <section aria-labelledby="workflows-heading">
          <h2 id="workflows-heading" className="text-lg font-semibold">
            Your workflows
          </h2>
          <div className="mt-3">
            {workflows === null && !listError && workspace.id ? (
              <ListSkeleton rows={3} label="Loading workflows…" />
            ) : workflows && workflows.length === 0 ? (
              <EmptyState
                title="No workflows yet."
                action={
                  workspace.id && !creating ? (
                    <Button variant="outline" onClick={() => setCreating(true)}>
                      New workflow
                    </Button>
                  ) : undefined
                }
              >
                A workflow chains steps such as waiting, sending a message or creating a task.
              </EmptyState>
            ) : workflows ? (
              <>
                <ul className="grid gap-2" aria-label="Workflows">
                  {workflows.map((workflow) => {
                    const selected = workflow.id === selectedId;
                    return (
                      <li key={workflow.id}>
                        <button
                          type="button"
                          aria-pressed={selected}
                          onClick={() => setSelectedId(workflow.id)}
                          className={`flex w-full items-center justify-between gap-3 rounded-xl border px-4 py-3 text-left transition-colors hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${selected ? "border-primary bg-accent" : "border-border bg-card"}`}
                        >
                          <span className="min-w-0">
                            <span className="block truncate font-medium">{workflow.name}</span>
                            <span className="mt-1 block text-sm text-muted-foreground">
                              {triggerLabel(workflow.trigger_type, workflow.trigger_config)}
                              {" · "}
                              {workflow.last_run_at
                                ? `Last run ${when(workflow.last_run_at)}`
                                : "Never run"}
                            </span>
                          </span>
                          <span className="shrink-0 rounded-full bg-muted px-2.5 py-0.5 text-sm">
                            {workflowStatusLabel(workflow.status)}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
                {total > workflows.length && (
                  <p className="mt-3 text-sm text-muted-foreground">
                    Showing the newest {workflows.length} of {total} workflows.
                  </p>
                )}
              </>
            ) : null}
          </div>
        </section>

        {selectedId && (
          <section aria-labelledby="workflow-detail-heading" className="grid gap-5">
            {detailError && (
              <ErrorNotice message={detailError} onRetry={() => setDetailKey((k) => k + 1)} />
            )}
            {!detail && !detailError && <Loading label="Loading workflow…" />}

            {detail && (
              <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 id="workflow-detail-heading" className="break-words text-lg font-semibold">
                      {detail.name || selectedSummary?.name || "Workflow"}
                    </h2>
                    <p className="mt-1 text-muted-foreground">
                      {triggerLabel(detail.trigger_type, detail.trigger_config)}
                    </p>
                  </div>
                  <span className="rounded-full bg-muted px-2.5 py-0.5 text-sm">
                    {workflowStatusLabel(detail.status)}
                  </span>
                </div>

                <dl className="grid grid-cols-3 gap-3 text-sm" aria-label="Workflow totals">
                  <div className="rounded-lg border border-border bg-card p-3">
                    <dt className="text-muted-foreground">Runs</dt>
                    <dd className="mt-1 text-lg font-semibold">{detail.run_count}</dd>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-3">
                    <dt className="text-muted-foreground">Successful</dt>
                    <dd className="mt-1 text-lg font-semibold">{detail.success_count}</dd>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-3">
                    <dt className="text-muted-foreground">Last run</dt>
                    <dd className="mt-1 text-sm font-medium">
                      {detail.last_run_at ? when(detail.last_run_at) : "Never"}
                    </dd>
                  </div>
                </dl>

                <div>
                  <h3 className="text-base font-semibold">Steps</h3>
                  {detail.steps.length === 0 ? (
                    <p className="mt-2 text-sm text-muted-foreground">
                      This workflow has no steps.
                    </p>
                  ) : (
                    <ol className="mt-3 grid gap-2 text-sm">
                      {detail.steps.map((step, index) => (
                        <li
                          key={step.id}
                          className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card px-3 py-2"
                        >
                          <span className="text-muted-foreground">{index + 1}.</span>
                          <span className="font-medium">{stepLabel(step.type, step.config)}</span>
                        </li>
                      ))}
                    </ol>
                  )}
                </div>

                <div className="grid gap-3 rounded-xl border border-border bg-card p-4 text-sm">
                  <h3 className="text-base font-semibold">Turn on or off</h3>
                  {!detailStatusKnown && (
                    <Notice>This workflow's status is not one this screen can show.</Notice>
                  )}
                  {detailStatusKnown && detailIsOn && pending === null && (
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="text-muted-foreground">
                        On. It runs when its trigger fires.
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => changeEnabled(false)}
                      >
                        {busy ? "Saving…" : "Turn off"}
                      </Button>
                    </div>
                  )}
                  {detailStatusKnown && !detailIsOn && pending === null && (
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="text-muted-foreground">
                        {detail.status === "draft"
                          ? "Draft. It does not run until you turn it on."
                          : "Off. It does not run until you turn it on."}
                      </span>
                      <Button size="sm" disabled={busy} onClick={() => setPending("enable")}>
                        Turn on
                      </Button>
                    </div>
                  )}
                  {pending === "enable" && (
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="w-full text-muted-foreground sm:w-auto">
                        Turn on this workflow? Once it is on, it runs with its trigger:{" "}
                        {triggerLabel(detail.trigger_type, detail.trigger_config)}. Messages still
                        respect consent and calling hours.
                      </span>
                      <Button size="sm" disabled={busy} onClick={() => changeEnabled(true)}>
                        {busy ? "Saving…" : "Confirm turn on"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => setPending(null)}
                      >
                        Cancel
                      </Button>
                    </div>
                  )}
                  {actionError && pending !== "delete" && <ErrorNotice message={actionError} />}
                </div>

                <div className="grid gap-3 rounded-xl border border-border bg-card p-4 text-sm">
                  <h3 className="text-base font-semibold">Delete</h3>
                  {pending !== "delete" ? (
                    <div>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => setPending("delete")}
                      >
                        Delete workflow
                      </Button>
                    </div>
                  ) : (
                    <div className="grid gap-3">
                      <p className="text-muted-foreground">
                        Delete “{detail.name}”? It stops running and is removed from this list. Its
                        run history is no longer shown in OraOne, and this cannot be undone.
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="destructive"
                          size="sm"
                          disabled={busy}
                          onClick={removeWorkflow}
                        >
                          {busy ? "Deleting…" : "Confirm delete"}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy}
                          onClick={() => setPending(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                      {actionError && <ErrorNotice message={actionError} />}
                    </div>
                  )}
                </div>

                <div>
                  <h3 className="text-base font-semibold">Run history</h3>
                  <div className="mt-3">
                    {runsError && (
                      <ErrorNotice message={runsError} onRetry={() => setDetailKey((k) => k + 1)} />
                    )}
                    {!runs && !runsError && <ListSkeleton rows={2} label="Loading runs…" />}
                    {runs && runs.length === 0 && (
                      <EmptyState title="No runs yet.">
                        Each time this workflow runs, the run and what each step did appear here.
                      </EmptyState>
                    )}
                    {runs && runs.length > 0 && (
                      <ul className="grid gap-2" aria-label="Workflow runs">
                        {runs.map((run) => {
                          const open = openRunId === run.id;
                          return (
                            <li
                              key={run.id}
                              className="grid gap-2 rounded-xl border border-border bg-card px-4 py-3 text-sm"
                            >
                              <button
                                type="button"
                                aria-expanded={open}
                                onClick={() => setOpenRunId(open ? null : run.id)}
                                className="flex w-full flex-wrap items-center justify-between gap-2 rounded-md text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                              >
                                <span className="font-medium">{runStatusLabel(run.status)}</span>
                                <time className="text-muted-foreground" dateTime={run.created_at}>
                                  {when(run.started_at ?? run.created_at)}
                                </time>
                              </button>
                              <p className="text-muted-foreground">
                                {run.steps_completed} of {run.steps_total} steps completed
                              </p>
                              {run.error_message && (
                                <p className="text-destructive">{run.error_message}</p>
                              )}

                              {open && (
                                <div className="grid gap-2 border-t border-border pt-3">
                                  {runDetailError && (
                                    <ErrorNotice
                                      message={runDetailError}
                                      onRetry={() => setRunKey((k) => k + 1)}
                                    />
                                  )}
                                  {!runDetailError &&
                                    (runDetail === null || runDetail.id !== run.id) && (
                                      <Loading label="Loading steps…" />
                                    )}
                                  {runDetail && runDetail.id === run.id && (
                                    <ol className="grid gap-2" aria-label="Steps in this run">
                                      {runDetail.run_steps.map((step) => (
                                        <li
                                          key={step.id}
                                          className="grid gap-1 rounded-lg bg-muted px-3 py-2"
                                        >
                                          <div className="flex flex-wrap items-center justify-between gap-2">
                                            <span className="font-medium">
                                              {runStepLabel(step, detail.steps)}
                                            </span>
                                            <span className="text-muted-foreground">
                                              {stepStatusLabel(step.status)}
                                            </span>
                                          </div>
                                          <p className="text-muted-foreground">
                                            Reason: {stepReason(step)}
                                          </p>
                                        </li>
                                      ))}
                                      {runDetail.run_steps.length === 0 && (
                                        <li className="text-muted-foreground">
                                          No steps were recorded for this run.
                                        </li>
                                      )}
                                    </ol>
                                  )}
                                </div>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </div>
                </div>
              </>
            )}
          </section>
        )}
      </div>
    </StudioFrame>
  );
}
