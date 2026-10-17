import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/client";
import {
  MARKETING_CHANNELS,
  MAX_MARKETING_RECIPIENTS,
  cancelMarketingCampaign,
  createMarketingCampaign,
  getMarketingCampaign,
  listMarketingCampaigns,
  sendMarketingCampaign,
  type MarketingCampaign,
  type MarketingCampaignDetail,
  type MarketingChannel,
  type MarketingRecipient,
  type MarketingRecipientStatus,
} from "@/lib/api/marketing";
import { listLeads, type Lead } from "@/lib/api/leads";
import { useWorkspaceId, when } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";
import { ProductGuide } from "./product-guide";
import { EmptyState, ErrorNotice, ListSkeleton, Loading, Notice, PageHeader } from "./studio-ui";

const CHANNEL_LABELS: Record<MarketingChannel, string> = {
  email: "Email",
  sms: "SMS",
  whatsapp: "WhatsApp",
};

const RECIPIENT_GROUPS: ReadonlyArray<{ status: MarketingRecipientStatus; heading: string }> = [
  { status: "queued", heading: "Will receive" },
  { status: "sent", heading: "Sent" },
  { status: "failed", heading: "Not sent" },
  { status: "skipped", heading: "Skipped" },
];

type PendingAction = "send" | "cancel" | null;

// Status values come from the API in lowercase; show them as plain words.
function statusLabel(status: string): string {
  const text = status.replace(/[_-]+/g, " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : "Unknown";
}

// Only drafts and scheduled campaigns can be sent or cancelled.
function isEditable(campaign: MarketingCampaign): boolean {
  return campaign.status === "draft" || campaign.status === "scheduled";
}

function leadLabel(lead: Lead): string {
  return lead.name || lead.email || lead.phone || "Unnamed lead";
}

// The note under the form says what the server adds to each message, so nothing surprises the sender.
function channelNote(channel: MarketingChannel): string {
  if (channel === "email") {
    return "An unsubscribe link is added to the end of every email automatically. Contacts who use it are added to your do-not-contact list for email.";
  }
  if (channel === "sms") {
    return "“Reply STOP to opt out.” is added to every text. Contacts who reply STOP are not messaged again.";
  }
  return "WhatsApp only reaches people who messaged you in the last 24 hours, or who received an approved template. WhatsApp refuses other free-text messages, and those show as not sent.";
}

export function MarketingPage() {
  const workspace = useWorkspaceId();
  const [campaigns, setCampaigns] = useState<MarketingCampaign[] | null>(null);
  const [listError, setListError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const [detail, setDetail] = useState<MarketingCampaignDetail | null>(null);
  const [detailError, setDetailError] = useState("");
  const [detailKey, setDetailKey] = useState(0);

  const [pending, setPending] = useState<PendingAction>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionNotice, setActionNotice] = useState("");

  const [creating, setCreating] = useState(false);
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [leadsError, setLeadsError] = useState("");
  const [name, setName] = useState("");
  const [channel, setChannel] = useState<MarketingChannel>("email");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [chosenLeads, setChosenLeads] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState("");

  // Campaign list.
  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    setListError("");
    listMarketingCampaigns(workspace.id)
      .then((rows) => {
        if (!cancelled) setCampaigns(Array.isArray(rows) ? rows : []);
      })
      .catch((err) => {
        if (!cancelled) setListError(messageOf(err, "Couldn't load marketing campaigns."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, reloadKey]);

  // Selected campaign with its recipient breakdown.
  useEffect(() => {
    if (!workspace.id || !selectedId) return;
    let cancelled = false;
    setDetail(null);
    setDetailError("");
    setPending(null);
    setActionError("");
    setActionNotice("");
    getMarketingCampaign(workspace.id, selectedId)
      .then((campaign) => {
        if (!cancelled) setDetail(campaign);
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
        if (!cancelled) setLeadsError(messageOf(err, "Couldn't load your leads."));
      });
    return () => {
      cancelled = true;
    };
  }, [creating, workspace.id, leads]);

  async function runAction(action: "send" | "cancel") {
    if (!workspace.id || !selectedId) return;
    setBusy(true);
    setActionError("");
    try {
      const updated =
        action === "send"
          ? await sendMarketingCampaign(workspace.id, selectedId)
          : await cancelMarketingCampaign(workspace.id, selectedId);
      setDetail(updated);
      setCampaigns((rows) => rows?.map((c) => (c.id === updated.id ? updated : c)) ?? rows);
      setPending(null);
      setActionNotice(
        action === "send"
          ? `Sent ${updated.sent_count}, not sent ${updated.failed_count}, skipped ${updated.skipped_count}.`
          : "Campaign cancelled. Nothing else will be sent.",
      );
    } catch (err) {
      setActionError(
        messageOf(
          err,
          action === "send"
            ? "Couldn't send this campaign. Check the recipients and try again."
            : "Couldn't cancel this campaign. Its status was not changed.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function submitCampaign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedName = name.trim();
    const trimmedBody = body.trim();
    const trimmedSubject = subject.trim();
    if (!workspace.id || !trimmedName || !trimmedBody || chosenLeads.length === 0) return;
    if (channel === "email" && !trimmedSubject) return;
    setSubmitting(true);
    setCreateError("");
    try {
      const created = await createMarketingCampaign(workspace.id, {
        name: trimmedName,
        channel,
        subject: channel === "email" ? trimmedSubject : null,
        body: trimmedBody,
        lead_ids: chosenLeads,
      });
      setCampaigns((rows) => [created, ...(rows ?? [])]);
      setCreating(false);
      setName("");
      setSubject("");
      setBody("");
      setChosenLeads([]);
      setSelectedId(created.id);
    } catch (err) {
      setCreateError(messageOf(err, "Couldn't create the campaign. Nothing was sent."));
    } finally {
      setSubmitting(false);
    }
  }

  function toggleLead(id: string) {
    setChosenLeads((ids) => {
      if (ids.includes(id)) return ids.filter((x) => x !== id);
      if (ids.length >= MAX_MARKETING_RECIPIENTS) return ids;
      return [...ids, id];
    });
  }

  const live = campaigns !== null && listError === "";
  const selectedSummary = campaigns?.find((c) => c.id === selectedId) ?? null;
  const formReady =
    name.trim().length > 0 &&
    body.trim().length > 0 &&
    chosenLeads.length > 0 &&
    (channel !== "email" || subject.trim().length > 0);

  return (
    <StudioFrame>
      <PageHeader
        title="Marketing"
        description="Send one message by email, SMS or WhatsApp to the leads you choose."
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
              {creating ? "Close campaign form" : "New campaign"}
            </Button>
          ) : undefined
        }
      />

      <ProductGuide
        whatItDoes="Sends one message to each lead you choose, by email, SMS or WhatsApp. Each lead is checked first: a lead is messaged only when they have said yes to marketing, and only when they are not on your do-not-contact list."
        needs={[
          "Consent set to granted on each lead. Leads with no consent or a withdrawn consent are skipped.",
          "A connected email, SMS or WhatsApp provider. Until one is connected, a send is recorded as not sent, with the reason.",
          "For email, a public API address on the server so the unsubscribe link works.",
        ]}
        terms={[
          {
            term: "Will receive",
            meaning: "The lead passed every check. The message is waiting to be sent.",
          },
          { term: "Sent", meaning: "The provider accepted the message." },
          {
            term: "Not sent",
            meaning:
              "The provider refused the message, or no provider is connected. The reason is shown.",
          },
          {
            term: "Skipped",
            meaning:
              "The lead was not messaged: no consent, on the do-not-contact list, asked not to be contacted, outside messaging hours, at the daily limit, or missing a valid address.",
          },
        ]}
        termsHeading="Why a recipient is skipped"
      />

      {workspace.error && (
        <div className="mt-4">
          <Notice kind="error">{workspace.error}</Notice>
        </div>
      )}
      {workspace.loaded && !workspace.id && !workspace.error && (
        <p className="mt-6 text-muted-foreground">Create a workspace to start a campaign.</p>
      )}
      {listError && (
        <div className="mt-4">
          <ErrorNotice
            message={listError}
            onRetry={workspace.id ? () => setReloadKey((k) => k + 1) : undefined}
          />
        </div>
      )}

      {creating && workspace.id && (
        <form
          onSubmit={submitCampaign}
          aria-label="New campaign"
          className="mt-6 grid gap-4 rounded-xl border border-border bg-card p-4"
        >
          <div className="grid gap-1 text-sm">
            <label htmlFor="marketing-name" className="font-medium">
              Campaign name
            </label>
            <input
              id="marketing-name"
              className="rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm"
              value={name}
              maxLength={120}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <fieldset className="grid gap-2 text-sm">
            <legend className="font-medium">Channel</legend>
            <div className="flex flex-wrap gap-2">
              {MARKETING_CHANNELS.map((option) => (
                <label
                  key={option}
                  className="flex min-h-11 items-center gap-2 rounded-lg border border-border px-3 py-2"
                >
                  <input
                    type="radio"
                    name="marketing-channel"
                    value={option}
                    checked={channel === option}
                    onChange={() => setChannel(option)}
                    className="size-4"
                  />
                  {CHANNEL_LABELS[option]}
                </label>
              ))}
            </div>
            <p className="rounded-lg bg-muted px-3 py-2 text-muted-foreground" role="note">
              {channelNote(channel)}
            </p>
          </fieldset>

          {channel === "email" && (
            <div className="grid gap-1 text-sm">
              <label htmlFor="marketing-subject" className="font-medium">
                Subject line
              </label>
              <input
                id="marketing-subject"
                className="rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm"
                value={subject}
                maxLength={200}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </div>
          )}

          <div className="grid gap-1 text-sm">
            <label htmlFor="marketing-body" className="font-medium">
              Message
            </label>
            <textarea
              id="marketing-body"
              className="min-h-32 rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm"
              value={body}
              maxLength={10000}
              onChange={(e) => setBody(e.target.value)}
              required
            />
          </div>

          <fieldset className="grid gap-2 text-sm">
            <legend className="font-medium">Choose leads</legend>
            {leadsError && <ErrorNotice message={leadsError} />}
            {!leadsError && leads === null && <Loading label="Loading leads…" />}
            {leads && leads.length === 0 && (
              <p className="text-muted-foreground">No leads yet. Add or import leads first.</p>
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
                        {(channel === "email" ? lead.email : lead.phone) && (
                          <span className="ml-2 text-muted-foreground">
                            {channel === "email" ? lead.email : lead.phone}
                          </span>
                        )}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-muted-foreground">
              {chosenLeads.length} of {MAX_MARKETING_RECIPIENTS} selected
            </p>
          </fieldset>

          {createError && <ErrorNotice message={createError} />}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={submitting || !formReady}>
              {submitting ? "Saving…" : "Save as draft"}
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
            {campaigns === null && !listError && workspace.id ? (
              <ListSkeleton rows={3} label="Loading campaigns…" />
            ) : campaigns && campaigns.length === 0 ? (
              <EmptyState
                title="No campaigns yet."
                action={
                  workspace.id && !creating ? (
                    <Button variant="outline" onClick={() => setCreating(true)}>
                      New campaign
                    </Button>
                  ) : undefined
                }
              >
                A campaign messages the leads you choose. Each lead is checked before anything is
                sent.
              </EmptyState>
            ) : campaigns ? (
              <ul className="grid gap-2" aria-label="Marketing campaigns">
                {campaigns.map((campaign) => {
                  const selected = campaign.id === selectedId;
                  return (
                    <li key={campaign.id}>
                      <button
                        type="button"
                        aria-pressed={selected}
                        onClick={() => setSelectedId(campaign.id)}
                        className={`flex w-full items-center justify-between gap-3 rounded-xl border px-4 py-3 text-left transition-colors hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${selected ? "border-primary bg-accent" : "border-border bg-card"}`}
                      >
                        <span className="min-w-0">
                          <span className="block truncate font-medium">{campaign.name}</span>
                          <time
                            className="mt-1 block text-sm text-muted-foreground"
                            dateTime={campaign.created_at}
                          >
                            {CHANNEL_LABELS[campaign.channel]} · Created {when(campaign.created_at)}
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
                  className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4"
                  aria-label="Campaign counts"
                >
                  {(
                    [
                      ["Will receive", detail.queued_count],
                      ["Sent", detail.sent_count],
                      ["Not sent", detail.failed_count],
                      ["Skipped", detail.skipped_count],
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
                    {CHANNEL_LABELS[detail.channel]} · {statusLabel(detail.status)}
                  </span>
                  {pending === null && isEditable(detail) && (
                    <>
                      <Button
                        size="sm"
                        disabled={busy || detail.queued_count === 0}
                        onClick={() => setPending("send")}
                      >
                        Send campaign
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => setPending("cancel")}
                      >
                        Cancel campaign
                      </Button>
                    </>
                  )}
                  {pending === "send" && (
                    <div
                      role="alertdialog"
                      aria-label="Confirm send"
                      className="flex flex-wrap items-center gap-2"
                    >
                      <span className="w-full text-muted-foreground sm:w-auto">
                        Send to {detail.queued_count}{" "}
                        {detail.queued_count === 1 ? "person" : "people"} by{" "}
                        {CHANNEL_LABELS[detail.channel]}? Sent messages cannot be recalled.
                      </span>
                      <Button size="sm" disabled={busy} onClick={() => runAction("send")}>
                        {busy ? "Sending…" : "Confirm send"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => setPending(null)}
                      >
                        Keep as draft
                      </Button>
                    </div>
                  )}
                  {pending === "cancel" && (
                    <div
                      role="alertdialog"
                      aria-label="Confirm cancel"
                      className="flex flex-wrap items-center gap-2"
                    >
                      <span className="w-full text-muted-foreground sm:w-auto">
                        Cancel this campaign? No one else will be messaged.
                      </span>
                      <Button size="sm" disabled={busy} onClick={() => runAction("cancel")}>
                        {busy ? "Cancelling…" : "Confirm cancel"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy}
                        onClick={() => setPending(null)}
                      >
                        Keep campaign
                      </Button>
                    </div>
                  )}
                </div>
                {actionError && <ErrorNotice message={actionError} />}
                {actionNotice && !actionError && (
                  <p role="status" className="text-sm text-muted-foreground">
                    {actionNotice}
                  </p>
                )}

                <div>
                  <h3 className="text-base font-semibold">Recipients</h3>
                  <div className="mt-3 grid gap-5">
                    {detail.recipients.length === 0 ? (
                      <EmptyState title="No recipients.">
                        This campaign has no leads attached.
                      </EmptyState>
                    ) : (
                      RECIPIENT_GROUPS.map((group) => {
                        const rows = detail.recipients.filter((r) => r.status === group.status);
                        if (rows.length === 0) return null;
                        return (
                          <RecipientGroup key={group.status} heading={group.heading} rows={rows} />
                        );
                      })
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

function RecipientGroup({ heading, rows }: { heading: string; rows: MarketingRecipient[] }) {
  return (
    <section aria-label={heading}>
      <h4 className="text-sm font-medium">
        {heading} <span className="text-muted-foreground">({rows.length})</span>
      </h4>
      <ul className="mt-2 grid gap-2">
        {rows.map((recipient) => {
          const reason = recipient.failure_reason || recipient.skip_reason;
          return (
            <li
              key={recipient.id}
              className="grid gap-1 rounded-xl border border-border bg-card px-4 py-3 text-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-medium">{recipient.lead_label}</span>
                {recipient.sent_at ? (
                  <time className="text-muted-foreground" dateTime={recipient.sent_at}>
                    {when(recipient.sent_at)}
                  </time>
                ) : null}
              </div>
              {reason && <p className="text-muted-foreground">Reason: {reason}</p>}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
