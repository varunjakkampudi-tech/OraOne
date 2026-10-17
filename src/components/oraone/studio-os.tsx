import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { useStudioAgent } from "@/lib/studio-agent";
import {
  areaAction,
  areaStatus,
  OS_AREAS,
  type ChannelLoad,
  type OsArea,
  type OsStatus,
} from "@/lib/studio-os";
import { StudioFrame } from "./studio";
import { ErrorNotice, PageHeader } from "./studio-ui";

// OraOne OS hub: one card per product area, with its real status and one primary action.
// Channel status is read for the first assistant in the first workspace. Nothing is written here.

const TONE_CLASS: Record<OsStatus["tone"], string> = {
  connected: "is-active",
  paused: "is-planned",
  available: "is-demo",
  planned: "is-planned",
  "not-connected": "is-planned",
  checking: "is-planned",
};

export function StatusPill({ status, className = "" }: { status: OsStatus; className?: string }) {
  return (
    <span className={`status-pill ${TONE_CLASS[status.tone]} ${className}`.trim()}>
      {status.label}
    </span>
  );
}

function AreaCard({ area, load }: { area: OsArea; load: ChannelLoad }) {
  const status = areaStatus(area, load);
  const action = areaAction(area, status);
  const headingId = `os-area-${area.id}`;
  return (
    <article
      aria-labelledby={headingId}
      className="flex h-full flex-col gap-3 rounded-xl border border-border bg-card p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 id={headingId} className="min-w-0 text-base font-semibold">
          {area.name}
        </h3>
        <StatusPill status={status} />
      </div>
      <p className="flex-1 text-sm text-muted-foreground">{area.summary}</p>
      {action.kind === "channel" && (
        <Button
          asChild
          variant={action.label === "Open" ? "outline" : "default"}
          className="w-full sm:w-auto sm:justify-self-start"
        >
          <Link
            to="/studio/channels/$channel"
            params={{ channel: action.channel }}
            aria-label={`${action.label} ${area.name}`}
          >
            {action.label}
          </Link>
        </Button>
      )}
      {action.kind === "page" && (
        <Button asChild variant="outline" className="w-full sm:w-auto sm:justify-self-start">
          <Link to={action.to} aria-label={`${action.label} ${area.name}`}>
            {action.label}
          </Link>
        </Button>
      )}
      {action.kind === "none" && (
        <div className="grid gap-1">
          <Button
            disabled
            variant="outline"
            className="w-full sm:w-auto sm:justify-self-start"
            aria-label={`${area.name}: screen not available yet`}
          >
            Set up
          </Button>
          <p className="text-xs text-muted-foreground">
            The {area.name} screen is not available yet.
          </p>
        </div>
      )}
    </article>
  );
}

export function StudioOsHub() {
  const view = useStudioAgent();
  return (
    <StudioFrame>
      <PageHeader
        title="OraOne OS"
        description="One place for every channel, conversation and campaign. Each area shows its real status."
      />
      <p className="mt-2 text-sm text-muted-foreground">
        {view.agentName
          ? `Channel status is for ${view.agentName}, the first assistant in your workspace.`
          : "Channel status appears here once you create an assistant."}
      </p>
      {view.error && (
        <div className="mt-4">
          <ErrorNotice message={view.error} />
        </div>
      )}
      <section aria-labelledby="os-areas-heading" className="mt-8 grid gap-4">
        <h2 id="os-areas-heading" className="text-xl font-semibold">
          Product areas
        </h2>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {OS_AREAS.map((area) => (
            <li key={area.id}>
              <AreaCard area={area} load={view.channels} />
            </li>
          ))}
        </ul>
      </section>
    </StudioFrame>
  );
}
