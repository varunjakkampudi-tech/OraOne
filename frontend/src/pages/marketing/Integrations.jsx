import React, { useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { useSEO } from "@/lib/seo";
import SimpleIcon from "@/components/ui/SimpleIcon";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.5 },
};

// Category color tokens
const CAT_STYLES = {
  CRM: { bg: "#FEE2E2", color: "#DC2626" },
  Communication: { bg: "#DBEAFE", color: "#2563EB" },
  Documents: { bg: "#DCFCE7", color: "#16A34A" },
  Other: { bg: "#EDE9FE", color: "#7C3AED" },
};

const INTEGRATIONS = [
  { slug: "google-drive", name: "Google Drive", category: "Documents", desc: "Auto-sync Drive folders straight into your Knowledge Base.", logo: "google-drive" },
  { slug: "notion", name: "Notion", category: "Documents", desc: "Sync pages, databases and wikis into your Knowledge Base.", logo: "notion" },
  { slug: "slack", name: "Slack", category: "Communication", desc: "Search channels and get notified about new leads and conversations.", logo: "slack" },
  { slug: "gmail", name: "Gmail", category: "Communication", desc: "Read, search and summarize email, and draft AI replies.", logo: "gmail" },
  { slug: "hubspot", name: "HubSpot", category: "CRM", desc: "Sync contacts and deals with HubSpot CRM.", logo: "hubspot" },
  { slug: "salesforce", name: "Salesforce", category: "CRM", desc: "Sync leads, opportunities and accounts to Salesforce.", logo: "salesforce" },
];

const CATEGORIES = ["All", "CRM", "Communication", "Documents"];

export default function IntegrationsPage() {
  const [active, setActive] = useState("All");
  useSEO({
    title: "Integrations",
    description: "Connect OraOne with Google Drive, Notion, Slack, Gmail, HubSpot and Salesforce — sync your knowledge, capture leads and automate workflows.",
  });

  const list = active === "All" ? INTEGRATIONS : INTEGRATIONS.filter((i) => i.category === active);

  return (
    <div className="bg-white">
      {/* ====== HERO ====== */}
      <section className="relative pt-24 pb-14 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.span {...fadeUp} className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EFF6FF] text-xs font-bold tracking-[0.2em] text-[#2563EB]">
            <span className="size-1.5 rounded-full bg-[#2563EB]" />
            SEAMLESS INTEGRATIONS
          </motion.span>
          <motion.h1 {...fadeUp} className="mt-6 text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tighter text-[#0F172A]">
            Integrate with Your <span className="gradient-text">Favorite Tools</span>
          </motion.h1>
          <motion.p {...fadeUp} className="mt-5 text-[#64748B] max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
            Connect OraOne with the tools you use every day.<br className="hidden sm:block" /> Automate workflows and streamline your operations.
          </motion.p>

          {/* Filter pills */}
          <div className="mt-10 flex flex-wrap justify-center gap-2.5">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setActive(c)}
                data-testid={`integrations-filter-${c.toLowerCase()}`}
                className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  active === c
                    ? "bg-[#2563EB] text-white shadow-[0_8px_24px_-6px_rgba(37,99,235,0.45)]"
                    : "bg-white text-[#475569] border border-[#E2E8F0] hover:border-[#CBD5E1] hover:bg-[#F8FAFC]"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ====== INTEGRATION GRID ====== */}
      <section className="pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div layout className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {list.map((i, idx) => {
              const cat = CAT_STYLES[i.category] || CAT_STYLES.Other;
              return (
                <motion.div
                  key={i.slug}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: idx * 0.03, duration: 0.4 }}
                  className="group rounded-3xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/40 hover:shadow-premium-lg transition-all p-6 flex flex-col"
                  data-testid={`integration-card-${i.slug}`}
                >
                  <BrandLogo name={i.logo} />

                  <h3 className="mt-5 text-lg font-bold tracking-tight text-[#0F172A]">{i.name}</h3>
                  <span
                    className="mt-1.5 inline-flex items-center self-start px-2.5 py-0.5 rounded-md text-[11px] font-semibold"
                    style={{ background: cat.bg, color: cat.color }}
                  >
                    {i.category}
                  </span>

                  <p className="mt-3 text-sm text-[#64748B] leading-relaxed flex-1">{i.desc}</p>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </section>

      {/* ====== COMING SOON BANNER ====== */}
      <section className="pb-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="rounded-3xl bg-[#F8FAFC] border border-[#E2E8F0] p-8 sm:p-12">
            <div className="grid lg:grid-cols-2 gap-10 items-center">
              {/* Left illustration */}
              <ConnectionIllustration />

              {/* Right text */}
              <div>
                <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#EFF6FF] text-[10px] font-bold tracking-[0.2em] text-[#2563EB]">
                  <Sparkles size={10} /> MORE INTEGRATIONS COMING SOON
                </span>
                <h2 className="mt-5 text-3xl sm:text-4xl font-bold tracking-tight text-[#0F172A] leading-tight">
                  We're adding more integrations every month.
                </h2>
                <p className="mt-4 text-[#64748B] leading-relaxed">
                  Can't find the integration you need? Our team can help you build a custom integration.
                </p>
                <Link
                  to="/contact"
                  data-testid="integrations-request-cta"
                  className="mt-7 inline-flex items-center gap-2 px-5 py-3 rounded-xl border-2 border-[#2563EB] text-[#2563EB] hover:bg-[#2563EB] hover:text-white font-semibold text-sm transition-all"
                >
                  Request an Integration <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}

/* =========================================================================
   Brand logo tiles — use OFFICIAL pixel-perfect SVGs from Simple Icons CDN.
   `cdn.simpleicons.org/<slug>` returns the real brand mark in the brand's
   official color, so the icons match the actual products exactly.
   ========================================================================= */

// Map our internal logo key -> Simple Icons slug (and optional config)
const BRAND_ICONS = {
  "google-drive": { slug: "googledrive", useBrandColor: true },
  notion: { slug: "notion", useBrandColor: true },
  slack: { slug: "slack", useBrandColor: true },
  gmail: { slug: "gmail", useBrandColor: true },
  hubspot: { slug: "hubspot", useBrandColor: true },
  salesforce: { slug: "salesforce", useBrandColor: true },
};

function BrandLogo({ name }) {
  const cfg = BRAND_ICONS[name];
  if (!cfg) {
    return <div className="size-12 rounded-2xl bg-[#F1F5F9] border border-[#E2E8F0]" />;
  }

  // Special-case branded coloured tile (e.g. WhatsApp)
  if (cfg.tile) {
    return (
      <div
        className="size-12 rounded-2xl grid place-items-center shrink-0"
        style={{ background: cfg.tile }}
      >
        <SimpleIcon slug={cfg.slug} size={28} color={`#${cfg.color}`} title={name} />
      </div>
    );
  }

  return (
    <div className="size-12 rounded-2xl bg-white grid place-items-center shrink-0">
      <SimpleIcon slug={cfg.slug} size={40} color={cfg.color ? `#${cfg.color}` : undefined} useBrandColor={cfg.useBrandColor} title={name} />
    </div>
  );
}

/* =========================================================================
   Connection illustration for the "More integrations" banner.
   ========================================================================= */
function ConnectionIllustration() {
  return (
    <div className="relative h-64 lg:h-72">
      {/* Browser window mock */}
      <div className="absolute left-4 top-8 w-52 sm:w-60 rounded-2xl bg-white border border-[#E2E8F0] shadow-premium overflow-hidden">
        <div className="px-3 py-2 border-b border-[#E2E8F0] flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-red-400" />
          <span className="size-2 rounded-full bg-yellow-400" />
          <span className="size-2 rounded-full bg-green-400" />
          <div className="ml-2 flex-1 h-2 rounded-full bg-[#F1F5F9]" />
        </div>
        <div className="p-3 space-y-2">
          <div className="h-2 rounded-full bg-[#F1F5F9] w-3/4" />
          <div className="h-2 rounded-full bg-[#F1F5F9] w-1/2" />
          <div className="mt-3 grid grid-cols-3 gap-1.5">
            <div className="h-8 rounded-lg bg-blue-100" />
            <div className="h-8 rounded-lg bg-cyan-100" />
            <div className="h-8 rounded-lg bg-purple-100" />
          </div>
        </div>
      </div>

      {/* Connection lines (SVG) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 400 280" fill="none" preserveAspectRatio="none">
        <path d="M 200 60 Q 300 50 320 110" stroke="#3B82F6" strokeWidth="1.5" strokeDasharray="3 4" fill="none" />
        <path d="M 200 150 Q 280 180 310 200" stroke="#F59E0B" strokeWidth="1.5" strokeDasharray="3 4" fill="none" />
        <path d="M 100 200 Q 60 220 80 250" stroke="#3B82F6" strokeWidth="1.5" strokeDasharray="3 4" fill="none" />
      </svg>

      {/* Floating tool tiles */}
      <div className="absolute right-4 top-2 size-14 rounded-2xl bg-white border border-[#E2E8F0] shadow-premium grid place-items-center float-anim">
        <svg width="32" height="32" viewBox="0 0 48 48">
          <path d="M6 16 H42 V32 H6 Z" fill="#00A1E0" opacity="0.15" />
          <path
            d="M14 22 Q14 16 20 16 Q22 12 27 13 Q32 11 35 16 Q42 16 41 23 Q43 27 38 30 Q37 35 30 35 Q26 38 21 34 Q14 36 13 30 Q9 28 14 22 Z"
            fill="#00A1E0"
          />
        </svg>
      </div>

      <div className="absolute right-10 top-32 size-14 rounded-2xl bg-white border border-[#E2E8F0] shadow-premium grid place-items-center float-anim" style={{ animationDelay: "0.6s" }}>
        <svg width="28" height="28" viewBox="0 0 48 48">
          <circle cx="32" cy="22" r="10" fill="none" stroke="#FF7A59" strokeWidth="3" />
          <circle cx="32" cy="22" r="3" fill="#FF7A59" />
          <line x1="16" y1="36" x2="28" y2="24" stroke="#FF7A59" strokeWidth="3" strokeLinecap="round" />
          <circle cx="14" cy="38" r="4" fill="#FF7A59" />
        </svg>
      </div>

      <div className="absolute left-2 bottom-2 size-14 rounded-2xl bg-white border border-[#E2E8F0] shadow-premium grid place-items-center float-anim" style={{ animationDelay: "1.2s" }}>
        <svg width="26" height="26" viewBox="0 0 48 48">
          <rect x="6" y="8" width="36" height="36" rx="4" fill="white" />
          <rect x="6" y="8" width="36" height="8" rx="4" fill="#4285F4" />
          <text x="24" y="34" textAnchor="middle" fontSize="14" fontWeight="700" fill="#4285F4" fontFamily="Inter, sans-serif">31</text>
        </svg>
      </div>
    </div>
  );
}
