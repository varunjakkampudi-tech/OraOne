import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { listCallCampaigns } from "@/lib/api/calls";
import { listKnowledgeBases } from "@/lib/api/knowledge";
import { listLeads } from "@/lib/api/leads";
import { listMarketingCampaigns } from "@/lib/api/marketing";
import { listProjects } from "@/lib/api/studio";
import { loadStudioAgent } from "@/lib/studio-agent";
import { CHANNEL_API_KEY, channelStatus, CHECKING, type OsStatus } from "@/lib/studio-os";
import {
  getUseCase,
  isUseCaseId,
  nextUndoneStep,
  USE_CASES,
  useCaseProgress,
  type GettingStartedChannel,
  type GettingStartedStep,
  type StepStatus,
  type UseCaseId,
} from "@/lib/getting-started";
import { ProductGuide } from "./product-guide";
import { StudioFrame } from "./studio";
import { Notice, PageHeader } from "./studio-ui";
import { StatusPill } from "./studio-os";

// Getting started: pick the kind of business, then see the steps for it and which are done.
// A step reads "Done" only when an existing API shows it. A step no API reports reads
// "Not checked yet". Only the chosen use case is stored in this browser.

const STORAGE_KEY = "oraone.studio.getting-started.use-case";
const NONE: ReadonlySet<string> = new Set();
const CHANNEL_KEYS: readonly GettingStartedChannel[] = [
  "website-chat",
  "whatsapp",
  "instagram",
  "voice",
];

function readStoredUseCase(): UseCaseId | null {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return isUseCaseId(value) ? value : null;
  } catch {
    return null;
  }
}

function writeStoredUseCase(id: UseCaseId): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Storage is blocked (private window or cleared site data). The choice lasts for this visit.
  }
}

type Completion = {
  /** Source keys known to be done. */
  completed: ReadonlySet<string>;
  /** Source keys that were actually looked up, whether or not they are done. */
  checked: ReadonlySet<string>;
  /** Plain message when some lookup failed. Empty when all loaded. */
  error: string;
};

const PROJECT_CHECKS: readonly {
  source: string;
  run: (projectId: string) => Promise<boolean>;
}[] = [
  {
    source: "knowledge_added",
    run: async (id) => (await listKnowledgeBases(id)).items.some((base) => base.document_count > 0),
  },
  { source: "leads_imported", run: async (id) => (await listLeads(id)).length > 0 },
  {
    source: "campaign_created",
    run: async (id) => (await listMarketingCampaigns(id)).length > 0,
  },
  {
    source: "call_campaign_created",
    run: async (id) => (await listCallCampaigns(id)).length > 0,
  },
];

/** Reads what the existing APIs show. Anything a request could not show stays unchecked. */
async function loadCompletion(): Promise<Completion> {
  const completed = new Set<string>();
  const checked = new Set<string>();
  const problems: string[] = [];

  const [agentView, projectId] = await Promise.all([
    loadStudioAgent(true),
    listProjects().then(
      (response) => response.items[0]?.id ?? null,
      () => undefined,
    ),
  ]);
  if (agentView.error) problems.push(agentView.error);
  if (projectId === undefined) problems.push("Couldn't load your workspace.");

  const facts = agentView.facts;
  const hasAssistant = facts.state === "ready";
  const noAssistant = facts.state === "no-assistant";

  if (hasAssistant || noAssistant) checked.add("assistant_created");
  if (hasAssistant) completed.add("assistant_created");

  for (const key of CHANNEL_KEYS) {
    const source = `channel_connected:${key}`;
    if (noAssistant) {
      checked.add(source);
    } else if (hasAssistant && facts.channels !== null) {
      checked.add(source);
      const row = facts.channels.find((item) => item.channel === CHANNEL_API_KEY[key]);
      if (channelStatus(row).tone === "connected") completed.add(source);
    }
  }

  if (noAssistant) {
    checked.add("widget_installed");
  } else if (hasAssistant && facts.deploy !== null) {
    checked.add("widget_installed");
    if (facts.deploy.verification.installed) completed.add("widget_installed");
  }

  if (projectId === null) {
    // No workspace yet, so nothing else can exist.
    for (const check of PROJECT_CHECKS) checked.add(check.source);
  } else if (projectId !== undefined) {
    const results = await Promise.allSettled(PROJECT_CHECKS.map((check) => check.run(projectId)));
    results.forEach((result, index) => {
      const source = PROJECT_CHECKS[index]!.source;
      if (result.status === "fulfilled") {
        checked.add(source);
        if (result.value) completed.add(source);
      } else {
        problems.push("Some steps could not be checked.");
      }
    });
  }

  return {
    completed,
    checked,
    error: [...new Set(problems)].join(" "),
  };
}

function stepStatusView(status: StepStatus, loading: boolean): OsStatus {
  if (status === "done") return { label: "Done", tone: "connected" };
  if (status === "not_done") return { label: "Not done", tone: "not-connected" };
  return loading
    ? { label: CHECKING, tone: "checking" }
    : { label: "Not checked yet", tone: "checking" };
}

function StepLink({ step }: { step: GettingStartedStep }) {
  const label = `Open: ${step.title}`;
  const route = step.route;
  return (
    <Button asChild variant="outline" className="w-full sm:w-auto sm:justify-self-start">
      {route.kind === "channel" ? (
        <Link to="/studio/channels/$channel" params={{ channel: route.channel }} aria-label={label}>
          Open
        </Link>
      ) : (
        <Link to={route.to} aria-label={label}>
          Open
        </Link>
      )}
    </Button>
  );
}

export function GettingStartedPage() {
  const [useCaseId, setUseCaseId] = useState<UseCaseId>("small_business");
  const [completion, setCompletion] = useState<Completion | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const stored = readStoredUseCase();
    if (stored) setUseCaseId(stored);
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadCompletion().then((next) => {
      if (!cancelled) setCompletion(next);
    });
    return () => {
      cancelled = true;
    };
  }, [version]);

  const loading = completion === null;
  const useCase = getUseCase(useCaseId);
  const progress = useCaseProgress(
    useCase,
    completion?.completed ?? NONE,
    completion?.checked ?? NONE,
  );
  const next = nextUndoneStep(progress);

  const choose = (id: UseCaseId) => {
    setUseCaseId(id);
    writeStoredUseCase(id);
  };

  return (
    <StudioFrame>
      <PageHeader
        title="Getting started"
        description="Choose what your business does. We show the first steps for it and what is done so far."
      />

      <ProductGuide
        whatItDoes="This page lists the steps for the kind of business you run, in order. A step shows Done only when OraOne can see it is done."
        needs={[
          "A workspace, with at least one assistant created in AI Studio.",
          "Your business documents, if you want the assistant to answer questions.",
        ]}
        terms={[
          { term: "Done", meaning: "OraOne can see this step is finished." },
          { term: "Not done", meaning: "OraOne checked, and this step is not finished yet." },
          {
            term: "Not checked yet",
            meaning: "OraOne has no way to check this step, so it does not count it as done.",
          },
        ]}
      />

      {completion?.error && (
        <div className="mt-6">
          <Notice>{completion.error} Steps marked Not checked yet may be done already.</Notice>
        </div>
      )}

      <section aria-labelledby="use-case-heading" className="mt-8 grid gap-4">
        <h2 id="use-case-heading" className="text-xl font-semibold">
          What do you want to do?
        </h2>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {USE_CASES.map((item) => {
            const selected = item.id === useCaseId;
            return (
              <li key={item.id} className="min-w-0">
                <button
                  type="button"
                  aria-pressed={selected}
                  onClick={() => choose(item.id)}
                  className={`flex h-full w-full min-w-0 flex-col gap-2 rounded-xl border p-4 text-left transition-colors ${selected ? "border-primary bg-accent" : "border-border bg-card hover:bg-muted"}`}
                >
                  <span className="font-semibold break-words">{item.title}</span>
                  <span className="text-sm text-muted-foreground break-words">{item.forWho}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-labelledby="steps-heading" className="mt-8 grid gap-4">
        <div className="grid gap-2">
          <h2 id="steps-heading" className="text-xl font-semibold break-words">
            Steps for {useCase.title.toLowerCase()}
          </h2>
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {loading
              ? "Checking your progress…"
              : `${progress.doneCount} of ${progress.total} steps done (${progress.percent}%).`}
          </p>
          <div
            role="progressbar"
            aria-label={`Progress for ${useCase.title}`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={loading ? undefined : progress.percent}
            className="h-2 w-full overflow-hidden rounded-full bg-muted"
          >
            <div
              className="h-full rounded-full bg-primary transition-[width]"
              style={{ width: `${loading ? 0 : progress.percent}%` }}
            />
          </div>
          {!loading && next && (
            <p className="text-sm">
              <span className="font-medium">Next step:</span> {next.title}
            </p>
          )}
        </div>

        <ol className="grid gap-3">
          {progress.steps.map((item, index) => {
            const view = stepStatusView(item.status, loading);
            return (
              <li
                key={item.step.id}
                className="grid min-w-0 gap-3 rounded-xl border border-border bg-card p-4 sm:grid-cols-[1fr_auto] sm:items-start"
              >
                <div className="grid min-w-0 gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm text-muted-foreground">Step {index + 1}</span>
                    <StatusPill status={view} />
                  </div>
                  <h3 className="font-medium break-words">{item.step.title}</h3>
                  <p className="text-sm text-muted-foreground break-words">
                    {item.step.instruction}
                  </p>
                </div>
                <StepLink step={item.step} />
              </li>
            );
          })}
        </ol>
      </section>

      <section aria-labelledby="limits-heading" className="mt-8 grid gap-2">
        <h2 id="limits-heading" className="text-xl font-semibold">
          What OraOne will not do
        </h2>
        <p className="text-sm text-muted-foreground break-words">{useCase.limits}</p>
      </section>

      <div className="mt-8">
        <Button variant="outline" onClick={() => setVersion((current) => current + 1)}>
          Check progress again
        </Button>
      </div>
    </StudioFrame>
  );
}
