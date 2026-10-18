import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { getMe } from "@/lib/api/auth";
import { messageOf } from "@/lib/api/client";
import {
  addEscalationNote,
  assignEscalation,
  getEscalationSummary,
  listEscalations,
  reopenEscalation,
  resolveEscalation,
  type Escalation,
  type EscalationFilter,
  type EscalationSummary,
} from "@/lib/api/escalations";
import { useWorkspaceId } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";
import { EmptyState, ErrorNotice, ListSkeleton, Notice, PageHeader } from "./studio-ui";

const FILTERS: { value: EscalationFilter; label: string }[] = [
  { value: "open", label: "Waiting" },
  { value: "assigned", label: "Owned" },
  { value: "overdue", label: "Overdue" },
  { value: "resolved", label: "Resolved" },
];

const CHANNEL_NAMES: Record<string, string> = {
  chat: "Website chat",
  whatsapp: "WhatsApp",
  instagram: "Instagram",
  voice: "Voice",
  email: "Email",
};

/** Plain-language delivery state for the team. Visitors never see this. */
function notifyLabel(item: Escalation): string {
  switch (item.notify_status) {
    case "sent":
      return "Team emailed";
    case "pending":
      return "Team email queued";
    case "failed":
      return `Email failed, retrying (attempt ${item.notify_attempts})`;
    case "dead_letter":
      return "Email could not be delivered. Contact the team directly.";
    case "no_recipients":
      return "No owner or admin to email. Add one in Team settings.";
    default:
      return "";
  }
}

function dueLabel(item: Escalation): string {
  if (item.status === "resolved") return "Resolved";
  if (!item.due_at) return "No response target";
  const due = new Date(item.due_at);
  return item.overdue
    ? `Overdue since ${due.toLocaleString()}`
    : `Respond by ${due.toLocaleString()}`;
}

function contactLine(item: Escalation): string {
  if (!item.has_contact) return "No contact details. Ask the visitor for an email or phone number.";
  return [item.contact_name, item.contact_email, item.contact_phone].filter(Boolean).join(" · ");
}

export function EscalationsPage() {
  const workspace = useWorkspaceId();
  const projectId = workspace.id ?? "";
  const [filter, setFilter] = useState<EscalationFilter>("open");
  const [items, setItems] = useState<Escalation[] | null>(null);
  const [summary, setSummary] = useState<EscalationSummary | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [me, setMe] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    getMe()
      .then((user) => setMe(user.userId))
      .catch(() => setMe(null));
  }, []);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setError("");
    Promise.all([listEscalations(projectId, filter), getEscalationSummary(projectId)])
      .then(([rows, counts]) => {
        if (cancelled) return;
        setItems(Array.isArray(rows) ? rows : []);
        setSummary(counts && typeof counts === "object" ? counts : null);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load escalations."));
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, filter, reloadKey]);

  const selected = items?.find((item) => item.id === selectedId) ?? null;

  // Apply a change to the server copy, then refresh the list and counts.
  async function act(action: () => Promise<Escalation>, failure: string) {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      await action();
      setReloadKey((n) => n + 1);
      return true;
    } catch (err) {
      setError(messageOf(err, failure));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function addNote() {
    if (!projectId || !selected || !draft.trim()) return;
    const saved = await act(
      () => addEscalationNote(projectId, selected.id, draft.trim()),
      "Couldn't save the note. It was not added.",
    );
    if (saved) setDraft("");
  }

  const live = items !== null && error === "";

  return (
    <StudioFrame>
      <PageHeader
        title="Escalations"
        description="Questions the assistant could not answer, and requests for a person. Each one has an owner and a response target."
        live={live}
      />

      {summary && (
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Escalation counts">
          <div className="rounded-xl border border-border p-4">
            <dt className="text-sm text-muted-foreground">Waiting for an owner</dt>
            <dd className="text-2xl font-semibold">{summary.open}</dd>
          </div>
          <div className="rounded-xl border border-border p-4">
            <dt className="text-sm text-muted-foreground">Overdue</dt>
            <dd className="text-2xl font-semibold">{summary.overdue}</dd>
          </div>
          <div className="rounded-xl border border-border p-4">
            <dt className="text-sm text-muted-foreground">Team email failed</dt>
            <dd className="text-2xl font-semibold">
              {summary.notify_failed + summary.dead_letter}
            </dd>
          </div>
          <div className="rounded-xl border border-border p-4">
            <dt className="text-sm text-muted-foreground">Resolved</dt>
            <dd className="text-2xl font-semibold">{summary.resolved}</dd>
          </div>
        </dl>
      )}

      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter escalations">
        {FILTERS.map((option) => (
          <Button
            key={option.value}
            size="sm"
            variant={filter === option.value ? "default" : "outline"}
            aria-pressed={filter === option.value}
            onClick={() => {
              setFilter(option.value);
              setSelectedId(null);
            }}
          >
            {option.label}
          </Button>
        ))}
      </div>

      {error && <ErrorNotice message={error} onRetry={() => setReloadKey((n) => n + 1)} />}

      {items === null && !error && <ListSkeleton label="Loading escalations" />}

      {items !== null && items.length === 0 && (
        <EmptyState title="Nothing here">
          When the assistant cannot answer a visitor, or a visitor asks for a person, the item
          appears here.
        </EmptyState>
      )}

      {items !== null && items.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <ul className="grid gap-2" aria-label="Escalation list">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(item.id)}
                  aria-current={selectedId === item.id ? "true" : undefined}
                  className="grid w-full gap-1 rounded-xl border border-border p-4 text-left hover:bg-muted"
                >
                  <span className="text-xs uppercase tracking-wide text-muted-foreground">
                    {CHANNEL_NAMES[item.channel] ?? item.channel}
                  </span>
                  <span className="font-medium">{item.question}</span>
                  <span
                    className={`text-sm ${item.overdue ? "text-destructive" : "text-muted-foreground"}`}
                  >
                    {dueLabel(item)}
                  </span>
                </button>
              </li>
            ))}
          </ul>

          {selected ? (
            <section
              className="grid content-start gap-4 rounded-xl border border-border p-5"
              aria-label="Escalation detail"
            >
              <div className="grid gap-1">
                <h2 className="text-lg font-semibold">{selected.question}</h2>
                <p className="text-sm text-muted-foreground">{dueLabel(selected)}</p>
              </div>

              <div className="grid gap-1 text-sm">
                <p>
                  <strong>Contact:</strong> {contactLine(selected)}
                </p>
                <p className="text-muted-foreground">{notifyLabel(selected)}</p>
                {selected.last_error && (
                  <p className="text-muted-foreground">Last error: {selected.last_error}</p>
                )}
              </div>

              <div className="flex flex-wrap gap-2">
                {selected.status !== "resolved" && me && selected.assigned_user_id !== me && (
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() =>
                      act(
                        () => assignEscalation(projectId, selected.id, me),
                        "Couldn't assign this item.",
                      )
                    }
                  >
                    Take it
                  </Button>
                )}
                {selected.status !== "resolved" ? (
                  <Button
                    disabled={busy}
                    onClick={() =>
                      act(
                        () => resolveEscalation(projectId, selected.id),
                        "Couldn't resolve this item.",
                      )
                    }
                  >
                    Mark resolved
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() =>
                      act(
                        () => reopenEscalation(projectId, selected.id),
                        "Couldn't reopen this item.",
                      )
                    }
                  >
                    Reopen
                  </Button>
                )}
              </div>

              <div className="grid gap-2">
                <h3 className="font-medium">Internal notes</h3>
                <p className="text-xs text-muted-foreground">
                  Visible to your team only. The visitor never sees these.
                </p>
                {selected.internal_notes.length === 0 && (
                  <p className="text-sm text-muted-foreground">No notes yet.</p>
                )}
                <ul className="grid gap-2">
                  {selected.internal_notes.map((note) => (
                    <li key={`${note.at}-${note.text}`} className="rounded-lg bg-muted p-3 text-sm">
                      {note.text}
                      <span className="block text-xs text-muted-foreground">
                        {new Date(note.at).toLocaleString()}
                      </span>
                    </li>
                  ))}
                </ul>
                <label className="grid gap-1 text-sm" htmlFor="escalation-note">
                  Add a note
                  <textarea
                    id="escalation-note"
                    className="min-h-20 rounded-lg border border-border bg-background p-2"
                    value={draft}
                    maxLength={1000}
                    onChange={(event) => setDraft(event.target.value)}
                  />
                </label>
                <Button variant="outline" disabled={busy || !draft.trim()} onClick={addNote}>
                  Save note
                </Button>
              </div>
            </section>
          ) : (
            <Notice>Select an item to see the question, contact details and notes.</Notice>
          )}
        </div>
      )}
    </StudioFrame>
  );
}
