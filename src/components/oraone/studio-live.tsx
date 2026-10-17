import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError, messageOf } from "@/lib/api/client";
import {
  getConversation,
  listConversations,
  listMessages,
  type ConversationSummary,
  type Message,
} from "@/lib/api/inbox";
import {
  LEAD_STATUSES,
  getLeadStats,
  listLeads,
  updateLeadStatus,
  type Lead,
  type LeadStats,
} from "@/lib/api/leads";
import { StudioFrame } from "./studio";
import { LeadImportDialog } from "./studio-lead-import";
import { ProductGuide } from "./product-guide";
import { EmptyState, ErrorNotice, ListSkeleton, Loading, Notice, PageHeader } from "./studio-ui";
import { importConsentLine } from "@/lib/lead-consent";
import { when, useWorkspaceId } from "@/lib/studio-helpers";

// Plain-language names for the lead statuses the API stores in lowercase.
const LEAD_STATUS_NAME: Record<(typeof LEAD_STATUSES)[number], string> = {
  new: "New",
  contacted: "Contacted",
  qualified: "Qualified",
  won: "Won",
  lost: "Lost",
};

// Channel keys as the API stores them, with the names shown in Studio. A missing channel is the website.
const CHANNEL_LABEL: Record<string, string> = {
  chat: "Website",
  whatsapp: "WhatsApp",
  instagram: "Instagram",
  voice: "Voice",
  sms: "SMS",
  telegram: "Telegram",
  email: "Email",
};
const CHANNEL_FILTERS = [
  "chat",
  "whatsapp",
  "instagram",
  "voice",
  "sms",
  "telegram",
  "email",
] as const;

function channelKey(channel: string | null | undefined): string {
  return channel ? channel.toLowerCase() : "chat";
}

function channelLabel(channel: string | null | undefined): string {
  const key = channelKey(channel);
  return CHANNEL_LABEL[key] ?? key.charAt(0).toUpperCase() + key.slice(1);
}

export function InboxPage() {
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [channelFilter, setChannelFilter] = useState("");

  const visibleConversations =
    conversations === null || channelFilter === ""
      ? conversations
      : conversations.filter((c) => channelKey(c.channel) === channelFilter);

  useEffect(() => {
    let cancelled = false;
    setError("");
    listConversations()
      .then((items) => {
        // Guard the boundary: an unexpected payload shows the empty state, never a crash.
        if (!cancelled) setConversations(Array.isArray(items) ? items : []);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load conversations."));
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // "Live" only when the conversation query returned data.
  const live = conversations !== null && error === "";

  return (
    <StudioFrame>
      <PageHeader
        title="Conversations"
        description="Conversations with your assistants. Replies come from the assistant; staff replies aren't available yet."
        live={live}
      />
      <ProductGuide
        whatItDoes="Shows conversations your assistants have had with customers, from every channel. You can filter them by channel."
        needs={[
          "Each channel you use must be connected. Until it is, its messages will not arrive here.",
          "For website chats, the chat widget must be installed on your website.",
          "WhatsApp, Instagram, SMS, and voice each need their account set up before they can connect.",
        ]}
        terms={[
          { term: "Website", meaning: "Chats from the chat widget on your website." },
          { term: "WhatsApp", meaning: "Messages from customers on WhatsApp." },
          { term: "Instagram", meaning: "Direct messages sent to your Instagram account." },
          {
            term: "Voice",
            meaning: "Conversations from phone calls answered by your voice assistant.",
          },
          { term: "SMS", meaning: "Text messages sent to your business phone number." },
          { term: "Email", meaning: "Conversations that start with an email to your business." },
          { term: "Telegram", meaning: "Messages from Telegram." },
          {
            term: "Connected",
            meaning: "The channel's account is linked and set up for your business.",
          },
        ]}
        termsHeading="Channels and status"
      />
      {error && (
        <div className="mt-4">
          <ErrorNotice
            message={`${error} Check your connection and try again.`}
            onRetry={() => setReloadKey((k) => k + 1)}
          />
        </div>
      )}
      {conversations && conversations.length > 0 && (
        <div className="mt-6 grid gap-1 text-sm sm:inline-grid sm:grid-cols-[auto_auto] sm:items-center sm:gap-2">
          <label htmlFor="inbox-channel">Filter by channel</label>
          <select
            id="inbox-channel"
            className="rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm"
            value={channelFilter}
            onChange={(e) => setChannelFilter(e.target.value)}
          >
            <option value="">All channels</option>
            {CHANNEL_FILTERS.map((key) => (
              <option key={key} value={key}>
                {CHANNEL_LABEL[key]}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="mt-8">
        {conversations === null && !error ? (
          <ListSkeleton rows={3} label="Loading conversations…" />
        ) : conversations && conversations.length === 0 ? (
          <EmptyState
            title="No conversations yet."
            action={
              <Button asChild variant="outline">
                <Link to="/studio/assistants">Go to assistants</Link>
              </Button>
            }
          >
            Test an assistant in its playground to start one.
          </EmptyState>
        ) : visibleConversations && visibleConversations.length === 0 ? (
          <EmptyState title="No conversations on this channel.">
            Choose another channel, or select All channels to see every conversation.
          </EmptyState>
        ) : visibleConversations ? (
          <ul className="grid grid-cols-1 gap-2" aria-label="Conversations">
            {visibleConversations.map((c) => (
              <li key={c.id}>
                <Link
                  to="/studio/inbox/$conversationId"
                  params={{ conversationId: c.id }}
                  className="flex items-center gap-4 rounded-xl border border-border bg-card px-4 py-4 transition-colors hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">
                      {c.title || "Untitled conversation"}
                    </span>
                    <span className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                      <span className="rounded-full bg-muted px-2 py-0.5">
                        {channelLabel(c.channel)}
                      </span>
                      <span className="rounded-full bg-muted px-2 py-0.5 capitalize">
                        {c.status}
                      </span>
                      <time dateTime={c.last_message_at ?? c.updated_at}>
                        {when(c.last_message_at ?? c.updated_at)}
                      </time>
                    </span>
                  </span>
                  <ChevronRight
                    className="size-5 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </StudioFrame>
  );
}

export function InboxThreadPage({ conversationId }: { conversationId: string }) {
  const [title, setTitle] = useState<string | null | undefined>(undefined);
  const [messages, setMessages] = useState<Message[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setError("");
    Promise.all([getConversation(conversationId), listMessages(conversationId)])
      .then(([conversation, rows]) => {
        if (cancelled) return;
        setTitle(conversation.title || "Untitled conversation");
        setMessages(rows);
      })
      .catch((err) => {
        if (cancelled) return;
        setTitle(null);
        setError(
          err instanceof ApiError && err.status === 404
            ? "This conversation doesn't exist or you don't have access to it."
            : messageOf(err, "Couldn't load this conversation."),
        );
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  return (
    <StudioFrame>
      <Link to="/studio/inbox" className="inline-flex items-center gap-1 text-sm">
        <ArrowLeft className="size-4" aria-hidden="true" />
        Conversations
      </Link>
      {title === undefined && !error ? (
        <div className="mt-6">
          <Loading label="Loading conversation…" />
        </div>
      ) : (
        <>
          <h1 className="mt-2 break-words text-2xl font-semibold tracking-tight sm:text-3xl">
            {title ?? "Conversation"}
          </h1>
          {error && (
            <div className="mt-4">
              <Notice kind="error">{error}</Notice>
            </div>
          )}
          {messages && (
            <ol className="mt-6 grid gap-3" aria-label="Messages">
              {messages.length === 0 && <li className="text-muted-foreground">No messages yet.</li>}
              {messages.map((m) => (
                <li
                  key={m.id}
                  className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 ${m.role === "user" ? "ml-auto bg-primary text-primary-foreground" : "bg-muted"}`}
                >
                  <span className="block text-sm opacity-75">
                    {m.role === "user" ? "Visitor" : "Assistant"} · {when(m.created_at)}
                  </span>
                  {m.content}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </StudioFrame>
  );
}

export function LeadsPage() {
  const workspace = useWorkspaceId();
  const [leads, setLeads] = useState<Lead[] | null>(null);
  const [stats, setStats] = useState<LeadStats | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState("");
  const [savingId, setSavingId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [importOpen, setImportOpen] = useState(false);

  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    setError("");
    Promise.all([getLeadStats(workspace.id), listLeads(workspace.id, statusFilter || undefined)])
      .then(([s, rows]) => {
        if (cancelled) return;
        setStats(s);
        setLeads(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load leads."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, statusFilter, reloadKey]);

  async function changeStatus(lead: Lead, status: string) {
    // The API returns statuses title-cased ("Qualified"); options are lowercase.
    if (!workspace.id || status === lead.status.toLowerCase()) return;
    setSavingId(lead.id);
    setError("");
    try {
      const updated = await updateLeadStatus(workspace.id, lead.id, status);
      setLeads((rows) => rows?.map((r) => (r.id === updated.id ? updated : r)) ?? rows);
    } catch (err) {
      setError(messageOf(err, "Couldn't update this lead. Your change was not saved."));
    } finally {
      setSavingId(null);
    }
  }

  // "Live" only when the leads query returned data.
  const live = leads !== null && error === "";

  return (
    <StudioFrame>
      <PageHeader
        title="Leads"
        description="Contacts captured by your assistants."
        live={live}
        action={
          workspace.id ? (
            <Button variant="outline" onClick={() => setImportOpen(true)}>
              Import contacts
            </Button>
          ) : undefined
        }
      />
      <ProductGuide
        whatItDoes="Lists the contacts your assistants captured and lets you update each lead's status. You can also import contacts from a CSV or Excel file."
        needs={[
          "A .csv or .xlsx file of up to 5,000 rows and 5 MB. Macro-enabled .xlsm files are not accepted.",
          "Columns named Name, Phone, Email, Company, Notes, and an optional Consent column (yes, no, or blank).",
          "Each contact needs a phone number or an email address.",
        ]}
        terms={[
          {
            term: "Preview",
            meaning:
              "Nothing is saved until you confirm. The preview shows what would be saved and what would be skipped.",
          },
          {
            term: "Ready to save",
            meaning: "Valid contacts. Only these are saved when you confirm.",
          },
          {
            term: "Already leads",
            meaning: "This phone number or email is already in your leads, so the row is skipped.",
          },
          {
            term: "Repeated in file",
            meaning:
              "The same phone number or email appears earlier in the file, so this repeat is skipped.",
          },
          {
            term: "Needs fixing",
            meaning: "This row is missing details or has a problem, so it is skipped.",
          },
        ]}
        termsHeading="Import terms"
      />
      {workspace.id && (
        <LeadImportDialog
          projectId={workspace.id}
          open={importOpen}
          onOpenChange={setImportOpen}
          onImported={() => setReloadKey((k) => k + 1)}
        />
      )}
      {workspace.error && (
        <div className="mt-4">
          <Notice kind="error">{workspace.error}</Notice>
        </div>
      )}
      {error && (
        <div className="mt-4">
          <ErrorNotice
            message={error}
            onRetry={workspace.id ? () => setReloadKey((k) => k + 1) : undefined}
          />
        </div>
      )}
      {workspace.loaded && !workspace.id && !workspace.error && (
        <p className="mt-6 text-muted-foreground">Create a workspace to start capturing leads.</p>
      )}
      {stats && (
        <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Lead totals">
          {(
            [
              ["Total", stats.total],
              ["New", stats.new],
              ["Qualified", stats.qualified],
              ["Won", stats.won],
            ] as const
          ).map(([label, value]) => (
            <div key={label} className="rounded-lg border border-border bg-card p-4">
              <dt className="text-sm text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-2xl font-semibold">{value}</dd>
            </div>
          ))}
        </dl>
      )}
      {workspace.id && (
        <div className="mt-6 grid gap-1 text-sm sm:inline-grid sm:grid-cols-[auto_auto] sm:items-center sm:gap-2">
          <label htmlFor="lead-status">Filter by status</label>
          <select
            id="lead-status"
            className="rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All statuses</option>
            {LEAD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {LEAD_STATUS_NAME[s]}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="mt-6">
        {leads === null && !error && workspace.id ? (
          <ListSkeleton rows={3} label="Loading leads…" />
        ) : leads && leads.length === 0 ? (
          <EmptyState
            title="No leads yet."
            action={
              workspace.id ? (
                <Button variant="outline" onClick={() => setImportOpen(true)}>
                  Import contacts
                </Button>
              ) : undefined
            }
          >
            Leads appear here when a visitor shares their contact details with an assistant. You can
            also import a CSV or Excel file.
          </EmptyState>
        ) : leads ? (
          <ul className="grid gap-3" aria-label="Leads">
            {leads.map((lead) => {
              const statusKey = lead.status.toLowerCase() as (typeof LEAD_STATUSES)[number];
              const who = lead.name || lead.email || "this lead";
              const consent = importConsentLine({
                consent_source: lead.consent_source,
                consent_note: lead.consent_note,
              });
              return (
                <li
                  key={lead.id}
                  className="grid gap-3 rounded-xl border border-border bg-card p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{lead.name || "No name given"}</p>
                    <p className="truncate text-sm text-muted-foreground">
                      {[lead.email, lead.company].filter(Boolean).join(" · ") ||
                        "No contact details"}
                    </p>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Score {lead.score} · Captured {when(lead.created_at)}
                    </p>
                    {consent ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Consent {consent.value}. {consent.note}
                      </p>
                    ) : null}
                  </div>
                  <div className="grid gap-1 text-sm">
                    <label htmlFor={`status-${lead.id}`} className="text-muted-foreground">
                      Status for {who}
                    </label>
                    <select
                      id={`status-${lead.id}`}
                      className="rounded-md border border-input bg-background px-3 py-2 text-base sm:w-44 sm:text-sm"
                      value={statusKey}
                      disabled={savingId === lead.id}
                      onChange={(e) => changeStatus(lead, e.target.value)}
                    >
                      {LEAD_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {LEAD_STATUS_NAME[s]}
                        </option>
                      ))}
                    </select>
                  </div>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>
    </StudioFrame>
  );
}
