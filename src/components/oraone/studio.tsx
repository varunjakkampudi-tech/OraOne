import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, Bot, Loader2, LogOut, Plus, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
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
import { Brand } from "./shell";
import { Notice } from "./studio-ui";

type Workspace = { id: string; name: string; website: string | null };
type Assistant = { id: string; name: string; purpose: string; instructions: string };
type ChatTurn = { role: "user" | "assistant"; content: string };

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

// Secondary screens live under "More" so the main navigation stays short.
const MORE_LINKS = [
  { to: "/studio/integrations", label: "Integrations" },
  { to: "/studio/webhooks", label: "Webhooks" },
  { to: "/studio/team", label: "Team" },
  { to: "/studio/analytics", label: "Analytics" },
  { to: "/studio/billing", label: "Billing" },
  { to: "/studio/api-keys", label: "API keys" },
  { to: "/studio/account", label: "Account" },
] as const;

export function StudioFrame({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  useEffect(() => {
    getMe()
      .then((me) => setEmail(me.email))
      .catch(() => setEmail(""));
  }, []);
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-b border-border px-5 py-3">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <Link to="/studio" aria-label="My OraOne workspaces">
            <Brand />
          </Link>
          <nav
            aria-label="Studio sections"
            className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm font-medium"
          >
            <Link to="/studio" className="hover:underline">
              Assistants
            </Link>
            <Link to="/studio/inbox" className="hover:underline">
              Inbox
            </Link>
            <Link to="/studio/leads" className="hover:underline">
              Leads
            </Link>
            <Link to="/studio/knowledge" className="hover:underline">
              Knowledge
            </Link>
            <details className="relative">
              <summary className="cursor-pointer list-none hover:underline">More</summary>
              <div className="absolute left-0 z-20 mt-2 grid w-56 gap-1 rounded-lg border border-border bg-background p-2 shadow-lg">
                {MORE_LINKS.map((item) => (
                  <Link key={item.to} to={item.to} className="rounded-md px-3 py-2 hover:bg-muted">
                    {item.label}
                  </Link>
                ))}
              </div>
            </details>
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="hidden sm:inline text-muted-foreground">{email}</span>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              await logout().catch(() => undefined);
              navigate({ to: "/auth/sign-in", replace: true });
            }}
          >
            <LogOut />
            Sign out
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-5 py-8 text-base">{children}</main>
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
  }, [load]);

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
  }, [selected]);

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
  return (
    <StudioFrame>
      <span className="marketing-eyebrow">LIVE · YOUR ACCOUNT</span>
      <h1 className="mt-2 text-3xl font-semibold">Your assistants</h1>
      <p className="mt-2 text-muted-foreground">
        Create an assistant, teach it from your content and add it to your website. Everything is
        saved to your account.
      </p>
      {error && (
        <div className="mt-4">
          <Notice kind="error">{error}</Notice>
        </div>
      )}
      {workspaces === null ? (
        <p className="mt-8 flex items-center gap-2">
          <Loader2 className="animate-spin" />
          Loading…
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
              <p className="text-muted-foreground">Setting up your workspace…</p>
            ) : assistants.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border p-6 text-muted-foreground">
                You don&apos;t have an assistant yet. Create one to start answering customers.
              </p>
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
      setMessages((m) => [...m, { role: "assistant", content: result.assistant_message.content }]);
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
          <Link to="/studio">
            <ArrowLeft />
            Back to workspaces
          </Link>
        </Button>
      </StudioFrame>
    );
  return (
    <StudioFrame>
      <Link to="/studio" className="inline-flex items-center gap-1 text-sm">
        <ArrowLeft className="size-4" />
        Workspaces
      </Link>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold">{assistant.name}</h1>
        <Button asChild>
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
          <h2 className="text-xl font-semibold">
            Playground{" "}
            <span className="ml-2 rounded-full bg-accent px-2 py-0.5 text-sm font-medium">
              Live AI
            </span>
          </h2>
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
