import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Bot, Loader2, LogOut, Menu, Plus, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ApiError, messageOf } from "@/lib/api/client";
import { getMe, logout } from "@/lib/api/auth";
import {
  createAgent,
  createConversation,
  createProject,
  getAgent,
  listAgents,
  listProjects,
  sendMessage,
  updateAgent,
  updateProjectSettings,
  type Agent,
  type Project,
} from "@/lib/api/studio";
import type { ChannelPageKey } from "@/lib/studio-os";
import { Brand } from "./shell";
import { EmptyState, ErrorNotice, Notice, PageHeader } from "./studio-ui";

type Workspace = { id: string; name: string; website: string | null };
type Assistant = { id: string; name: string; purpose: string; instructions: string };
type ChatTurn = { role: "user" | "assistant"; content: string; generated?: boolean };

const FALLBACK_REPLY_NOTICE =
  "This reply was a fallback because the AI model is not available right now.";

// Assistant purpose is stored as the agent description so no backend field is invented.
const PURPOSES = ["Customer support", "Lead qualification", "Customer onboarding", "Other"];

const toWorkspace = (p: Project): Workspace => ({
  id: p.id,
  name: p.name,
  website: typeof p.settings["website"] === "string" ? (p.settings["website"] as string) : null,
});

const toAssistant = (a: Agent): Assistant => ({
  id: a.id,
  name: a.name,
  purpose: PURPOSES.includes(a.description ?? "") ? (a.description as string) : "Other",
  instructions: a.system_prompt ?? "",
});

// Studio navigation, in four groups. Every route the studio had stays reachable; only the grouping
// and labels changed. Marketing has no screen yet, so it is shown but cannot be opened.
type NavItem =
  | { label: string; to: StudioNavPath }
  | { label: string; channel: ChannelPageKey }
  | { label: string; to: null };

type StudioNavPath =
  | "/studio/inbox"
  | "/studio/escalations"
  | "/studio/calls"
  | "/studio/marketing"
  | "/studio/leads"
  | "/studio/workflows"
  | "/studio/analytics"
  | "/studio/assistants"
  | "/studio/knowledge"
  | "/studio/marketplace"
  | "/studio/getting-started"
  | "/studio/integrations"
  | "/studio/webhooks"
  | "/studio/api-keys"
  | "/studio/team"
  | "/studio/billing"
  | "/studio/account";

const STUDIO_NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: "Conversations",
    items: [
      { label: "Inbox", to: "/studio/inbox" },
      { label: "Escalations", to: "/studio/escalations" },
      { label: "Calls", to: "/studio/calls" },
    ],
  },
  {
    title: "Channels",
    items: [
      { label: "Website chat", channel: "website-chat" },
      { label: "WhatsApp", channel: "whatsapp" },
      { label: "Instagram", channel: "instagram" },
      { label: "Voice", channel: "voice" },
    ],
  },
  {
    title: "Grow",
    items: [
      { label: "Leads", to: "/studio/leads" },
      { label: "Marketing", to: "/studio/marketing" },
      { label: "Workflows", to: "/studio/workflows" },
      { label: "Analytics", to: "/studio/analytics" },
    ],
  },
  {
    title: "Build",
    items: [
      { label: "AI Studio", to: "/studio/assistants" },
      { label: "Knowledge", to: "/studio/knowledge" },
      { label: "Marketplace", to: "/studio/marketplace" },
      { label: "Getting started", to: "/studio/getting-started" },
      { label: "Integrations", to: "/studio/integrations" },
      { label: "Webhooks", to: "/studio/webhooks" },
      { label: "API keys", to: "/studio/api-keys" },
      { label: "Team", to: "/studio/team" },
      { label: "Billing", to: "/studio/billing" },
      { label: "Settings", to: "/studio/account" },
    ],
  },
];

const NAV_ACTIVE = {
  "aria-current": "page",
  className: "bg-accent text-accent-foreground",
} as const;

function StudioNavItem({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const className = "inline-block rounded-md px-3 py-2 hover:bg-muted";
  if ("channel" in item) {
    return (
      <Link
        to="/studio/channels/$channel"
        params={{ channel: item.channel }}
        onClick={onNavigate}
        activeProps={NAV_ACTIVE}
        className={className}
      >
        {item.label}
      </Link>
    );
  }
  if (item.to === null) {
    return (
      <span
        aria-disabled="true"
        title="Not connected yet"
        className="inline-block rounded-md px-3 py-2 text-muted-foreground"
      >
        {item.label}
      </span>
    );
  }
  return (
    <Link to={item.to} onClick={onNavigate} activeProps={NAV_ACTIVE} className={className}>
      {item.label}
    </Link>
  );
}

export function StudioFrame({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    getMe()
      .then((me) => setEmail(me.email))
      .catch(() => setEmail(""));
  }, []);
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="border-b border-border bg-background">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3 sm:px-5">
          <Link to="/studio" aria-label="OraOne OS home" className="shrink-0">
            <Brand />
          </Link>
          <div className="flex min-w-0 items-center gap-2 text-sm sm:gap-3">
            <span className="hidden min-w-0 truncate text-muted-foreground lg:inline">{email}</span>
            <Button
              variant="outline"
              size="sm"
              aria-label="Sign out"
              onClick={async () => {
                await logout().catch(() => undefined);
                navigate({ to: "/auth/sign-in", replace: true });
              }}
            >
              <LogOut />
              <span className="hidden sm:inline">Sign out</span>
            </Button>
          </div>
        </div>
        <nav
          aria-label="Studio sections"
          className="mx-auto max-w-5xl px-3 pb-2 text-sm font-medium"
        >
          <div className="hidden gap-x-6 gap-y-3 md:grid">
            {STUDIO_NAV_GROUPS.map((group) => (
              <section
                key={group.title}
                aria-label={group.title}
                className="grid grid-cols-[7.5rem_1fr] items-baseline gap-2"
              >
                <p className="px-3 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                  {group.title}
                </p>
                <ul className="flex flex-wrap gap-1">
                  {group.items.map((item) => (
                    <li key={item.label}>
                      <StudioNavItem item={item} />
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
          <div className="flex justify-end md:hidden">
            <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="sm">
                  <Menu />
                  Menu
                </Button>
              </SheetTrigger>
              <SheetContent side="left">
                <SheetHeader>
                  <SheetTitle>Studio sections</SheetTitle>
                  <SheetDescription>Choose where to go next.</SheetDescription>
                </SheetHeader>
                <nav aria-label="All studio sections" className="mt-4 grid gap-5">
                  {STUDIO_NAV_GROUPS.map((group) => (
                    <section key={group.title} aria-label={group.title} className="grid gap-1">
                      <p className="px-3 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                        {group.title}
                      </p>
                      {group.items.map((item) => (
                        <div key={item.label}>
                          <StudioNavItem item={item} onNavigate={() => setMenuOpen(false)} />
                        </div>
                      ))}
                    </section>
                  ))}
                </nav>
              </SheetContent>
            </Sheet>
          </div>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-5xl px-4 py-8 text-base sm:px-5">{children}</main>
    </div>
  );
}

export function StudioHome() {
  const [showNewAssistant, setShowNewAssistant] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [assistants, setAssistants] = useState<Assistant[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [error, setError] = useState("");
  const [wsName, setWsName] = useState("");
  const [wsSite, setWsSite] = useState("");
  const [aName, setAName] = useState("");
  const [aPurpose, setAPurpose] = useState(PURPOSES[0]!);
  const [busy, setBusy] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    try {
      const { items } = await listProjects();
      const list = items.map(toWorkspace);
      setWorkspaces(list);
      setSelected((s) => (list.some((w) => w.id === s) ? s : (list[0]?.id ?? "")));
    } catch (e) {
      setError(messageOf(e, "Couldn't load your workspaces."));
      setWorkspaces([]);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load, reloadKey]);

  useEffect(() => {
    if (!selected) {
      setAssistants([]);
      return;
    }
    let cancelled = false;
    listAgents(selected)
      .then(({ items }) => {
        if (!cancelled) setAssistants(items.map(toAssistant));
      })
      .catch((e) => {
        if (!cancelled) setError(messageOf(e, "Couldn't load assistants."));
      });
    return () => {
      cancelled = true;
    };
  }, [selected, reloadKey]);

  const retry = () => {
    setError("");
    setReloadKey((k) => k + 1);
  };

  async function createWorkspace(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (wsName.trim().length < 2) {
      setError("Workspace name needs at least 2 characters.");
      return;
    }
    setBusy(true);
    try {
      const created = await createProject({ name: wsName.trim() });
      if (wsSite.trim()) await updateProjectSettings(created.id, { website: wsSite.trim() });
      setWsName("");
      setWsSite("");
      setSelected(created.id);
      await load();
    } catch (err) {
      setError(messageOf(err, "Couldn't create the workspace. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  async function createAssistant(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (aName.trim().length < 2) {
      setError("Assistant name needs at least 2 characters.");
      return;
    }
    setBusy(true);
    try {
      const agent = await createAgent(selected, {
        name: aName.trim(),
        type: "chat",
        description: aPurpose,
      });
      navigate({ to: "/studio/assistants/$id", params: { id: agent.id } });
    } catch (err) {
      setError(messageOf(err, "Couldn't create the assistant. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  const current = workspaces?.find((w) => w.id === selected);
  // "Live" only when the workspace and assistant queries both returned data.
  const live = workspaces !== null && workspaces.length > 0 && error === "";
  return (
    <StudioFrame>
      <PageHeader
        title="Your assistants"
        description="Create an assistant, teach it from your content and add it to your website. Everything is saved to your account."
        live={live}
      />
      {error && (
        <div className="mt-4">
          <ErrorNotice message={`${error} Check your connection and try again.`} onRetry={retry} />
        </div>
      )}
      {workspaces === null ? (
        <p className="mt-8 flex items-center gap-2 text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          Loading your assistants…
        </p>
      ) : (
        <div className="mt-8 grid gap-8">
          <section aria-labelledby="assistants-heading" className="grid gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 id="assistants-heading" className="text-xl font-semibold">
                {current ? `Assistants in ${current.name}` : "Assistants"}
              </h2>
              {current && (
                <Button
                  className="w-full sm:w-auto"
                  onClick={() => setShowNewAssistant((open) => !open)}
                  aria-expanded={showNewAssistant}
                  aria-controls="new-assistant-form"
                >
                  <Plus />
                  New assistant
                </Button>
              )}
            </div>
            {!current ? (
              <EmptyState title="No workspace yet.">
                Open Workspaces below and add one. It holds your assistants and their leads.
              </EmptyState>
            ) : assistants.length === 0 ? (
              <EmptyState
                title="No assistants yet."
                action={
                  <Button
                    onClick={() => setShowNewAssistant(true)}
                    aria-controls="new-assistant-form"
                  >
                    <Plus />
                    Create your first assistant
                  </Button>
                }
              >
                Create one to start answering visitors on your website.
              </EmptyState>
            ) : (
              <ul className="grid gap-3 md:grid-cols-2">
                {assistants.map((a) => (
                  <li key={a.id}>
                    <Link
                      to="/studio/assistants/$id"
                      params={{ id: a.id }}
                      className="flex h-full items-center gap-4 rounded-xl border border-border bg-card p-4 hover:bg-accent"
                    >
                      <span className="grid size-10 shrink-0 place-items-center rounded-full bg-accent">
                        <Bot className="size-5" aria-hidden="true" />
                      </span>
                      <span>
                        <strong className="block text-base">{a.name}</strong>
                        <span className="text-sm text-muted-foreground">{a.purpose}</span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {current && showNewAssistant && (
              <form
                id="new-assistant-form"
                onSubmit={createAssistant}
                className="grid max-w-xl gap-3 rounded-xl border border-border bg-card p-5"
              >
                <h3 className="text-base font-semibold">New assistant</h3>
                <label htmlFor="a-name" className="text-sm font-medium">
                  Assistant name
                </label>
                <input
                  id="a-name"
                  className="rounded-md border border-input bg-background px-3 py-2 text-base"
                  value={aName}
                  onChange={(e) => setAName(e.target.value)}
                  placeholder="Customer Support"
                />
                <label htmlFor="a-purpose" className="text-sm font-medium">
                  Purpose
                </label>
                <select
                  id="a-purpose"
                  className="rounded-md border border-input bg-background px-3 py-2 text-base"
                  value={aPurpose}
                  onChange={(e) => setAPurpose(e.target.value)}
                >
                  {PURPOSES.map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
                <Button type="submit" disabled={busy} className="justify-self-start">
                  Create assistant
                </Button>
              </form>
            )}
          </section>

          <details className="rounded-xl border border-border p-5">
            <summary className="cursor-pointer text-base font-semibold">
              Workspaces ({workspaces.length})
            </summary>
            <ul className="mt-4 grid gap-2">
              {workspaces.map((w) => (
                <li key={w.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(w.id)}
                    aria-pressed={w.id === selected}
                    className={`w-full rounded-lg border px-3 py-2 text-left ${w.id === selected ? "border-primary bg-accent" : "border-border"}`}
                  >
                    {w.name}
                  </button>
                </li>
              ))}
            </ul>
            <form
              onSubmit={createWorkspace}
              className="mt-5 grid max-w-xl gap-2 border-t border-border pt-4"
            >
              <h3 className="text-base font-semibold">Add a workspace</h3>
              <label htmlFor="ws-name" className="text-sm font-medium">
                Name
              </label>
              <input
                id="ws-name"
                className="rounded-md border border-input bg-background px-3 py-2 text-base"
                value={wsName}
                onChange={(e) => setWsName(e.target.value)}
                placeholder="Your organization"
              />
              <label htmlFor="ws-site" className="text-sm font-medium">
                Website (optional)
              </label>
              <input
                id="ws-site"
                type="url"
                className="rounded-md border border-input bg-background px-3 py-2 text-base"
                value={wsSite}
                onChange={(e) => setWsSite(e.target.value)}
                placeholder="https://your-website.com"
              />
              <Button
                type="submit"
                disabled={busy}
                variant="outline"
                className="justify-self-start"
              >
                <Plus />
                Create workspace
              </Button>
            </form>
          </details>
        </div>
      )}
    </StudioFrame>
  );
}

export function StudioAssistant({ id }: { id: string }) {
  const [assistant, setAssistant] = useState<Assistant | null | undefined>(undefined);
  const [loadError, setLoadError] = useState("");
  const [draft, setDraft] = useState({ name: "", purpose: "", instructions: "" });
  const [saved, setSaved] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [chatError, setChatError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setAssistant(undefined);
    setLoadError("");
    getAgent(id)
      .then((agent) => {
        if (cancelled) return;
        const next = toAssistant(agent);
        setAssistant(next);
        setDraft({ name: next.name, purpose: next.purpose, instructions: next.instructions });
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && (err.status === 404 || err.status === 403))
          setAssistant(null);
        else {
          setLoadError(messageOf(err, "Couldn't load this assistant."));
          setAssistant(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id]);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages, thinking]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaved("");
    if (draft.name.trim().length < 2) {
      setSaved("Name needs at least 2 characters.");
      return;
    }
    try {
      const updated = await updateAgent(id, {
        name: draft.name.trim(),
        description: draft.purpose,
        system_prompt: draft.instructions.slice(0, 4000),
      });
      setAssistant(toAssistant(updated));
      setSaved("Saved.");
    } catch (err) {
      setSaved(messageOf(err, "Couldn't save. Please try again."));
    }
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || thinking) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    setThinking(true);
    setChatError("");
    try {
      // One conversation per playground visit; the backend keeps the history.
      let convId = conversationId;
      if (!convId) {
        const conversation = await createConversation(id, "Playground");
        convId = conversation.id;
        setConversationId(convId);
      }
      const result = await sendMessage(convId, text);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: result.assistant_message.content,
          generated: result.generated !== false,
        },
      ]);
    } catch (err) {
      setChatError(messageOf(err, "Something went wrong. Please try again."));
    } finally {
      setThinking(false);
    }
  }

  if (assistant === undefined)
    return (
      <StudioFrame>
        <p className="flex items-center gap-2">
          <Loader2 className="animate-spin" />
          Loading…
        </p>
      </StudioFrame>
    );
  if (assistant === null)
    return (
      <StudioFrame>
        <Notice kind="error">
          {loadError || "This assistant doesn't exist or you don't have access to it."}
        </Notice>
        <Button asChild variant="outline" className="mt-4">
          <Link to="/studio/assistants">
            <ArrowLeft />
            Back to assistants
          </Link>
        </Button>
      </StudioFrame>
    );
  return (
    <StudioFrame>
      <Link to="/studio/assistants" className="inline-flex items-center gap-1 text-sm">
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to assistants
      </Link>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
        <h1 className="min-w-0 break-words text-2xl font-semibold tracking-tight sm:text-3xl">
          {assistant.name}
        </h1>
        <Button asChild className="w-full sm:w-auto">
          <Link to="/studio/assistants/$id/install" params={{ id }}>
            Add to website
          </Link>
        </Button>
      </div>
      <p className="mt-1 text-muted-foreground">
        Configure how it behaves, then test real answers in the playground.
      </p>
      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <form
          onSubmit={save}
          className="grid content-start gap-2 rounded-xl border border-border bg-card p-5"
        >
          <h2 className="text-xl font-semibold">Configuration</h2>
          <label htmlFor="c-name" className="text-sm">
            Name
          </label>
          <input
            id="c-name"
            className="rounded-md border border-input bg-background px-3 py-2"
            value={draft.name}
            onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
          />
          <label htmlFor="c-purpose" className="text-sm">
            Purpose
          </label>
          <select
            id="c-purpose"
            className="rounded-md border border-input bg-background px-3 py-2"
            value={draft.purpose}
            onChange={(e) => setDraft((d) => ({ ...d, purpose: e.target.value }))}
          >
            {PURPOSES.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
          <label htmlFor="c-ins" className="text-sm">
            Instructions
          </label>
          <textarea
            id="c-ins"
            rows={8}
            className="rounded-md border border-input bg-background px-3 py-2"
            value={draft.instructions}
            onChange={(e) => setDraft((d) => ({ ...d, instructions: e.target.value }))}
            placeholder="E.g. We sell handmade furniture. Be warm, keep answers short, and offer to connect people with our team for custom orders."
          />
          <Button type="submit">Save changes</Button>
          {saved && (
            <p role="status" className="text-sm">
              {saved}
            </p>
          )}
        </form>
        <section
          className="flex min-h-[28rem] flex-col rounded-xl border border-border bg-card p-5"
          aria-label="Playground"
        >
          <h2 className="text-xl font-semibold">Playground</h2>
          <p className="text-sm text-muted-foreground">
            Uses your saved configuration. Save changes before testing.
          </p>
          <div className="mt-3 flex-1 space-y-3 overflow-y-auto" aria-live="polite">
            {messages.length === 0 && (
              <p className="text-sm text-muted-foreground">Ask something a customer might ask.</p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 ${m.role === "user" ? "ml-auto bg-primary text-primary-foreground" : "bg-muted"}`}
              >
                {m.content}
                {m.generated === false && (
                  <p className="mt-1 text-xs text-muted-foreground">{FALLBACK_REPLY_NOTICE}</p>
                )}
              </div>
            ))}
            {thinking && (
              <p className="flex items-center gap-2 text-sm">
                <Loader2 className="size-4 animate-spin" />
                Thinking…
              </p>
            )}
            <div ref={endRef} />
          </div>
          {chatError && <Notice kind="error">{chatError}</Notice>}
          <form onSubmit={send} className="mt-3 flex gap-2">
            <label htmlFor="chat-in" className="sr-only">
              Message
            </label>
            <input
              id="chat-in"
              className="flex-1 rounded-md border border-input bg-background px-3 py-2"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message"
            />
            <Button type="submit" disabled={thinking || !input.trim()} aria-label="Send">
              <Send />
            </Button>
          </form>
        </section>
      </div>
    </StudioFrame>
  );
}
