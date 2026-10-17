import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/client";
import {
  createCallCampaign,
  listCallAttempts,
  listCallCampaigns,
  getCallCampaign,
  pauseCallCampaign,
  startCallCampaign,
  type CallAttempt,
  type CallCampaign,
} from "@/lib/api/calls";
import { listLeads, type Lead } from "@/lib/api/leads";
import { useWorkspaceId, when } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";
import { ProductGuide } from "./product-guide";
import { EmptyState, ErrorNotice, ListSkeleton, Loading, Notice, PageHeader } from "./studio-ui";

// Status values come from the API in lowercase; show them as plain words.
function statusLabel(status: string): string {
  const text = status.replace(/[_-]+/g, " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Unknown";
}

// Start is offered for drafts and paused campaigns; Pause only while running.
function canStart(campaign: CallCampaign): boolean {
  return campaign.status === "draft" || campaign.status === "paused";
}

function isRunning(campaign: CallCampaign): boolean {
  return campaign.status === "running";
}

function attemptIsSkipped(attempt: CallAttempt): boolean {
  return attempt.status === "skipped" || Boolean(attempt.skip_reason);
}

function leadLabel(lead: Lead): string {
  return lead.name || lead.email || lead.phone || "Unnamed lead";
}

type PendingAction = "start" | "pause" | null;

export function CallsPage() {
  const workspace = useWorkspaceId();
  const [campaigns, setCampaigns] = useState<CallCampaign[] | null>(null);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [detail, setDetail] = useState<CallCampaign | null>(null);
  const [attempts, setAttempts] = useState<CallAttempt[] | null>(null);
  const [detailError, setDetailError] = useState("");
  const [detailKey, setDetailKey] = useState(0);

  const [pending, setPending] = useState<PendingAction>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");

  const [creating, setCreating] = useState(false);
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [leadsError, setLeadsError] = useState("");
  const [campaignName, setCampaignName] = useState("");
  const [chosenLeads, setChosenLeads] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState("");

  // Campaign list.
  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    setError("");
    listCallCampaigns(workspace.id)
      .then((rows) => {
        if (!cancelled) setCampaigns(Array.isArray(rows) ? rows : []);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load call campaigns."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, reloadKey]);

  // Selected campaign and its attempts.
  useEffect(() => {
    if (!workspace.id || !selectedId) return;
    let cancelled = false;
    setDetail(null);
    setAttempts(null);
    setDetailError("");
    setPending(null);
    setActionError("");
    Promise.all([
      getCallCampaign(workspace.id, selectedId),
      listCallAttempts(workspace.id, selectedId),
    ])
      .then(([campaign, rows]) => {
        if (cancelled) return;
        setDetail(campaign);
        setAttempts(Array.isArray(rows) ? rows : []);
      })
      .catch((err) => {
        if (!cancelled) setDetailError(messageOf(err, "Couldn't load this campaign."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, selectedId, detailKey]);

  // Leads to choose from when creating a campaign.
  useEffect(() => {
    if (!creating || !workspace.id || leads !== null) return;
    let cancelled = false;
    listLeads(workspace.id)
      .then((rows) => {
        if (!cancelled) setLeads(Array.isArray(rows) ? rows : []);
      })
      .catch((err) => {
        if (!cancelled) setLeadsError(messageOf(err, "Couldn't load your imported leads."));
      });
    return () => {
      cancelled = true;
    };
  }, [creating, workspace.id, leads]);

  async function runAction(action: "start" | "pause") {
    if (!workspace.id || !selectedId) return;
    setBusy(true);
    setActionError("");
    try {
      const updated =
        action === "start"
          ? await startCallCampaign(workspace.id, selectedId)
          : await pauseCallCampaign(workspace.id, selectedId);
      setDetail(updated);
      setCampaigns((rows) => rows?.map((c) => (c.id === updated.id ? updated : c)) ?? rows);
      setPending(null);
    } catch (err) {
      setActionError(
        messageOf(
          err,
          action === "start"
            ? "Couldn't start this campaign. Its status was not changed."
            : "Couldn't pause this campaign. Its status was not changed.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function submitCampaign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = campaignName.trim();
    if (!workspace.id || !name || chosenLeads.length === 0) return;
    setSubmitting(true);
    setCreateError("");
    try {
      const created = await createCallCampaign(workspace.id, {
        name,
        lead_ids: chosenLeads,
      });
      setCampaigns((rows) => [created, ...(rows ?? [])]);
      setCreating(false);
      setCampaignName("");
      setChosenLeads([]);
      setSelectedId(created.id);
    } catch (err) {
      setCreateError(messageOf(err, "Couldn't create the campaign. No calls were scheduled."));
    } finally {
      setSubmitting(false);
    }
  }

  function toggleLead(id: string) {
    setChosenLeads((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));
  }

  // "Live" only when the campaign query returned data.
  const live = campaigns !== null && error === "";
  const selectedSummary = campaigns?.find((c) => c.id === selectedId) ?? null;

  return (
    <StudioFrame>
      <PageHeader
        title="Calls"
        description="Outbound call campaigns for imported leads."
        live={live}
        action={
          workspace.id ? (
            <Button
              variant="outline"
              aria-expanded={creating}
              onClick={() => {
                setCreating((open) => !open);
                setCreateError("");
              }}
            >
              {creating ? "Close campaign form" : "Create campaign from imported leads"}
            </Button>
          ) : undefined
        }
      />

      <ProductGuide
        whatItDoes="Starts outbound call campaigns for imported leads and records the result of each call attempt. Calls go only to contacts who have said yes to being called, within calling hours."
        needs={[
          "A telephony account that is connected. Until it is, a started campaign does not place calls.",
          "Leads imported with Consent set to yes. Blank or unknown consent is never called.",
          "Calls are placed between 08:00 and 21:00 in the campaign's time zone.",
        ]}
        terms={[
          { term: "No consent", meaning: "The contact has not said yes to being called." },
          {
            term: "Outside calling hours",
            meaning: "The call would fall outside 08:00 to 21:00 in the campaign's time zone.",
          },
          {
            term: "Daily limit reached",
            meaning: "This contact has reached today's limit of call attempts.",
          },
          {
            term: "Do not contact",
            meaning:
              "The contact is on your do-not-contact list, asked not to be contacted, or withdrew consent.",
          },
          {
            term: "Phone number problem",
            meaning:
              "The lead has no phone number, or the number does not start with a + country code.",
          },
        ]}
        termsHeading="Why a call is skipped"
      />
      <div className="mt-6">
        <Notice>
          Calls run only when the telephony account is connected. Until it is connected, a started
          campaign does not place calls.
        </Notice>
      </div>

      {workspace.error && (
        <div className="mt-4">
          <Notice kind="error">{workspace.error}</Notice>
        </div>
      )}
      {workspace.loaded && !workspace.id && !workspace.error && (
        <p className="mt-6 text-muted-foreground">Create a workspace to start calling leads.</p>
      )}
      {error && (
        <div className="mt-4">
          <ErrorNotice
            message={error}
            onRetry={workspace.id ? () => setReloadKey((k) => k + 1) : undefined}
          />
        </div>
      )}

      {creating && workspace.id && (
        <form
          onSubmit={submitCampaign}
          aria-label="Create campaign"
          className="mt-6 grid gap-4 rounded-xl border border-border bg-card p-4"
        >
          <div className="grid gap-1 text-sm">
            <label htmlFor="campaign-name" className="font-medium">
              Campaign name
            </label>
            <input
              id="campaign-name"
              className="rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm"
              value={campaignName}
              maxLength={120}
              onChange={(e) => setCampaignName(e.target.value)}
              required
            />
          </div>

          <fieldset className="grid gap-2 text-sm">
            <legend className="font-medium">Choose imported leads</legend>
            {leadsError && <ErrorNotice message={leadsError} />}
            {!leadsError && leads === null && <Loading label="Loading leads…" />}
            {leads && leads.length === 0 && (
              <p className="text-muted-foreground">
                No imported leads yet. Import contacts from the Leads page first.
              </p>
            )}
            {leads && leads.length > 0 && (
              <ul className="grid max-h-72 gap-2 overflow-y-auto pr-1">
                {leads.map((lead) => (
                  <li key={lead.id}>
                    <label className="flex min-h-11 items-center gap-3 rounded-lg border border-border px-3 py-2">
                      <input
                        type="checkbox"
                        className="size-4 shrink-0"
                        checked={chosenLeads.includes(lead.id)}
                        onChange={() => toggleLead(lead.id)}
                      />
                      <span className="min-w-0 truncate">
                        {leadLabel(lead)}
                        {lead.phone && (
                          <span className="ml-2 text-muted-foreground">{lead.phone}</span>
                        )}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-muted-foreground">{chosenLeads.length} selected</p>
          </fieldset>

          {createError && <ErrorNotice message={createError} />}
          <div className="flex flex-wrap gap-2">
            <Button
              type="submit"
              disabled={submitting || !campaignName.trim() || chosenLeads.length === 0}
            >
              {submitting ? "Creating…" : "Create campaign"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setCreating(false);
                setCreateError("");
              }}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}

      <div className="mt-8 grid gap-8">
        <section aria-labelledby="campaigns-heading">
          <h2 id="campaigns-heading" className="text-lg font-semibold">
            Campaigns
          </h2>
          <div className="mt-3">
            {campaigns === null && !error && workspace.id ? (
              <ListSkeleton rows={3} label="Loading campaigns…" />
            ) : campaigns && campaigns.length === 0 ? (
              <EmptyState
                title="No call campaigns yet."
                action={
                  workspace.id && !creating ? (
                    <Button variant="outline" onClick={() => setCreating(true)}>
                      Create campaign from imported leads
                    </Button>
                  ) : undefined
                }
              >
                A campaign calls the leads you choose. Import contacts first if you have none.
              </EmptyState>
            ) : campaigns ? (
              <ul className="grid gap-2" aria-label="Call campaigns">
                {campaigns.map((campaign) => {
                  const selected = campaign.id === selectedId;
                  return (
                    <li key={campaign.id}>
                      <button
                        type="button"
                        aria-pressed={selected}
                        onClick={() => {
                          setSelectedId(campaign.id);
                        }}
                        className={`flex w-full items-center justify-between gap-3 rounded-xl border px-4 py-3 text-left transition-colors hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${selected ? "border-primary bg-accent" : "border-border bg-card"}`}
                      >
                        <span className="min-w-0">
                          <span className="block truncate font-medium">{campaign.name}</span>
                          <time
                            className="mt-1 block text-sm text-muted-foreground"
                            dateTime={campaign.created_at}
                          >
                            Created {when(campaign.created_at)}
                          </time>
                        </span>
                        <span className="shrink-0 rounded-full bg-muted px-2.5 py-0.5 text-sm">
                          {statusLabel(campaign.status)}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </div>
        </section>

        {selectedId && (
          <section aria-labelledby="campaign-detail-heading" className="grid gap-4">
            <h2 id="campaign-detail-heading" className="text-lg font-semibold">
              {selectedSummary?.name ?? "Campaign"}
            </h2>

            {detailError && (
              <ErrorNotice message={detailError} onRetry={() => setDetailKey((k) => k + 1)} />
            )}
            {!detail && !detailError && <Loading label="Loading campaign…" />}

            {detail && (
              <>
                <dl
                  className="grid grid-cols-3 gap-3 text-sm sm:grid-cols-6"
                  aria-label="Campaign counts"
                >
                  {(
                    [
                      ["Leads", detail.counts.total],
                      ["Queued", detail.counts.queued],
                      ["Calling", detail.counts.calling],
                      ["Completed", detail.counts.completed],
                      ["Failed", detail.counts.failed],
                      ["Skipped", detail.counts.skipped],
                    ] as const
                  ).map(([label, value]) => (
                    <div key={label} className="rounded-lg border border-border bg-card p-3">
                      <dt className="text-muted-foreground">{label}</dt>
                      <dd className="mt-1 text-lg font-semibold">{value}</dd>
                    </div>
                  ))}
                </dl>
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <span className="rounded-full bg-muted px-2.5 py-0.5">
                    {statusLabel(detail.status)}
                  </span>
                  {pending === null && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy || !canStart(detail)}
                        onClick={() => setPending("start")}
                      >
                        Start campaign
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy || !isRunning(detail)}
                        onClick={() => setPending("pause")}
                      >
                        Pause campaign
                      </Button>
                    </>
                  )}
                  {pending !== null && (
                    <>
                      <span className="w-full text-muted-foreground sm:w-auto">
                        {pending === "start"
                          ? "Start this campaign? Calls run only when the telephony account is connected."
                          : "Pause this campaign? It will stop starting new calls."}
                      </span>
                      <Button size="sm" disabled={busy} onClick={() => runAction(pending)}>
                        {busy ? "Saving…" : pending === "start" ? "Confirm start" : "Confirm pause"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => setPending(null)}
                      >
                        Cancel
                      </Button>
                    </>
                  )}
                </div>
                {actionError && <ErrorNotice message={actionError} />}

                <div>
                  <h3 className="text-base font-semibold">Attempts</h3>
                  <div className="mt-3">
                    {attempts === null ? (
                      <ListSkeleton rows={2} label="Loading attempts…" />
                    ) : attempts.length === 0 ? (
                      <EmptyState title="No attempts yet.">
                        Attempts appear here once the campaign starts working through its leads.
                      </EmptyState>
                    ) : (
                      <ul className="grid gap-2" aria-label="Call attempts">
                        {attempts.map((attempt) => {
                          const skipped = attemptIsSkipped(attempt);
                          return (
                            <li
                              key={attempt.id}
                              className="grid gap-1 rounded-xl border border-border bg-card px-4 py-3 text-sm"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <span className="font-medium">{statusLabel(attempt.status)}</span>
                                {attempt.attempted_at ? (
                                  <time
                                    className="text-muted-foreground"
                                    dateTime={attempt.attempted_at}
                                  >
                                    {when(attempt.attempted_at)}
                                  </time>
                                ) : (
                                  <span className="text-muted-foreground">Not attempted yet</span>
                                )}
                              </div>
                              {skipped && (
                                <p className="text-muted-foreground">
                                  Reason:{" "}
                                  {attempt.skip_reason || "The system did not record a reason."}
                                </p>
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
