import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { nextStep, type ChecklistStep } from "@/lib/studio-os";

// Reusable setup checklist for one channel: what the user needs (by name), what the data shows
// is done, and what is next. Every page that sets up a channel uses this component.

export type ChannelChecklistProps = {
  /** Accounts and settings by name only. Never values, tokens or secrets. */
  needs: readonly string[];
  steps: readonly ChecklistStep[];
  /** True while the first request is still running; the done list then reads "Checking". */
  loading?: boolean;
  /** Optional place to continue, shown next to the next step. */
  nextLink?: { to: "/studio/assistants"; label: string };
};

const MARK: Record<"done" | "todo" | "unknown", { text: string; className: string }> = {
  done: { text: "Done", className: "is-active" },
  todo: { text: "Not done", className: "is-planned" },
  unknown: { text: "Not checked yet", className: "is-planned" },
};

function markOf(done: boolean | null) {
  if (done === true) return MARK.done;
  if (done === false) return MARK.todo;
  return MARK.unknown;
}

export function ChannelChecklist({
  needs,
  steps,
  loading = false,
  nextLink,
}: ChannelChecklistProps) {
  const next = nextStep(steps);
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <section
        aria-labelledby="checklist-needs"
        className="grid content-start gap-3 rounded-xl border border-border bg-card p-5"
      >
        <h2 id="checklist-needs" className="text-lg font-semibold">
          What you need
        </h2>
        <p className="text-sm text-muted-foreground">
          Have these ready. This page shows names only, never account details or keys.
        </p>
        <ul className="grid gap-2 text-sm">
          {needs.map((need) => (
            <li key={need} className="flex gap-2">
              <span aria-hidden="true" className="text-muted-foreground">
                •
              </span>
              <span>{need}</span>
            </li>
          ))}
        </ul>
      </section>

      <section
        aria-labelledby="checklist-done"
        className="grid content-start gap-3 rounded-xl border border-border bg-card p-5"
      >
        <h2 id="checklist-done" className="text-lg font-semibold">
          What is done
        </h2>
        {loading ? (
          <p role="status" className="text-sm text-muted-foreground">
            Checking your setup…
          </p>
        ) : (
          <ol className="grid gap-3">
            {steps.map((step) => {
              const mark = markOf(step.done);
              return (
                <li key={step.label} className="grid gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`status-pill ${mark.className}`}>{mark.text}</span>
                    <span className="font-medium">{step.label}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">{step.detail}</p>
                </li>
              );
            })}
          </ol>
        )}
      </section>

      <section
        aria-labelledby="checklist-next"
        className="grid gap-3 rounded-xl border border-border bg-card p-5 md:col-span-2"
      >
        <h2 id="checklist-next" className="text-lg font-semibold">
          What is next
        </h2>
        {loading ? (
          <p className="text-sm text-muted-foreground">Nothing yet. Checking your setup first.</p>
        ) : next ? (
          <p>{next.action}</p>
        ) : (
          <p>Everything on this list is done. Nothing is next.</p>
        )}
        {nextLink && !loading && next && (
          <Button asChild variant="outline" className="w-full sm:w-auto sm:justify-self-start">
            <Link to={nextLink.to}>{nextLink.label}</Link>
          </Button>
        )}
      </section>
    </div>
  );
}
