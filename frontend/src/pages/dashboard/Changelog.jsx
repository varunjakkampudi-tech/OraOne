import React from "react";
import { motion } from "framer-motion";
import {
  Sparkles,
  Rocket,
  Wand2,
  Bug,
  Zap,
  ArrowUpRight,
} from "lucide-react";
import { PageHeader, Card, Badge } from "@/components/dashboard/kit";

// ─────────────────────────────────────────────────────────────────────────────
// Changelog — the public-facing "what's new" log, in-product so customers always
// see how OraOne is improving. Entries are curated and shipped with the app.
// ─────────────────────────────────────────────────────────────────────────────

const TAGS = {
  new: { label: "New", tone: "indigo", icon: Sparkles },
  improved: { label: "Improved", tone: "blue", icon: Wand2 },
  fixed: { label: "Fixed", tone: "green", icon: Bug },
  performance: { label: "Performance", tone: "amber", icon: Zap },
};

const ENTRIES = [
  {
    version: "1.1.0",
    date: "June 25, 2026",
    title: "OraOne now supports you with OraOne",
    highlight: true,
    changes: [
      { tag: "new", text: "OraOne AI Support — an in-product assistant grounded in our docs, API, pricing, troubleshooting and release notes answers product questions anywhere in the dashboard." },
      { tag: "new", text: "Was this helpful? 👍 👎 feedback on every AI answer feeds quality scoring and knowledge-gap detection." },
      { tag: "new", text: "Product Status page with live health checks, and an in-product Changelog (this page)." },
    ],
  },
  {
    version: "1.0.0",
    date: "June 22, 2026",
    title: "OraOne 1.0 — production launch",
    changes: [
      { tag: "new", text: "Hybrid retrieval: dense vectors fused with BM25 keyword ranking plus a cross-encoder reranker for sharper, grounded answers. Configure the reranker engine in AI Models → Knowledge retrieval." },
      { tag: "new", text: "Visual workflow builder: arrange AI prompt, classify, extract, knowledge lookup, run-agent, condition, human-approval, webhook and notify nodes on a canvas; runs show a live status overlay." },
      { tag: "new", text: "Distributed website crawler with live telemetry, polite per-host rate limiting, JS rendering, and pause / resume / cancel." },
      { tag: "new", text: "AI model routing: choose balanced / cheapest / fastest / highest-quality, set a monthly budget and latency cap with automatic fallback." },
      { tag: "improved", text: "Conversation observability — per-message tokens, cost, latency, model and citations." },
      { tag: "improved", text: "Cost & insights analytics: spend by agent / model / project, top questions and knowledge gaps." },
    ],
  },
  {
    version: "0.9.0",
    date: "June 10, 2026",
    title: "Channels, widgets & multi-tenant foundations",
    changes: [
      { tag: "new", text: "Embeddable chat widget with theming, suggested questions, lead capture and escalation to a human." },
      { tag: "new", text: "Workspace → Project hierarchy with strict per-organization isolation and role-based access." },
      { tag: "performance", text: "Connection pooling and async I/O across the API for lower p95 latency under load." },
      { tag: "fixed", text: "Resolved duplicate document chunks when re-uploading a file with the same name." },
    ],
  },
];

function ChangeRow({ change }) {
  const meta = TAGS[change.tag] || TAGS.improved;
  const Icon = meta.icon;
  return (
    <li className="flex items-start gap-3">
      <span className="mt-0.5 shrink-0">
        <Badge tone={meta.tone} className="inline-flex items-center gap-1">
          <Icon size={11} />
          {meta.label}
        </Badge>
      </span>
      <p className="text-[13.5px] leading-relaxed text-[#334155]">{change.text}</p>
    </li>
  );
}

export default function Changelog() {
  return (
    <div className="space-y-6">
      <PageHeader
        icon={Rocket}
        eyebrow="Product"
        title="Changelog"
        subtitle="Everything new in OraOne — features, improvements and fixes."
        actions={
          <a
            href="/documentation"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-xl border border-[#E2E8F0] bg-white px-3.5 py-2 text-[13px] font-semibold text-[#334155] transition hover:border-[#BFD3F5] hover:bg-[#EFF6FF]"
          >
            Documentation
            <ArrowUpRight size={14} />
          </a>
        }
      />

      <div className="relative space-y-5">
        {ENTRIES.map((entry, i) => (
          <motion.div
            key={entry.version}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: i * 0.05 }}
          >
            <Card
              className={`p-6 ${entry.highlight ? "ring-1 ring-[#BFD3F5]" : ""}`}
              data-testid={`changelog-entry-${entry.version}`}
            >
              <div className="flex flex-wrap items-center gap-3">
                <span className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-br from-[#EFF6FF] to-[#ECFEFF] px-2.5 py-1 text-[12px] font-bold text-[#1D4ED8] ring-1 ring-[#DBEAFE]">
                  v{entry.version}
                </span>
                <span className="text-[12.5px] font-medium text-[#94A3B8]">{entry.date}</span>
                {entry.highlight && (
                  <Badge tone="indigo" className="inline-flex items-center gap-1">
                    <Sparkles size={11} />
                    Latest
                  </Badge>
                )}
              </div>
              <h3 className="mt-3 text-[16px] font-bold text-[#0F172A]">{entry.title}</h3>
              <ul className="mt-4 space-y-3">
                {entry.changes.map((c, j) => (
                  <ChangeRow key={j} change={c} />
                ))}
              </ul>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
