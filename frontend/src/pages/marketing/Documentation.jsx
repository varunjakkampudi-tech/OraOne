import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  BookOpen,
  Code2,
  Plug,
  ShieldCheck,
  Compass,
  HelpCircle,
  Activity,
  MessageSquare,
  Clock,
  CheckCircle2,
  ChevronDown,
  Search,
  Copy,
  Check,
  ExternalLink,
  Mail,
  LifeBuoy,
  Ticket,
  Lock,
  KeyRound,
  FileCheck2,
  Cloud,
  Users,
  ArrowRight,
} from "lucide-react";
import { useSEO } from "@/lib/seo";

/* ──────────────────────────────────────────────────────────────────── */
/*  Sidebar navigation config                                           */
/* ──────────────────────────────────────────────────────────────────── */
const NAV = [
  { id: "quickstart", label: "Quick Start", icon: Compass },
  { id: "products", label: "Product Docs", icon: BookOpen },
  { id: "api", label: "API Reference", icon: Code2 },
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "security", label: "Security & Compliance", icon: ShieldCheck },
  { id: "help", label: "Help Center", icon: HelpCircle },
  { id: "status", label: "Status & Support", icon: Activity },
];

/* ──────────────────────────────────────────────────────────────────── */
/*  Quick start steps                                                   */
/* ──────────────────────────────────────────────────────────────────── */
const QUICK_STEPS = [
  { n: "01", title: "Create Account", desc: "Sign up with your work email and verify in 30 seconds.", time: "1 min" },
  { n: "02", title: "Create First Agent", desc: "Name and configure your chat agent in minutes.", time: "2 mins" },
  { n: "03", title: "Connect Website", desc: "Paste a single embed snippet into your site.", time: "3 mins" },
  { n: "04", title: "Publish Agent", desc: "Test the flow and flip the switch — your AI is live.", time: "1 min" },
];

/* ──────────────────────────────────────────────────────────────────── */
/*  Product docs                                                        */
/* ──────────────────────────────────────────────────────────────────── */
const PRODUCT_TABS = [
  {
    id: "chat",
    label: "Chat Agent",
    icon: MessageSquare,
    color: "#2563EB",
    bg: "#DBEAFE",
    topics: [
      { title: "Widget Installation", desc: "Single line of JS — works on React, Next.js, WordPress, Shopify." },
      { title: "Website Integration", desc: "Custom triggers, page targeting and visitor identification." },
      { title: "Custom Branding", desc: "Match your colours, fonts, avatar and chat tone." },
      { title: "Knowledge Base Setup", desc: "Upload PDFs, FAQs, Notion or Help docs as the source of truth." },
      { title: "Lead Forms", desc: "Inline forms with validation, hidden fields and CRM sync." },
    ],
  },
];

/* ──────────────────────────────────────────────────────────────────── */
/*  API examples                                                        */
/* ──────────────────────────────────────────────────────────────────── */
const API_ENDPOINTS = [
  {
    id: "auth",
    title: "Authentication",
    method: "—",
    path: "All requests",
    desc: "Authenticate every request with your API key in the Authorization header.",
    examples: {
      curl: `curl https://api.oraone.in/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
      js: `const res = await fetch("https://api.oraone.in/v1/agents", {
  headers: { Authorization: "Bearer YOUR_API_KEY" }
});
const data = await res.json();`,
      python: `import requests

res = requests.get(
    "https://api.oraone.in/v1/agents",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
)
print(res.json())`,
    },
  },
  {
    id: "create-agent",
    title: "Create Agent",
    method: "POST",
    path: "/v1/agents",
    desc: "Spin up a new chat agent programmatically.",
    examples: {
      curl: `curl -X POST https://api.oraone.in/v1/agents \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Sales Assistant",
    "type": "chat",
    "language": "en-IN"
  }'`,
      js: `await fetch("https://api.oraone.in/v1/agents", {
  method: "POST",
  headers: {
    Authorization: "Bearer YOUR_API_KEY",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    name: "Sales Assistant",
    type: "chat",
    language: "en-IN",
  }),
});`,
      python: `requests.post(
    "https://api.oraone.in/v1/agents",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={"name": "Sales Assistant", "type": "chat", "language": "en-IN"},
)`,
    },
  },
  {
    id: "list-conversations",
    title: "List Conversations",
    method: "GET",
    path: "/v1/conversations",
    desc: "Fetch, search and export conversations across all channels.",
    examples: {
      curl: `curl "https://api.oraone.in/v1/conversations?limit=50&channel=chat" \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
      js: `const res = await fetch(
  "https://api.oraone.in/v1/conversations?limit=50&channel=chat",
  { headers: { Authorization: "Bearer YOUR_API_KEY" } }
);`,
      python: `requests.get(
    "https://api.oraone.in/v1/conversations",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    params={"limit": 50, "channel": "chat"},
)`,
    },
  },
  {
    id: "create-lead",
    title: "Create Lead",
    method: "POST",
    path: "/v1/leads",
    desc: "Push captured leads into OraOne or pull lead details for sync.",
    examples: {
      curl: `curl -X POST https://api.oraone.in/v1/leads \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Aarav Mehta",
    "phone": "+91-9876543210",
    "source": "website",
    "intent": "demo-request"
  }'`,
      js: `await fetch("https://api.oraone.in/v1/leads", {
  method: "POST",
  headers: {
    Authorization: "Bearer YOUR_API_KEY",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    name: "Aarav Mehta",
    phone: "+91-9876543210",
    source: "website",
    intent: "demo-request",
  }),
});`,
      python: `requests.post(
    "https://api.oraone.in/v1/leads",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "name": "Aarav Mehta",
        "phone": "+91-9876543210",
        "source": "website",
        "intent": "demo-request",
    },
)`,
    },
  },
];

const API_GROUPS = [
  { title: "Agents API", items: ["Create Agent", "Update Agent", "Delete Agent", "List Agents"] },
  { title: "Conversations API", items: ["Fetch Conversations", "Search Conversations", "Export Conversations"] },
  { title: "Leads API", items: ["Create Lead", "Update Lead", "Get Lead Details"] },
];

/* ──────────────────────────────────────────────────────────────────── */
/*  Integration guides                                                  */
/* ──────────────────────────────────────────────────────────────────── */
const INTEGRATIONS = [
  {
    id: "gmail",
    name: "Gmail",
    desc: "Send lead notifications and conversation digests directly to Gmail.",
    requirements: "Google Workspace or Gmail account with admin permissions.",
    steps: [
      "Navigate to Settings → Integrations → Gmail.",
      "Click Connect and authorize OraOne with your Google account.",
      "Select the mailbox to send from and configure notification rules.",
      "Send a test email to verify delivery.",
    ],
    troubleshooting: "If emails bounce, confirm SPF/DKIM records and that the OraOne sender is whitelisted.",
    faq: "Yes — you can connect multiple Gmail accounts and route them per agent.",
  },
  {
    id: "gcal",
    name: "Google Calendar",
    desc: "Let your AI agents book and reschedule meetings on your calendar.",
    requirements: "Google account with edit access to the target calendar.",
    steps: [
      "Open Settings → Integrations → Google Calendar.",
      "Grant OraOne calendar.events scope.",
      "Pick the calendar to manage and set buffer/duration defaults.",
      "Test by asking the agent to book a slot.",
    ],
    troubleshooting: "If slots show as busy, re-run sync from the Integrations panel.",
    faq: "Yes — round-robin across multiple calendars is supported on Growth and above.",
  },
  {
    id: "hubspot",
    name: "HubSpot",
    desc: "Sync leads, contacts and deal stages bidirectionally with HubSpot CRM.",
    requirements: "HubSpot account with API access (Starter plan or higher).",
    steps: [
      "Generate a Private App token in HubSpot Settings → Integrations.",
      "Paste the token into Settings → Integrations → HubSpot.",
      "Map OraOne fields to HubSpot contact properties.",
      "Run an initial backfill from the Sync tab.",
    ],
    troubleshooting: "Duplicate contacts usually indicate a missing dedupe key — set email as primary in the mapping.",
    faq: "Bi-directional sync runs every 60 seconds; manual resync is available on demand.",
  },
  {
    id: "zoho",
    name: "Zoho CRM",
    desc: "Push qualified leads and conversation transcripts into Zoho CRM.",
    requirements: "Zoho CRM with API user access enabled.",
    steps: [
      "Create a Self Client in Zoho Developer Console.",
      "Copy the client ID / secret into OraOne.",
      "Authorize the scopes ZohoCRM.modules.ALL and ZohoCRM.settings.ALL.",
      "Verify with a test lead.",
    ],
    troubleshooting: "INVALID_TOKEN errors mean the refresh token has expired — re-authorize from Settings.",
    faq: "Yes — both Leads and Deals modules are supported with full custom-field mapping.",
  },
  {
    id: "slack",
    name: "Slack",
    desc: "Get real-time alerts when agents capture leads or escalate conversations.",
    requirements: "Slack workspace with permission to install apps.",
    steps: [
      "Open Settings → Integrations → Slack and click Add to Slack.",
      "Pick the channel for notifications.",
      "Configure rules (new lead, escalation, low-confidence reply).",
      "Send a test notification.",
    ],
    troubleshooting: "If the agent can't post, re-invite @OraOne to the target channel.",
    faq: "Yes — different rule sets can target different channels.",
  },
  {
    id: "webhooks",
    name: "Webhooks",
    desc: "Receive real-time events for any platform via signed HTTPS callbacks.",
    requirements: "Public HTTPS endpoint that can receive POST requests.",
    steps: [
      "Open Settings → Developers → Webhooks.",
      "Add an endpoint URL and pick the events to subscribe to.",
      "Copy the signing secret and verify signatures on your server.",
      "Replay events from the dashboard to test.",
    ],
    troubleshooting: "Signature mismatches usually mean clock drift — sync your server time via NTP.",
    faq: "Retries run for up to 24 hours with exponential backoff.",
  },
];

/* ──────────────────────────────────────────────────────────────────── */
/*  Security                                                            */
/* ──────────────────────────────────────────────────────────────────── */
const SECURITY = [
  { icon: Lock, title: "AES-256 Encryption", desc: "All data at rest encrypted with rotating master keys." },
  { icon: ShieldCheck, title: "TLS 1.3", desc: "End-to-end encryption in transit across every endpoint." },
  { icon: FileCheck2, title: "GDPR Compliance", desc: "DPA, DSR workflows and EU data residency available." },
  { icon: Cloud, title: "SOC 2 Roadmap", desc: "Type I in audit, Type II report targeted for Q4 2026." },
  { icon: KeyRound, title: "Audit Logs", desc: "Immutable logs for every admin and API action, 90-day retention." },
  { icon: Users, title: "RBAC Permissions", desc: "Owner, Admin, Manager and Viewer roles with scoped access." },
];

/* ──────────────────────────────────────────────────────────────────── */
/*  Help center FAQ                                                     */
/* ──────────────────────────────────────────────────────────────────── */
const FAQS = [
  {
    q: "Why is my agent not responding?",
    a: "Check the agent status in the dashboard — it must be Published. If status is Paused, click Resume. Also confirm the connected channel (Chat) shows as Connected in Settings → Channels.",
  },
  {
    q: "How do I reset API keys?",
    a: "Go to Settings → Developers → API Keys, click the three-dot menu next to the key and choose Rotate. The old key remains active for 24 hours so you can deploy the new one without downtime.",
  },
  {
    q: "Why is my website widget offline?",
    a: "Confirm the embed snippet is present in the <head> tag and that your domain is added to the allow-list in Settings → Channels → Web. CSP rules blocking *.oraone.in are the most common cause.",
  },
  {
    q: "Can I export all my conversations?",
    a: "Yes — head to Conversations → Export. You can filter by date, channel or agent and download CSV or JSON. Programmatic export is available via the /v1/conversations API.",
  },
  {
    q: "How is OraOne billed?",
    a: "Per active agent and per conversation message (Chat). See the Pricing page for tier-wise limits or contact sales for enterprise plans.",
  },
  {
    q: "Does OraOne support multiple languages?",
    a: "Yes — your chat agent auto-detects and replies in 90+ languages.",
  },
  {
    q: "How quickly can I go live?",
    a: "Most teams deploy their first agent within 24 hours.",
  },
];

/* ──────────────────────────────────────────────────────────────────── */
/*  Code block with language tabs + copy                                */
/* ──────────────────────────────────────────────────────────────────── */
function CodeBlock({ examples, endpointId }) {
  const [lang, setLang] = useState("curl");
  const [copied, setCopied] = useState(false);
  const code = examples[lang];

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  const langs = [
    { id: "curl", label: "cURL" },
    { id: "js", label: "JavaScript" },
    { id: "python", label: "Python" },
  ];

  return (
    <div className="rounded-xl overflow-hidden border border-[#1E293B] bg-[#0F172A]">
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1E293B] bg-[#0B1220]">
        <div className="flex gap-1">
          {langs.map((l) => (
            <button
              key={l.id}
              onClick={() => setLang(l.id)}
              data-testid={`code-lang-${endpointId}-${l.id}`}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                lang === l.id
                  ? "bg-[#2563EB] text-white"
                  : "text-[#94A3B8] hover:text-white hover:bg-[#1E293B]"
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
        <button
          onClick={copy}
          data-testid={`code-copy-${endpointId}`}
          className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[11px] text-[#94A3B8] hover:text-white hover:bg-[#1E293B] transition-colors"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="p-4 text-[12.5px] leading-relaxed text-[#E2E8F0] overflow-x-auto font-mono">
        <code>{code}</code>
      </pre>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Page                                                                 */
/* ──────────────────────────────────────────────────────────────────── */
export default function DocumentationPage() {
  useSEO({
    title: "Documentation — OraOne",
    description:
      "Complete OraOne docs — quick start, product guides, API reference, integrations, security, help center and status.",
  });

  const [active, setActive] = useState(NAV[0].id);
  const [productTab, setProductTab] = useState(PRODUCT_TABS[0].id);
  const [openIntegration, setOpenIntegration] = useState(null);
  const [openFaq, setOpenFaq] = useState(null);
  const [faqQuery, setFaqQuery] = useState("");

  /* scroll-spy */
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) setActive(e.target.id);
        });
      },
      { rootMargin: "-30% 0px -60% 0px", threshold: 0 }
    );
    NAV.forEach((n) => {
      const el = document.getElementById(n.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  const filteredFaqs = useMemo(() => {
    const q = faqQuery.trim().toLowerCase();
    if (!q) return FAQS;
    return FAQS.filter(
      (f) => f.q.toLowerCase().includes(q) || f.a.toLowerCase().includes(q)
    );
  }, [faqQuery]);

  const activeProduct = PRODUCT_TABS.find((t) => t.id === productTab);

  return (
    <div className="bg-white">
      {/* ===================== HERO ===================== */}
      <section className="bg-[#F8FAFC] border-b border-[#E2E8F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="max-w-3xl"
          >
            <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#EFF6FF] text-[11px] font-semibold tracking-[0.2em] text-[#2563EB]">
              <BookOpen size={11} /> DOCUMENTATION
            </span>
            <h1 className="mt-5 text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter text-[#0F172A] leading-[1.04]">
              Build, ship and scale with <span className="text-[#2563EB]">OraOne</span>.
            </h1>
            <p className="mt-4 text-base sm:text-lg text-[#64748B] leading-relaxed">
              Quick starts, product guides, API references, integration playbooks and everything else
              your team needs to take an AI agent from zero to production.
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              {NAV.map((n) => (
                <a
                  key={n.id}
                  href={`#${n.id}`}
                  data-testid={`doc-hero-pill-${n.id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-[#E2E8F0] text-xs font-medium text-[#334155] hover:border-[#2563EB] hover:text-[#2563EB] transition-colors"
                >
                  <n.icon size={12} />
                  {n.label}
                </a>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ===================== BODY (sidebar + content) ===================== */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="lg:grid lg:grid-cols-[240px_1fr] lg:gap-12">
          {/* sidebar */}
          <aside className="hidden lg:block">
            <nav className="sticky top-24 space-y-1" data-testid="doc-sidebar">
              <p className="text-[11px] font-semibold tracking-[0.2em] text-[#94A3B8] uppercase mb-3 px-3">
                On this page
              </p>
              {NAV.map((n) => {
                const isActive = active === n.id;
                return (
                  <a
                    key={n.id}
                    href={`#${n.id}`}
                    data-testid={`doc-nav-${n.id}`}
                    className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                      isActive
                        ? "bg-[#EFF6FF] text-[#2563EB] font-semibold"
                        : "text-[#475569] hover:text-[#0F172A] hover:bg-[#F8FAFC]"
                    }`}
                  >
                    <n.icon size={15} />
                    {n.label}
                  </a>
                );
              })}
            </nav>
          </aside>

          {/* content */}
          <main className="space-y-20">
            {/* ===== Quick Start ===== */}
            <section id="quickstart" className="scroll-mt-24" data-testid="section-quickstart">
              <SectionHeader
                eyebrow="QUICK START"
                title="Get your first agent live in under 15 minutes."
                subtitle="Follow these six steps in order. Each one is short, focused and unblocks the next."
              />
              <div className="mt-8 grid sm:grid-cols-2 gap-4">
                {QUICK_STEPS.map((s, i) => (
                  <motion.div
                    key={s.n}
                    initial={{ opacity: 0, y: 14 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.04 }}
                    className="p-5 rounded-2xl border border-[#E2E8F0] bg-white hover:border-[#2563EB]/30 hover:shadow-premium transition-all"
                  >
                    <div className="flex items-start justify-between">
                      <span className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">
                        STEP {s.n}
                      </span>
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#64748B] bg-[#F1F5F9] px-2 py-0.5 rounded-full">
                        <Clock size={10} /> {s.time}
                      </span>
                    </div>
                    <h3 className="mt-2 text-[15px] font-semibold text-[#0F172A]">{s.title}</h3>
                    <p className="mt-1.5 text-[13.5px] text-[#64748B] leading-relaxed">{s.desc}</p>
                  </motion.div>
                ))}
              </div>
            </section>

            {/* ===== Product Docs ===== */}
            <section id="products" className="scroll-mt-24" data-testid="section-products">
              <SectionHeader
                eyebrow="PRODUCT DOCUMENTATION"
                title="Deep dives for each OraOne agent."
                subtitle="Configure, customise and analyse the agent that fits your channel."
              />

              {/* tabs */}
              <div className="mt-8 flex flex-wrap gap-2 border-b border-[#E2E8F0] pb-1">
                {PRODUCT_TABS.map((t) => {
                  const isActive = productTab === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setProductTab(t.id)}
                      data-testid={`product-tab-${t.id}`}
                      className={`relative inline-flex items-center gap-2 px-4 py-2.5 text-sm font-semibold transition-colors ${
                        isActive ? "text-[#2563EB]" : "text-[#64748B] hover:text-[#0F172A]"
                      }`}
                    >
                      <span
                        className="size-6 rounded-md grid place-items-center"
                        style={{ background: t.bg }}
                      >
                        <t.icon size={13} style={{ color: t.color }} />
                      </span>
                      {t.label}
                      {isActive && (
                        <motion.span
                          layoutId="product-underline"
                          className="absolute left-0 right-0 -bottom-[5px] h-[2px] bg-[#2563EB]"
                        />
                      )}
                    </button>
                  );
                })}
              </div>

              {/* topics */}
              <motion.div
                key={productTab}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className="mt-6 grid sm:grid-cols-2 gap-4"
              >
                {activeProduct.topics.map((topic) => (
                  <div
                    key={topic.title}
                    className="p-5 rounded-2xl border border-[#E2E8F0] bg-white hover:border-[#2563EB]/30 hover:shadow-premium transition-all"
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="size-8 rounded-lg grid place-items-center"
                        style={{ background: activeProduct.bg }}
                      >
                        <activeProduct.icon size={14} style={{ color: activeProduct.color }} />
                      </div>
                      <h4 className="text-[14.5px] font-semibold text-[#0F172A]">{topic.title}</h4>
                    </div>
                    <p className="mt-2.5 text-[13.5px] text-[#64748B] leading-relaxed">{topic.desc}</p>
                  </div>
                ))}
              </motion.div>
            </section>

            {/* ===== API Reference ===== */}
            <section id="api" className="scroll-mt-24" data-testid="section-api">
              <SectionHeader
                eyebrow="API REFERENCE"
                title="REST API for every OraOne resource."
                subtitle="Predictable URLs, JSON bodies, key-based auth and verbose error messages."
              />

              {/* groups overview */}
              <div className="mt-8 grid sm:grid-cols-3 gap-4">
                {API_GROUPS.map((g) => (
                  <div
                    key={g.title}
                    className="p-5 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC]"
                  >
                    <h4 className="text-[14px] font-bold text-[#0F172A]">{g.title}</h4>
                    <ul className="mt-3 space-y-1.5">
                      {g.items.map((i) => (
                        <li
                          key={i}
                          className="flex items-center gap-2 text-[13px] text-[#475569]"
                        >
                          <CheckCircle2 size={12} className="text-[#2563EB]" />
                          {i}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>

              {/* endpoint examples */}
              <div className="mt-10 space-y-8">
                {API_ENDPOINTS.map((e) => (
                  <div
                    key={e.id}
                    className="rounded-2xl border border-[#E2E8F0] overflow-hidden bg-white"
                    data-testid={`api-endpoint-${e.id}`}
                  >
                    <div className="p-5 sm:p-6 border-b border-[#E2E8F0]">
                      <div className="flex flex-wrap items-center gap-2">
                        {e.method !== "—" && (
                          <span
                            className={`px-2 py-0.5 rounded-md text-[10.5px] font-bold tracking-wider ${
                              e.method === "POST"
                                ? "bg-[#DCFCE7] text-[#15803D]"
                                : e.method === "GET"
                                ? "bg-[#DBEAFE] text-[#1D4ED8]"
                                : "bg-[#F1F5F9] text-[#475569]"
                            }`}
                          >
                            {e.method}
                          </span>
                        )}
                        <code className="text-[13px] font-mono text-[#0F172A] break-all">{e.path}</code>
                      </div>
                      <h4 className="mt-2 text-lg font-bold text-[#0F172A]">{e.title}</h4>
                      <p className="mt-1 text-[13.5px] text-[#64748B]">{e.desc}</p>
                    </div>
                    <div className="p-5 sm:p-6 bg-[#F8FAFC]">
                      <CodeBlock examples={e.examples} endpointId={e.id} />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* ===== Integrations ===== */}
            <section id="integrations" className="scroll-mt-24" data-testid="section-integrations">
              <SectionHeader
                eyebrow="INTEGRATION GUIDES"
                title="Connect OraOne to the tools you already use."
                subtitle="Every integration includes requirements, setup, troubleshooting and FAQs."
              />
              <div className="mt-8 space-y-3">
                {INTEGRATIONS.map((it) => {
                  const isOpen = openIntegration === it.id;
                  return (
                    <div
                      key={it.id}
                      className="rounded-2xl border border-[#E2E8F0] bg-white overflow-hidden"
                    >
                      <button
                        onClick={() => setOpenIntegration(isOpen ? null : it.id)}
                        data-testid={`integration-toggle-${it.id}`}
                        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-[#F8FAFC] transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <div className="size-9 rounded-xl bg-[#EFF6FF] grid place-items-center">
                            <Plug size={16} className="text-[#2563EB]" />
                          </div>
                          <div>
                            <h4 className="text-[14.5px] font-semibold text-[#0F172A]">{it.name}</h4>
                            <p className="text-[12.5px] text-[#64748B] mt-0.5">{it.desc}</p>
                          </div>
                        </div>
                        <ChevronDown
                          size={18}
                          className={`text-[#94A3B8] transition-transform ${isOpen ? "rotate-180" : ""}`}
                        />
                      </button>
                      {isOpen && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          className="px-5 pb-5 grid md:grid-cols-2 gap-5 border-t border-[#E2E8F0] pt-5"
                          data-testid={`integration-panel-${it.id}`}
                        >
                          <div>
                            <p className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">
                              REQUIREMENTS
                            </p>
                            <p className="mt-1.5 text-[13.5px] text-[#475569]">{it.requirements}</p>
                            <p className="mt-4 text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">
                              TROUBLESHOOTING
                            </p>
                            <p className="mt-1.5 text-[13.5px] text-[#475569]">{it.troubleshooting}</p>
                            <p className="mt-4 text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">
                              FAQ
                            </p>
                            <p className="mt-1.5 text-[13.5px] text-[#475569]">{it.faq}</p>
                          </div>
                          <div>
                            <p className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">
                              SETUP STEPS
                            </p>
                            <ol className="mt-1.5 space-y-2">
                              {it.steps.map((step, idx) => (
                                <li
                                  key={idx}
                                  className="flex gap-2.5 text-[13.5px] text-[#475569]"
                                >
                                  <span className="flex-shrink-0 size-5 rounded-full bg-[#EFF6FF] text-[#2563EB] text-[11px] font-bold grid place-items-center">
                                    {idx + 1}
                                  </span>
                                  <span>{step}</span>
                                </li>
                              ))}
                            </ol>
                          </div>
                        </motion.div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            {/* ===== Security ===== */}
            <section id="security" className="scroll-mt-24" data-testid="section-security">
              <SectionHeader
                eyebrow="SECURITY & COMPLIANCE"
                title="Enterprise-grade security from day one."
                subtitle="Encryption, compliance, audit and access controls baked in."
              />
              <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {SECURITY.map((s) => (
                  <div
                    key={s.title}
                    className="p-5 rounded-2xl border border-[#E2E8F0] bg-white hover:border-[#2563EB]/30 hover:shadow-premium transition-all"
                  >
                    <div className="size-10 rounded-xl bg-[#EFF6FF] grid place-items-center">
                      <s.icon size={18} className="text-[#2563EB]" />
                    </div>
                    <h4 className="mt-3.5 text-[14.5px] font-semibold text-[#0F172A]">{s.title}</h4>
                    <p className="mt-1.5 text-[13px] text-[#64748B] leading-relaxed">{s.desc}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* ===== Help Center ===== */}
            <section id="help" className="scroll-mt-24" data-testid="section-help">
              <SectionHeader
                eyebrow="HELP CENTER"
                title="Answers to the most asked questions."
                subtitle="Can't find what you need? Email support@oraone.in and we'll respond within 4 business hours."
              />

              {/* search */}
              <div className="mt-6 relative max-w-xl">
                <Search
                  size={16}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#94A3B8] pointer-events-none"
                />
                <input
                  type="text"
                  value={faqQuery}
                  onChange={(e) => setFaqQuery(e.target.value)}
                  placeholder="Search FAQs…"
                  data-testid="faq-search"
                  className="w-full pl-10 pr-4 py-3 rounded-xl border border-[#E2E8F0] bg-white text-sm placeholder:text-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10 transition-all"
                />
              </div>

              <div className="mt-6 space-y-3">
                {filteredFaqs.length === 0 && (
                  <p
                    data-testid="faq-empty"
                    className="text-sm text-[#64748B] py-4"
                  >
                    No results for &quot;{faqQuery}&quot;. Try a different phrase or contact support.
                  </p>
                )}
                {filteredFaqs.map((f, idx) => {
                  const isOpen = openFaq === idx;
                  return (
                    <div
                      key={f.q}
                      className="rounded-xl border border-[#E2E8F0] bg-white overflow-hidden"
                    >
                      <button
                        onClick={() => setOpenFaq(isOpen ? null : idx)}
                        data-testid={`faq-toggle-${idx}`}
                        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-[#F8FAFC] transition-colors"
                      >
                        <span className="text-[14px] font-semibold text-[#0F172A] pr-4">{f.q}</span>
                        <ChevronDown
                          size={16}
                          className={`flex-shrink-0 text-[#94A3B8] transition-transform ${
                            isOpen ? "rotate-180" : ""
                          }`}
                        />
                      </button>
                      {isOpen && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: "auto" }}
                          className="px-5 pb-4 text-[13.5px] text-[#475569] leading-relaxed border-t border-[#E2E8F0] pt-4"
                          data-testid={`faq-answer-${idx}`}
                        >
                          {f.a}
                        </motion.div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            {/* ===== Status & Support ===== */}
            <section id="status" className="scroll-mt-24" data-testid="section-status">
              <SectionHeader
                eyebrow="STATUS & SUPPORT"
                title="We're here when you need us."
                subtitle="Live system status, incident history and four ways to reach our team."
              />

              {/* status pill */}
              <div
                className="mt-6 inline-flex items-center gap-3 px-4 py-3 rounded-2xl bg-[#ECFDF5] border border-[#A7F3D0]"
                data-testid="platform-status"
              >
                <span className="relative flex size-2.5">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-[#10B981] opacity-60 animate-ping" />
                  <span className="relative inline-flex rounded-full size-2.5 bg-[#10B981]" />
                </span>
                <div>
                  <p className="text-[13px] font-semibold text-[#065F46]">
                    All systems operational
                  </p>
                  <p className="text-[11.5px] text-[#047857]">
                    Last incident — none in the past 30 days
                  </p>
                </div>
              </div>

              {/* incident history */}
              <div className="mt-6 rounded-2xl border border-[#E2E8F0] bg-white overflow-hidden">
                <div className="px-5 py-4 border-b border-[#E2E8F0]">
                  <p className="text-[13px] font-bold text-[#0F172A]">Incident history</p>
                </div>
                <ul className="divide-y divide-[#E2E8F0]">
                  {[
                    { date: "Feb 12, 2026", title: "Elevated latency on chat responses", status: "Resolved" },
                    { date: "Jan 28, 2026", title: "Scheduled maintenance — APAC region", status: "Completed" },
                    { date: "Jan 04, 2026", title: "Database failover test", status: "Completed" },
                  ].map((i) => (
                    <li key={i.title} className="px-5 py-3 flex items-center justify-between">
                      <div>
                        <p className="text-[13.5px] text-[#0F172A]">{i.title}</p>
                        <p className="text-[11.5px] text-[#94A3B8] mt-0.5">{i.date}</p>
                      </div>
                      <span className="text-[11px] font-semibold text-[#15803D] bg-[#DCFCE7] px-2 py-0.5 rounded-full">
                        {i.status}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* contact channels */}
              <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <SupportCard
                  icon={Mail}
                  title="Support Email"
                  desc="Reach us anytime — average response 4 business hours."
                  cta="support@oraone.in"
                  href="mailto:support@oraone.in"
                  testid="support-email"
                />
                <SupportCard
                  icon={LifeBuoy}
                  title="Live Chat"
                  desc="Talk to a human or an AI agent right inside the dashboard."
                  cta="Open live chat"
                  href="#"
                  testid="support-livechat"
                />
                <SupportCard
                  icon={Ticket}
                  title="Ticket Portal"
                  desc="Track every ticket, attach logs and get SLA-backed responses."
                  cta="Visit portal"
                  href="#"
                  testid="support-ticket"
                />
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */
/*  Small primitives                                                    */
/* ──────────────────────────────────────────────────────────────────── */
function SectionHeader({ eyebrow, title, subtitle }) {
  return (
    <div className="max-w-2xl">
      <span className="text-[11px] font-bold tracking-[0.25em] text-[#2563EB]">{eyebrow}</span>
      <h2 className="mt-2 text-2xl sm:text-3xl font-black tracking-tight text-[#0F172A] leading-tight">
        {title}
      </h2>
      <p className="mt-2 text-[14.5px] text-[#64748B] leading-relaxed">{subtitle}</p>
    </div>
  );
}

function SupportCard({ icon: Icon, title, desc, cta, href, testid }) {
  return (
    <a
      href={href}
      data-testid={testid}
      className="block p-5 rounded-2xl border border-[#E2E8F0] bg-white hover:border-[#2563EB]/30 hover:shadow-premium transition-all group"
    >
      <div className="size-10 rounded-xl bg-[#EFF6FF] grid place-items-center">
        <Icon size={18} className="text-[#2563EB]" />
      </div>
      <h4 className="mt-3.5 text-[14.5px] font-semibold text-[#0F172A]">{title}</h4>
      <p className="mt-1.5 text-[13px] text-[#64748B] leading-relaxed">{desc}</p>
      <span className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-semibold text-[#2563EB] group-hover:gap-2 transition-all">
        {cta} <ArrowRight size={13} />
      </span>
    </a>
  );
}
