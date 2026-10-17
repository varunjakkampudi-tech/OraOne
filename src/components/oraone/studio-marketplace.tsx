import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/client";
import {
  installMarketplaceListing,
  listMarketplaceListings,
  type MarketplaceListing,
  type MarketplaceRequirement,
} from "@/lib/api/marketplace";
import { useWorkspaceId } from "@/lib/studio-helpers";
import { LISTING_STATUS_LABEL, listingStatus, type ListingStatus } from "@/lib/marketplace-status";
import { StudioFrame } from "./studio";
import { EmptyState, ErrorNotice, ListSkeleton, Loading, PageHeader } from "./studio-ui";

// Marketplace under /studio. Templates come from the server catalogue; the badge and the
// Install button only reflect what the server says about each listing.

const GROUPS = [
  {
    category: "agent_template",
    title: "Agent templates",
    description: "Ready-made assistants. Installing one adds a draft assistant to this workspace.",
  },
  {
    category: "workflow",
    title: "Workflow blueprints",
    description:
      "Automations. Installing a supported blueprint creates a draft workflow that stays off until you turn it on.",
  },
] as const;

type Outcome = { slug: string; text: string; agentId: string | null };

function describeInstall(
  listing: MarketplaceListing,
  res: { agent_id: string | null; workflow_id: string | null },
): Outcome {
  if (res.workflow_id) {
    return {
      slug: listing.slug,
      text: "Created a draft workflow. Turn it on when you are ready.",
      agentId: null,
    };
  }
  if (res.agent_id) {
    return {
      slug: listing.slug,
      text: "Added a draft assistant to this workspace. Review it before you use it.",
      agentId: res.agent_id,
    };
  }
  return { slug: listing.slug, text: "Added to this workspace.", agentId: null };
}

const PILL_TONE: Record<ListingStatus | "installed", string> = {
  installable: "border-emerald-600 text-emerald-700 dark:text-emerald-400",
  requires_integration: "border-border text-foreground",
  not_supported: "border-destructive text-destructive",
  installed: "border-emerald-600 text-emerald-700 dark:text-emerald-400",
};

function Pill({ tone, children }: { tone: keyof typeof PILL_TONE; children: string }) {
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-sm ${PILL_TONE[tone]}`}>
      {children}
    </span>
  );
}

function RequirementItem({ req }: { req: MarketplaceRequirement }) {
  const needsIntegration = req.kind === "integration" && req.status === "requires_integration";
  return (
    <li className="break-words text-sm text-muted-foreground">
      {req.message}
      {needsIntegration && (
        <>
          {" "}
          <Link
            to="/studio/integrations"
            className="font-medium text-foreground underline underline-offset-4"
          >
            Open Integrations
          </Link>
        </>
      )}
    </li>
  );
}

type CardProps = {
  listing: MarketplaceListing;
  confirming: boolean;
  busy: boolean;
  anyBusy: boolean;
  outcome: Outcome | undefined;
  failure: string | undefined;
  onAsk: () => void;
  onCancel: () => void;
  onConfirm: () => void;
};

function ListingCard({
  listing,
  confirming,
  busy,
  anyBusy,
  outcome,
  failure,
  onAsk,
  onCancel,
  onConfirm,
}: CardProps) {
  const status = listingStatus(listing);
  const shownRequirements = listing.requirements.filter((r) => r.status !== "satisfied");
  const isWorkflow = listing.category === "workflow";

  return (
    <article className="grid min-w-0 gap-3 rounded-xl border border-border p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="min-w-0 break-words text-lg font-semibold">
          <span aria-hidden="true" className="mr-2">
            {listing.icon}
          </span>
          {listing.name}
        </h3>
        <div className="flex flex-wrap gap-2">
          {listing.installed ? (
            <Pill tone="installed">Installed</Pill>
          ) : (
            <Pill tone={status}>{LISTING_STATUS_LABEL[status]}</Pill>
          )}
        </div>
      </div>
      <p className="break-words text-sm text-muted-foreground">{listing.summary}</p>
      <p className="text-xs text-muted-foreground">By {listing.author}</p>

      {shownRequirements.length > 0 && (
        <ul className="grid gap-1 pl-4 [list-style:disc]">
          {shownRequirements.map((req) => (
            <RequirementItem key={`${req.kind}:${req.key}`} req={req} />
          ))}
        </ul>
      )}

      {outcome && (
        <p role="status" className="rounded-lg border border-border bg-muted px-3 py-2 text-sm">
          {outcome.text}{" "}
          {outcome.agentId && (
            <Link
              to="/studio/assistants/$id"
              params={{ id: outcome.agentId }}
              className="font-medium underline underline-offset-4"
            >
              Open the assistant
            </Link>
          )}
        </p>
      )}
      {failure && (
        <p
          role="alert"
          className="rounded-lg border border-destructive px-3 py-2 text-sm text-destructive"
        >
          {failure}
        </p>
      )}

      {!listing.installed && status === "installable" && (
        <div className="flex flex-wrap items-center gap-2">
          {confirming ? (
            <>
              <p className="w-full text-sm text-muted-foreground">
                {isWorkflow
                  ? "This creates a draft workflow. It stays off until you turn it on."
                  : "This adds a draft assistant with a starter knowledge base to this workspace."}
              </p>
              <Button
                size="sm"
                disabled={anyBusy}
                aria-label={`Confirm install of ${listing.name}`}
                onClick={onConfirm}
              >
                {busy ? "Installing…" : "Confirm install"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={anyBusy}
                aria-label={`Cancel install of ${listing.name}`}
                onClick={onCancel}
              >
                Cancel
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              disabled={anyBusy}
              aria-label={`Install ${listing.name}`}
              onClick={onAsk}
            >
              Install
            </Button>
          )}
        </div>
      )}
    </article>
  );
}

export function MarketplacePage() {
  const workspace = useWorkspaceId();
  const [listings, setListings] = useState<MarketplaceListing[] | null>(null);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [confirmSlug, setConfirmSlug] = useState<string | null>(null);
  const [busySlug, setBusySlug] = useState<string | null>(null);
  const [outcomes, setOutcomes] = useState<Record<string, Outcome>>({});
  const [failure, setFailure] = useState<{ slug: string; message: string } | null>(null);

  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    setError("");
    listMarketplaceListings(workspace.id)
      .then((items) => {
        if (!cancelled) setListings(items);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load the marketplace."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, reloadKey]);

  async function install(listing: MarketplaceListing) {
    if (!workspace.id) return;
    setConfirmSlug(null);
    setFailure(null);
    setBusySlug(listing.slug);
    try {
      // Nothing is shown as installed until the server answers; the list is then re-read.
      const res = await installMarketplaceListing(workspace.id, listing.slug);
      setOutcomes((prev) => ({ ...prev, [listing.slug]: describeInstall(listing, res) }));
      setReloadKey((k) => k + 1);
    } catch (err) {
      setFailure({
        slug: listing.slug,
        message: messageOf(err, "Couldn't install this template. Try again."),
      });
    } finally {
      setBusySlug(null);
    }
  }

  const retry = () => setReloadKey((k) => k + 1);
  const visible = (listings ?? []).filter((l) => GROUPS.some((g) => g.category === l.category));
  const anyBusy = busySlug !== null;

  return (
    <StudioFrame>
      <PageHeader
        title="Marketplace"
        description="Browse ready-made assistants and automation blueprints for this workspace. Installing creates drafts you review before they go live."
      />
      {workspace.error ? (
        <div className="mt-6">
          <ErrorNotice message={workspace.error} />
        </div>
      ) : !workspace.loaded ? (
        <div className="mt-6">
          <Loading label="Loading your workspace…" />
        </div>
      ) : !workspace.id ? (
        <p className="mt-6 text-muted-foreground">Create a workspace first.</p>
      ) : (
        <div className="mt-6 grid gap-8">
          {error && <ErrorNotice message={error} onRetry={retry} />}
          {!error && listings === null && (
            <ListSkeleton rows={3} label="Loading marketplace templates…" />
          )}
          {listings !== null && visible.length === 0 && (
            <EmptyState title="No templates are available yet.">
              Check back later. Nothing is installed until you choose a template.
            </EmptyState>
          )}
          {GROUPS.map((group) => {
            const items = visible.filter((l) => l.category === group.category);
            if (items.length === 0) return null;
            const headingId = `marketplace-${group.category}`;
            return (
              <section key={group.category} aria-labelledby={headingId} className="grid gap-3">
                <div>
                  <h2 id={headingId} className="text-xl font-semibold tracking-tight">
                    {group.title}
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">{group.description}</p>
                </div>
                <ul className="grid gap-4 md:grid-cols-2">
                  {items.map((listing) => (
                    <li key={listing.slug} className="min-w-0">
                      <ListingCard
                        listing={listing}
                        confirming={confirmSlug === listing.slug}
                        busy={busySlug === listing.slug}
                        anyBusy={anyBusy}
                        outcome={outcomes[listing.slug]}
                        failure={failure?.slug === listing.slug ? failure.message : undefined}
                        onAsk={() => setConfirmSlug(listing.slug)}
                        onCancel={() => setConfirmSlug(null)}
                        onConfirm={() => void install(listing)}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      )}
    </StudioFrame>
  );
}
