import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  Code2,
  Copy,
  Check,
  KeyRound,
  Webhook as WebhookIcon,
  Play,
  Loader2,
  ExternalLink,
  Terminal,
  BookOpen,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { API_BASE } from "@/lib/api";

const V1_BASE = `${API_BASE}/v1`;
const OPENAPI_URL = API_BASE.replace(/\/api$/, "") + "/openapi.json";

const ENDPOINTS = [
  { group: "Core", method: "GET", path: "/v1/ping", scope: "—", desc: "Verify your key and view granted scopes." },
  { group: "Agents", method: "GET", path: "/v1/agents", scope: "agents:read", desc: "List agents in your organization." },
  { group: "Chat", method: "POST", path: "/v1/chat", scope: "chat:write", desc: "Ask a question; returns a grounded answer with sources." },
  { group: "Chat", method: "GET", path: "/v1/conversations", scope: "chat:read", desc: "List recent conversations." },
  { group: "Chat", method: "GET", path: "/v1/conversations/{id}", scope: "chat:read", desc: "Fetch a conversation with its messages." },
  { group: "Knowledge", method: "GET", path: "/v1/knowledge-bases", scope: "knowledge:read", desc: "List knowledge bases." },
  { group: "Knowledge", method: "GET", path: "/v1/documents", scope: "documents:read", desc: "List documents (optionally by knowledge base)." },
  { group: "Knowledge", method: "GET", path: "/v1/websites", scope: "websites:read", desc: "List crawled websites." },
  { group: "Knowledge", method: "POST", path: "/v1/search", scope: "search:read", desc: "Hybrid semantic + keyword search across your knowledge." },
  { group: "Automation", method: "GET", path: "/v1/workflows", scope: "workflows:read", desc: "List workflows." },
  { group: "Automation", method: "POST", path: "/v1/workflows/{id}/run", scope: "workflows:execute", desc: "Trigger a workflow run." },
  { group: "Surfaces", method: "GET", path: "/v1/widgets", scope: "widgets:read", desc: "List embedded chat widgets." },
  { group: "Surfaces", method: "GET", path: "/v1/integrations", scope: "integrations:read", desc: "List connected integrations." },
  { group: "Insights", method: "GET", path: "/v1/usage", scope: "usage:read", desc: "Current billing-period usage." },
  { group: "Insights", method: "GET", path: "/v1/analytics/overview", scope: "analytics:read", desc: "Organization analytics snapshot." },
  { group: "Insights", method: "GET", path: "/v1/analytics/{module}", scope: "analytics:read", desc: "Module analytics: cost, executive, chat, agents, rag, widget, workflows…" },
];

const METHOD_STYLES = {
  GET: "bg-[#DCFCE7] text-[#16A34A]",
  POST: "bg-[#DBEAFE] text-[#2563EB]",
  PATCH: "bg-[#FEF3C7] text-[#B45309]",
  DELETE: "bg-[#FEE2E2] text-[#DC2626]",
};

function CopyButton({ text, label = "Copy" }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      toast.error("Couldn't copy.");
    }
  };
  return (
    <button
      onClick={copy}
      className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-2.5 py-1.5 text-[12px] font-medium text-[#475569] hover:bg-[#F8FAFC]"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-[#16A34A]" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : label}
    </button>
  );
}

function CodeBlock({ code }) {
  return (
    <div className="relative">
      <div className="absolute right-2 top-2">
        <CopyButton text={code} />
      </div>
      <pre className="overflow-x-auto rounded-xl border border-[#1E293B] bg-[#0F172A] p-4 pt-12 font-mono text-[12.5px] leading-relaxed text-[#E2E8F0]">
        {code}
      </pre>
    </div>
  );
}

function MethodBadge({ method }) {
  return (
    <span className={`inline-flex w-14 justify-center rounded-md px-2 py-0.5 text-[11px] font-bold ${METHOD_STYLES[method] || "bg-[#F1F5F9] text-[#475569]"}`}>
      {method}
    </span>
  );
}

export default function Developers() {
  const [lang, setLang] = useState("curl");
  const [playKey, setPlayKey] = useState("");
  const [playMsg, setPlayMsg] = useState("What can you help me with?");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  // Per-endpoint "Try it" runner state.
  const [rowBusy, setRowBusy] = useState(null);
  const [rowResult, setRowResult] = useState({});

  const samples = useMemo(() => {
    const key = playKey.trim() || "sk_ora_xxx";
    return {
      curl: `curl -X POST ${V1_BASE}/chat \\
  -H "Authorization: Bearer ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{"message": "What is your refund policy?", "top_k": 4}'`,
      javascript: `const res = await fetch("${V1_BASE}/chat", {
  method: "POST",
  headers: {
    Authorization: "Bearer ${key}",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ message: "What is your refund policy?", top_k: 4 }),
});
const data = await res.json();
console.log(data.answer, data.sources);`,
      python: `import requests

res = requests.post(
    "${V1_BASE}/chat",
    headers={"Authorization": "Bearer ${key}"},
    json={"message": "What is your refund policy?", "top_k": 4},
)
data = res.json()
print(data["answer"], data["sources"])`,
    };
  }, [playKey]);

  const runPlayground = async (kind) => {
    const key = playKey.trim();
    if (!key) {
      toast.error("Paste an API key to run a live request.");
      return;
    }
    setRunning(true);
    setResult(null);
    try {
      const opts = {
        headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      };
      let res;
      if (kind === "chat") {
        res = await fetch(`${V1_BASE}/chat`, {
          ...opts,
          method: "POST",
          body: JSON.stringify({ message: playMsg, top_k: 4 }),
        });
      } else {
        res = await fetch(`${V1_BASE}/ping`, opts);
      }
      const json = await res.json();
      setResult({ status: res.status, ok: res.ok, body: json });
    } catch (e) {
      setResult({ status: 0, ok: false, body: { error: String(e) } });
    } finally {
      setRunning(false);
    }
  };

  const grouped = useMemo(() => {
    const map = {};
    ENDPOINTS.forEach((e) => {
      (map[e.group] = map[e.group] || []).push(e);
    });
    return Object.entries(map);
  }, []);

  // Run any read-only (GET, no path params) endpoint live from the reference.
  const runEndpoint = async (path) => {
    const key = playKey.trim();
    if (!key) {
      toast.error("Paste an API key in the playground above to try endpoints.");
      return;
    }
    setRowBusy(path);
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        headers: { Authorization: `Bearer ${key}` },
      });
      const json = await res.json().catch(() => ({}));
      setRowResult((prev) => ({ ...prev, [path]: { status: res.status, ok: res.ok, body: json } }));
    } catch (e) {
      setRowResult((prev) => ({ ...prev, [path]: { status: 0, ok: false, body: { error: String(e) } } }));
    } finally {
      setRowBusy(null);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-5xl space-y-8 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#EEF2FF] text-[#4F46E5]">
          <Code2 className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#0F172A]">Developer Platform</h1>
          <p className="text-sm text-[#64748B]">Build on OraOne with a scoped, rate-limited REST API.</p>
        </div>
      </div>

      {/* Quick start cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Link to="/app/api-keys" className="group rounded-2xl border border-[#E2E8F0] bg-white p-5 transition hover:border-[#4F46E5]">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#EEF2FF] text-[#4F46E5]">
            <KeyRound className="h-5 w-5" />
          </div>
          <p className="mt-3 text-sm font-semibold text-[#0F172A]">1. Create an API key</p>
          <p className="mt-1 text-[13px] text-[#64748B]">Scope it to only the data and actions you need.</p>
        </Link>
        <div className="rounded-2xl border border-[#E2E8F0] bg-white p-5">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#DCFCE7] text-[#16A34A]">
            <Terminal className="h-5 w-5" />
          </div>
          <p className="mt-3 text-sm font-semibold text-[#0F172A]">2. Call the API</p>
          <div className="mt-2 flex items-center gap-2">
            <code className="truncate rounded-md bg-[#F1F5F9] px-2 py-1 font-mono text-[11px] text-[#475569]">{V1_BASE}</code>
            <CopyButton text={V1_BASE} label="" />
          </div>
        </div>
        <Link to="/app/webhooks" className="group rounded-2xl border border-[#E2E8F0] bg-white p-5 transition hover:border-[#4F46E5]">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#FEF3C7] text-[#B45309]">
            <WebhookIcon className="h-5 w-5" />
          </div>
          <p className="mt-3 text-sm font-semibold text-[#0F172A]">3. Subscribe to events</p>
          <p className="mt-1 text-[13px] text-[#64748B]">Receive signed webhooks in real time.</p>
        </Link>
      </div>

      {/* Auth note */}
      <div className="flex items-start gap-3 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-5">
        <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-[#4F46E5]" />
        <div className="text-[13px] text-[#475569]">
          <p className="font-semibold text-[#0F172A]">Authentication</p>
          <p className="mt-1">
            Pass your key as a bearer token:{" "}
            <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[12px] text-[#0F172A]">Authorization: Bearer sk_ora_…</code>. Requests are
            rate-limited per plan and support an <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[12px]">Idempotency-Key</code> header on writes.
          </p>
        </div>
      </div>

      {/* Code samples */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-[#0F172A]">Send your first chat request</h3>
          <div className="inline-flex rounded-xl border border-[#E2E8F0] bg-white p-1">
            {[
              { key: "curl", label: "cURL" },
              { key: "javascript", label: "JavaScript" },
              { key: "python", label: "Python" },
            ].map((l) => (
              <button
                key={l.key}
                onClick={() => setLang(l.key)}
                className={`rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors ${
                  lang === l.key ? "bg-[#2563EB] text-white" : "text-[#475569] hover:bg-[#F8FAFC]"
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4">
          <CodeBlock code={samples[lang]} />
        </div>
      </div>

      {/* Playground */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6">
        <h3 className="text-base font-semibold text-[#0F172A]">API playground</h3>
        <p className="mt-1 text-[13px] text-[#64748B]">Run a live request against your organization. Your key stays in the browser.</p>
        <div className="mt-4 space-y-3">
          <input
            value={playKey}
            onChange={(e) => setPlayKey(e.target.value)}
            data-testid="playground-key"
            placeholder="sk_ora_…  (paste an API key)"
            className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 font-mono text-[13px] outline-none focus:border-[#4F46E5]"
          />
          <div className="flex flex-wrap gap-2">
            <input
              value={playMsg}
              onChange={(e) => setPlayMsg(e.target.value)}
              placeholder="Message for /v1/chat"
              className="flex-1 rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
            <button
              onClick={() => runPlayground("ping")}
              disabled={running}
              data-testid="playground-ping"
              className="inline-flex items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-60"
            >
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} Ping
            </button>
            <button
              onClick={() => runPlayground("chat")}
              disabled={running}
              data-testid="playground-chat"
              className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-3 py-2 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60"
            >
              {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} Run chat
            </button>
          </div>
          {result && (
            <div className="mt-2">
              <div className="mb-1 flex items-center gap-2 text-[12px]">
                <span className={`rounded-md px-2 py-0.5 font-semibold ${result.ok ? "bg-[#DCFCE7] text-[#16A34A]" : "bg-[#FEE2E2] text-[#DC2626]"}`}>
                  {result.status || "ERR"}
                </span>
                <span className="text-[#94A3B8]">Response</span>
              </div>
              <pre className="max-h-72 overflow-auto rounded-xl border border-[#1E293B] bg-[#0F172A] p-4 font-mono text-[12px] leading-relaxed text-[#E2E8F0]">
                {JSON.stringify(result.body, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* Endpoint reference */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-[#0F172A]">API reference</h3>
          <a
            href={OPENAPI_URL}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-2.5 py-1.5 text-[12px] font-medium text-[#475569] hover:bg-[#F8FAFC]"
          >
            <ExternalLink className="h-3.5 w-3.5" /> OpenAPI schema
          </a>
        </div>
        <div className="mt-4 space-y-6">
          {grouped.map(([group, rows]) => (
            <div key={group}>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-[#94A3B8]">{group}</p>
              <div className="overflow-hidden rounded-xl border border-[#E2E8F0]">
                {rows.map((e, i) => {
                  const tryable = e.method === "GET" && !e.path.includes("{");
                  const res = rowResult[e.path];
                  const busy = rowBusy === e.path;
                  return (
                    <div
                      key={e.path + e.method}
                      className={`flex flex-wrap items-center gap-3 px-4 py-3 ${i % 2 ? "bg-[#F8FAFC]" : "bg-white"}`}
                    >
                      <MethodBadge method={e.method} />
                      <code className="font-mono text-[13px] font-medium text-[#0F172A]">{e.path}</code>
                      <span className="ml-auto rounded-md bg-[#EEF2FF] px-2 py-0.5 font-mono text-[11px] text-[#4F46E5]">{e.scope}</span>
                      {tryable && (
                        <button
                          onClick={() => runEndpoint(e.path)}
                          disabled={busy}
                          data-testid={`try-${e.path}`}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] bg-white px-2.5 py-1 text-[12px] font-medium text-[#4F46E5] hover:bg-[#EEF2FF] disabled:opacity-60"
                        >
                          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />} Try it
                        </button>
                      )}
                      <p className="w-full text-[12.5px] text-[#64748B]">{e.desc}</p>
                      {res && (
                        <div className="w-full">
                          <div className="mb-1 flex items-center gap-2 text-[12px]">
                            <span className={`rounded-md px-2 py-0.5 font-semibold ${res.ok ? "bg-[#DCFCE7] text-[#16A34A]" : "bg-[#FEE2E2] text-[#DC2626]"}`}>
                              {res.status || "ERR"}
                            </span>
                            <span className="text-[#94A3B8]">Live response</span>
                          </div>
                          <pre className="max-h-60 overflow-auto rounded-xl border border-[#1E293B] bg-[#0F172A] p-3 font-mono text-[11.5px] leading-relaxed text-[#E2E8F0]">
                            {JSON.stringify(res.body, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Resources */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <a
          href={OPENAPI_URL}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 rounded-2xl border border-[#E2E8F0] bg-white p-5 transition hover:border-[#4F46E5]"
        >
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#EEF2FF] text-[#4F46E5]">
            <BookOpen className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[#0F172A]">OpenAPI / Postman</p>
            <p className="text-[13px] text-[#64748B]">Import the schema URL into Postman or Insomnia.</p>
          </div>
        </a>
        <Link to="/app/webhooks" className="flex items-center gap-3 rounded-2xl border border-[#E2E8F0] bg-white p-5 transition hover:border-[#4F46E5]">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#FEF3C7] text-[#B45309]">
            <WebhookIcon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[#0F172A]">Webhooks &amp; signatures</p>
            <p className="text-[13px] text-[#64748B]">Subscribe to events and verify HMAC signatures.</p>
          </div>
        </Link>
      </div>
    </motion.div>
  );
}
