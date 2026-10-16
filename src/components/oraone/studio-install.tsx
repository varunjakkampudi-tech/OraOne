import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Check, Copy, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/client";
import { getAgent, type Agent } from "@/lib/api/studio";
import {
  createWidget,
  listWidgets,
  setWidgetPublished,
  updateWidgetDomains,
  type Widget,
} from "@/lib/api/widgets";
import { Loading, Notice } from "./studio-ui";
import { when, useWorkspaceId } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";

// Connects one assistant to a website. The owner creates a chat widget for the
// assistant, lists the domains allowed to load it, publishes it, and copies the
// install code: a script tag, the browser SDK, or a React/Next.js component.

type Tab = "script" | "sdk" | "react";

const TABS: { id: Tab; label: string }[] = [
  { id: "script", label: "Script tag" },
  { id: "sdk", label: "Browser SDK" },
  { id: "react", label: "React / Next.js" },
];

// The loader is served by the same origin as this app, which proxies /api to the
// backend, so the snippet needs no extra configuration in any environment.
function embedTag(publicKey: string): string {
  const origin = typeof window === "undefined" ? "" : window.location.origin;
  return `<script src="${origin}/widget.js" data-widget-id="${publicKey}" async></script>`;
}

function sdkCode(widget: Widget): string {
  return [
    embedTag(widget.public_key),
    "<script>",
    "  // Available after the widget script has loaded.",
    "  window.addEventListener('load', function () {",
    "    window.OraOne.identify({ plan: 'pro' }); // optional, non-secret context",
    "    document.querySelector('#help-button').addEventListener('click', function () {",
    "      window.OraOne.open();",
    "    });",
    "  });",
    "</script>",
  ].join("\n");
}

function reactCode(widget: Widget): string {
  return [
    "import { useEffect } from 'react';",
    "",
    "// Load the widget once. It renders its own launcher.",
    "export function OraOneChat() {",
    "  useEffect(() => {",
    "    const script = document.createElement('script');",
    `    script.src = '${typeof window === "undefined" ? "" : window.location.origin}/widget.js';`,
    `    script.setAttribute('data-widget-id', '${widget.public_key}');`,
    "    script.async = true;",
    "    document.body.appendChild(script);",
    "    return () => {",
    "      window.OraOne?.destroy();",
    "      script.remove();",
    "    };",
    "  }, []);",
    "  return null;",
    "}",
  ].join("\n");
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 2000);
        } catch {
          setCopied(false);
        }
      }}
    >
      {copied ? <Check /> : <Copy />}
      {copied ? "Copied" : label}
    </Button>
  );
}

function CodeBlock({ code, label }: { code: string; label: string }) {
  return (
    <div className="space-y-3">
      <pre
        tabIndex={0}
        aria-label={label}
        className="overflow-x-auto rounded-lg bg-muted p-4 text-sm leading-relaxed"
      >
        <code>{code}</code>
      </pre>
      <CopyButton text={code} label="Copy code" />
    </div>
  );
}

function InstallPanel({ widget }: { widget: Widget }) {
  const [tab, setTab] = useState<Tab>("script");
  const code =
    tab === "script"
      ? embedTag(widget.public_key)
      : tab === "sdk"
        ? sdkCode(widget)
        : reactCode(widget);

  return (
    <div className="space-y-4">
      <div role="tablist" aria-label="Install options" className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
            className={`rounded-full border px-4 py-2 text-sm font-medium ${
              tab === item.id
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      <p className="text-muted-foreground">
        {tab === "script" &&
          "Paste this line before the closing </body> tag of every page where the chat should appear."}
        {tab === "sdk" &&
          "Use the SDK to open the chat from your own button, or to send messages and pass non-secret visitor details."}
        {tab === "react" &&
          "Add this component to your app once. It loads the widget on the client."}
      </p>
      <CodeBlock code={code} label={`${TABS.find((t) => t.id === tab)?.label} code`} />
      {tab === "sdk" && (
        <p className="text-sm text-muted-foreground">
          SDK methods: <code>open()</code>, <code>close()</code>, <code>toggle()</code>,{" "}
          <code>send(text)</code>, <code>identify(context)</code>, <code>destroy()</code>.
        </p>
      )}
    </div>
  );
}

function WidgetSettings({ widget, onChange }: { widget: Widget; onChange: (w: Widget) => void }) {
  const [domains, setDomains] = useState(widget.domains.join("\n"));
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      const list = domains
        .split(/[\n,]/)
        .map((d) => d.trim())
        .filter(Boolean);
      onChange(await updateWidgetDomains(widget.id, list));
      setMessage("Domains saved.");
    } catch (err) {
      setMessage(messageOf(err, "Couldn't save the domains."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <label
        htmlFor="widget-domains"
        className="block text-sm font-semibold uppercase tracking-wide text-muted-foreground"
      >
        Allowed websites
      </label>
      <p className="text-sm text-muted-foreground">
        One domain per line, for example <code>example.com</code>. Leave empty to allow any site.
      </p>
      <textarea
        id="widget-domains"
        value={domains}
        onChange={(e) => setDomains(e.target.value)}
        rows={3}
        className="w-full rounded-lg border border-input bg-background p-3 text-base"
      />
      <div className="flex items-center gap-3">
        <Button onClick={save} disabled={busy}>
          Save domains
        </Button>
        {message && (
          <span role="status" className="text-sm text-muted-foreground">
            {message}
          </span>
        )}
      </div>
    </div>
  );
}

function Publishing({ widget, onChange }: { widget: Widget; onChange: (w: Widget) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const live = widget.status === "published";

  async function toggle() {
    setBusy(true);
    setError("");
    try {
      onChange(await setWidgetPublished(widget.id, !live));
    } catch (err) {
      setError(messageOf(err, "Couldn't change the status. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border p-5">
      <div>
        <p className="font-semibold">{live ? "Live on your website" : "Not live yet"}</p>
        <p className="text-sm text-muted-foreground">
          {live
            ? "Visitors on allowed websites can chat with this assistant."
            : "Publish when the code is installed. Visitors see nothing until then."}
        </p>
      </div>
      <Button variant={live ? "outline" : "default"} onClick={toggle} disabled={busy}>
        {live ? "Pause widget" : "Publish widget"}
      </Button>
      {error && <Notice kind="error">{error}</Notice>}
    </div>
  );
}

export function StudioInstall({ assistantId }: { assistantId: string }) {
  const workspace = useWorkspaceId();
  const [agent, setAgent] = useState<Agent | null | undefined>(undefined);
  const [widget, setWidget] = useState<Widget | null | undefined>(undefined);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!workspace.loaded) return;
    if (!workspace.id) {
      setError(workspace.error || "Create a workspace first.");
      setAgent(null);
      return;
    }
    let cancelled = false;
    Promise.all([getAgent(assistantId), listWidgets(workspace.id)])
      .then(([found, list]) => {
        if (cancelled) return;
        setAgent(found);
        setWidget(list.items.find((w) => w.agent_id === assistantId) ?? null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(messageOf(err, "Couldn't load this assistant."));
        setAgent(null);
      });
    return () => {
      cancelled = true;
    };
  }, [assistantId, workspace.loaded, workspace.id, workspace.error]);

  async function create() {
    if (!workspace.id || !agent) return;
    setCreating(true);
    setError("");
    try {
      setWidget(
        await createWidget(workspace.id, {
          name: `${agent.name} on website`,
          agent_id: assistantId,
          domains: [],
        }),
      );
    } catch (err) {
      setError(messageOf(err, "Couldn't create the widget. Please try again."));
    } finally {
      setCreating(false);
    }
  }

  const back = (
    <Link
      to="/studio/assistants/$id"
      params={{ id: assistantId }}
      className="inline-flex items-center gap-2 text-sm font-medium hover:underline"
    >
      <ArrowLeft className="size-4" />
      Back to assistant
    </Link>
  );

  if (agent === undefined || widget === undefined) {
    return (
      <StudioFrame>
        <Loading label="Loading install options…" />
      </StudioFrame>
    );
  }
  if (agent === null) {
    return (
      <StudioFrame>
        <Notice kind="error">
          {error || "This assistant doesn't exist or you don't have access to it."}
        </Notice>
      </StudioFrame>
    );
  }

  return (
    <StudioFrame>
      <div className="space-y-8">
        {back}
        <header className="space-y-2">
          <p className="text-sm font-medium text-primary">Install</p>
          <h1 className="text-3xl font-semibold tracking-tight">
            Add {agent.name} to your website
          </h1>
          <p className="max-w-2xl text-muted-foreground">
            Create a chat widget for this assistant, allow your domains, then paste one line of
            code.
          </p>
        </header>

        {error && <Notice kind="error">{error}</Notice>}

        {!widget ? (
          <section className="space-y-4 rounded-xl border border-border p-6">
            <h2 className="text-xl font-semibold">Step 1 · Create the chat widget</h2>
            <p className="text-muted-foreground">
              The widget connects this assistant to your site and uses your workspace knowledge.
            </p>
            <Button onClick={create} disabled={creating}>
              {creating ? "Creating…" : "Create chat widget"}
            </Button>
          </section>
        ) : (
          <>
            <section className="space-y-4">
              <h2 className="text-xl font-semibold">Step 1 · Allow your websites</h2>
              <WidgetSettings widget={widget} onChange={setWidget} />
            </section>
            <section className="space-y-4">
              <h2 className="text-xl font-semibold">Step 2 · Install the code</h2>
              <InstallPanel widget={widget} />
            </section>
            <section className="space-y-4">
              <h2 className="text-xl font-semibold">Step 3 · Publish</h2>
              <Publishing widget={widget} onChange={setWidget} />
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Globe className="size-4" aria-hidden="true" />
                Need a server-side or REST integration? Create a key under API keys.
              </p>
            </section>
          </>
        )}
      </div>
    </StudioFrame>
  );
}
