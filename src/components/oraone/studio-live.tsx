import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
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
import { Loading, Notice } from "./studio-ui";
import { when, useWorkspaceId } from "@/lib/studio-helpers";

export function InboxPage() {
  const [conversations, setConversations] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    listConversations()
      .then((items) => {
        if (!cancelled) setConversations(items);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load conversations."));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <StudioFrame>
      <span className="marketing-eyebrow">LIVE · INBOX</span>
      <h1 className="mt-2 text-3xl font-semibold">Conversations</h1>
      <p className="mt-2 text-muted-foreground">
        Conversations with your assistants. Replies come from the assistant; staff replies aren't
        available yet.
      </p>
      {error && (
        <div className="mt-4">
          <Notice kind="error">{error}</Notice>
        </div>
      )}
      <div className="mt-8">
        {conversations === null && !error ? (
          <Loading label="Loading conversations…" />
        ) : conversations && conversations.length === 0 ? (
          <p className="text-muted-foreground">
            No conversations yet. Test an assistant in its playground to start one.
          </p>
        ) : conversations ? (
          <ul className="grid gap-2" aria-label="Conversations">
            {conversations.map((c) => (
              <li key={c.id}>
                <Link
                  to="/studio/inbox/$conversationId"
                  params={{ conversationId: c.id }}
                  className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card px-4 py-3 hover:bg-accent"
                >
                  <span className="font-medium">{c.title || "Untitled conversation"}</span>
                  <span className="text-sm text-muted-foreground">
                    {when(c.last_message_at ?? c.updated_at)}
                  </span>
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
        <ArrowLeft className="size-4" />
        Inbox
      </Link>
      {title === undefined && !error ? (
        <div className="mt-6">
          <Loading label="Loading conversation…" />
        </div>
      ) : (
        <>
          <h1 className="mt-2 text-3xl font-semibold">{title ?? "Conversation"}</h1>
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
  }, [workspace.id, statusFilter]);

  async function changeStatus(lead: Lead, status: string) {
    // The API returns statuses title-cased ("Qualified"); options are lowercase.
    if (!workspace.id || status === lead.status.toLowerCase()) return;
    setSavingId(lead.id);
    setError("");
    try {
      const updated = await updateLeadStatus(workspace.id, lead.id, status);
      setLeads((rows) => rows?.map((r) => (r.id === updated.id ? updated : r)) ?? rows);
    } catch (err) {
      setError(messageOf(err, "Couldn't update this lead."));
    } finally {
      setSavingId(null);
    }
  }

  return (
    <StudioFrame>
      <span className="marketing-eyebrow">LIVE · LEADS</span>
      <h1 className="mt-2 text-3xl font-semibold">Leads</h1>
      <p className="mt-2 text-muted-foreground">Contacts captured by your assistants.</p>
      {workspace.error && (
        <div className="mt-4">
          <Notice kind="error">{workspace.error}</Notice>
        </div>
      )}
      {error && (
        <div className="mt-4">
          <Notice kind="error">{error}</Notice>
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
        <div className="mt-6 flex items-center gap-2">
          <label htmlFor="lead-status" className="text-sm">
            Filter by status
          </label>
          <select
            id="lead-status"
            className="rounded-md border border-input bg-background px-3 py-2"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All</option>
            {LEAD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="mt-6">
        {leads === null && !error && workspace.id ? (
          <Loading label="Loading leads…" />
        ) : leads && leads.length === 0 ? (
          <p className="text-muted-foreground">No leads yet.</p>
        ) : leads ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Email</th>
                  <th className="py-2 pr-4 font-medium">Company</th>
                  <th className="py-2 pr-4 font-medium">Score</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 font-medium">Captured</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id} className="border-b border-border">
                    <td className="py-2 pr-4">{lead.name || "—"}</td>
                    <td className="py-2 pr-4">{lead.email || "—"}</td>
                    <td className="py-2 pr-4">{lead.company || "—"}</td>
                    <td className="py-2 pr-4">{lead.score}</td>
                    <td className="py-2 pr-4">
                      <label className="sr-only" htmlFor={`status-${lead.id}`}>
                        Status for {lead.name || lead.email || "lead"}
                      </label>
                      <select
                        id={`status-${lead.id}`}
                        className="rounded-md border border-input bg-background px-2 py-1"
                        value={lead.status.toLowerCase()}
                        disabled={savingId === lead.id}
                        onChange={(e) => changeStatus(lead, e.target.value)}
                      >
                        {LEAD_STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2">{when(lead.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </StudioFrame>
  );
}
