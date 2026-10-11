// SEOLanding.jsx — Marketing-heavy SEO landing template.
// Used by /ai-chat-agent, /ai-lead-generation,
// /ai-appointment-booking, /ai-customer-support.
//
// Each landing page passes its config (hero copy, benefits, features,
// industries, FAQs, social proof) and this template renders a high-
// conversion long-form page with strong CTAs.

import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Star,
  Quote,
  ShieldCheck,
  Zap,
  Lock,
  TrendingUp,
  ChevronDown,
} from "lucide-react";
import { useSEO } from "@/lib/seo";
import { track, EVENTS } from "@/lib/analytics";

const fadeUp = {
  initial: { opacity: 0, y: 18 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.5 },
};

const TRUST_LOGOS = ["Acme Health", "Brightside Realty", "ServPro Auto", "Lumen Bank", "Bloom Hotels", "GreenLeaf Edu"];

export default function SEOLanding({ config }) {
  const {
    slug,
    title,
    description,
    eyebrow,
    h1,
    h1Accent,
    sub,
    primaryCTA = "Start Free",
    primaryCTAHref = "/signup",
    secondaryCTA = "Book Demo",
    secondaryCTAHref = "/contact",
    metrics = [],
    benefits = [],
    features = [],
    industries = [],
    socialProof = [],
    faqs = [],
  } = config;

  useSEO({
    title,
    description,
    breadcrumbs: [
      { name: "Home", url: "/" },
      { name: title, url: `/${slug}` },
    ],
    faq: faqs.map((f) => ({ question: f.q, answer: f.a })),
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "Product",
      name: title,
      description,
      brand: { "@type": "Brand", name: "OraOne" },
      offers: {
        "@type": "Offer",
        availability: "https://schema.org/InStock",
        price: "0",
        priceCurrency: "USD",
        url: `https://oraone.in/${slug}`,
      },
    },
  });

  return (
    <div className="bg-white" data-testid={`seo-landing-${slug}`}>
      {/* ═══════════ HERO ═══════════ */}
      <section className="relative pt-20 pb-16 sm:pt-24 sm:pb-20 overflow-hidden bg-gradient-to-b from-[#F8FAFC] via-white to-white">
        <div className="absolute inset-0 pointer-events-none opacity-50">
          <div className="absolute top-12 left-1/4 w-72 h-72 rounded-full bg-[#DBEAFE] blur-3xl" />
          <div className="absolute bottom-10 right-1/4 w-72 h-72 rounded-full bg-[#EDE9FE] blur-3xl" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.span {...fadeUp} className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EFF6FF] text-xs font-bold tracking-[0.2em] text-[#2563EB]">
            <Sparkles size={11} /> {eyebrow}
          </motion.span>
          <motion.h1 {...fadeUp} className="mt-6 text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter text-[#0F172A] leading-[1.05]">
            {h1} <span className="gradient-text">{h1Accent}</span>
          </motion.h1>
          <motion.p {...fadeUp} className="mt-5 text-[#475569] max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
            {sub}
          </motion.p>
          <motion.div {...fadeUp} className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              to={primaryCTAHref}
              onClick={() => track(EVENTS.START_FREE, { source: `landing:${slug}`, position: "hero" })}
              data-testid={`landing-${slug}-cta-primary`}
              className="inline-flex items-center gap-1.5 px-6 py-3.5 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[15px] font-semibold shadow-[0_12px_24px_-8px_rgba(37,99,235,0.55)] transition-all"
            >
              {primaryCTA} <ArrowRight size={15} />
            </Link>
            <Link
              to={secondaryCTAHref}
              onClick={() => track(EVENTS.BOOK_DEMO, { source: `landing:${slug}`, position: "hero" })}
              data-testid={`landing-${slug}-cta-secondary`}
              className="inline-flex items-center gap-1.5 px-6 py-3.5 rounded-xl border border-[#CBD5E1] bg-white hover:border-[#2563EB] hover:text-[#2563EB] text-[#0F172A] text-[15px] font-semibold transition-all"
            >
              {secondaryCTA}
            </Link>
          </motion.div>

          {/* Trust badges */}
          <motion.div {...fadeUp} className="mt-8 flex flex-wrap items-center justify-center gap-3 text-[11.5px] text-[#64748B]">
            <Badge icon={ShieldCheck} text="GDPR Compliant" />
            <Badge icon={Lock} text="AES-256 · TLS 1.3" />
            <Badge icon={TrendingUp} text="99.9% Uptime" />
            <Badge icon={Zap} text="Live in 24h" />
          </motion.div>
        </div>
      </section>

      {/* ═══════════ METRICS BAR ═══════════ */}
      {metrics.length > 0 && (
        <section className="border-y border-[#E2E8F0] bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
            {metrics.map((m) => (
              <div key={m.label}>
                <p className="text-3xl sm:text-4xl font-black text-[#0F172A] tracking-tight">{m.value}</p>
                <p className="mt-1 text-[12px] text-[#64748B]">{m.label}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ═══════════ BENEFITS ═══════════ */}
      <section className="py-20 bg-[#F8FAFC]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto">
            <p className="text-[11px] font-bold tracking-[0.25em] text-[#2563EB]">WHY ORAONE</p>
            <h2 className="mt-2 text-3xl sm:text-4xl font-black tracking-tight text-[#0F172A]">Built to deliver outcomes, not just demos.</h2>
          </motion.div>
          <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {benefits.map((b, i) => (
              <motion.div
                key={b.title}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="p-6 rounded-2xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/30 hover:shadow-premium transition-all"
              >
                <div className="size-11 rounded-xl bg-[#EFF6FF] grid place-items-center">
                  <b.icon size={20} className="text-[#2563EB]" />
                </div>
                <h3 className="mt-4 text-[16px] font-bold text-[#0F172A]">{b.title}</h3>
                <p className="mt-2 text-[13.5px] text-[#64748B] leading-relaxed">{b.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ FEATURES (alternating rows) ═══════════ */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 18 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              className={`grid lg:grid-cols-2 gap-10 items-center ${i % 2 ? "lg:[direction:rtl]" : ""}`}
            >
              <div className="lg:[direction:ltr]">
                <p className="text-[11px] font-bold tracking-[0.25em] text-[#2563EB]">FEATURE</p>
                <h3 className="mt-2 text-2xl sm:text-3xl font-black tracking-tight text-[#0F172A]">{f.title}</h3>
                <p className="mt-3 text-[#475569] leading-relaxed">{f.desc}</p>
                <ul className="mt-5 space-y-2.5">
                  {f.points.map((p) => (
                    <li key={p} className="flex items-start gap-2.5 text-[14px] text-[#0F172A]">
                      <CheckCircle2 size={16} className="text-[#16A34A] mt-0.5 flex-shrink-0" />
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="lg:[direction:ltr]">
                <div className="rounded-3xl border border-[#E2E8F0] bg-gradient-to-br from-[#F8FAFC] to-white p-6 sm:p-8 aspect-[4/3] flex flex-col justify-between">
                  <div className="size-14 rounded-2xl grid place-items-center" style={{ background: f.bg || "#EFF6FF" }}>
                    <f.icon size={26} className="text-[#2563EB]" style={f.color ? { color: f.color } : undefined} />
                  </div>
                  <div>
                    <p className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">{f.tag || "PREVIEW"}</p>
                    <p className="mt-1 text-lg font-bold text-[#0F172A]">{f.previewTitle || f.title}</p>
                    <p className="text-[13px] text-[#64748B]">{f.previewDesc || f.desc}</p>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ═══════════ INDUSTRY USE CASES ═══════════ */}
      {industries.length > 0 && (
        <section className="py-20 bg-[#F8FAFC]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto">
              <p className="text-[11px] font-bold tracking-[0.25em] text-[#2563EB]">INDUSTRY USE CASES</p>
              <h2 className="mt-2 text-3xl sm:text-4xl font-black tracking-tight text-[#0F172A]">Trusted across industries.</h2>
            </motion.div>
            <div className="mt-10 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {industries.map((u, i) => (
                <motion.div
                  key={u.title}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.04 }}
                  className="p-5 rounded-2xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/30 transition-all"
                >
                  <span className="text-[10.5px] font-bold tracking-wider text-[#94A3B8] uppercase">{u.industry}</span>
                  <h3 className="mt-1 text-[15px] font-bold text-[#0F172A]">{u.title}</h3>
                  <p className="mt-1.5 text-[13px] text-[#64748B] leading-relaxed">{u.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ═══════════ SOCIAL PROOF (Logos + Testimonials) ═══════════ */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center">
            <p className="text-[11px] font-bold tracking-[0.25em] text-[#94A3B8]">TRUSTED BY GROWING TEAMS</p>
          </motion.div>
          <div className="mt-6 flex flex-wrap justify-center items-center gap-x-10 gap-y-3 opacity-70">
            {TRUST_LOGOS.map((l) => (
              <span key={l} className="text-[#475569] font-bold tracking-tight text-base sm:text-lg">{l}</span>
            ))}
          </div>

          {socialProof.length > 0 && (
            <div className="mt-12 grid md:grid-cols-2 lg:grid-cols-3 gap-5">
              {socialProof.map((s) => (
                <motion.div
                  key={s.author}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  className="p-6 rounded-2xl bg-white border border-[#E2E8F0]"
                >
                  <Quote size={18} className="text-[#2563EB]" />
                  <p className="mt-3 text-[13.5px] text-[#0F172A] leading-relaxed">&ldquo;{s.quote}&rdquo;</p>
                  <div className="mt-4 flex items-center gap-3 pt-4 border-t border-[#E2E8F0]">
                    <span className="size-9 rounded-full bg-gradient-to-br from-[#2563EB] to-[#7C3AED] text-white grid place-items-center text-[12px] font-bold">
                      {s.author[0]}
                    </span>
                    <div>
                      <p className="text-[13px] font-semibold text-[#0F172A]">{s.author}</p>
                      <p className="text-[11.5px] text-[#64748B]">{s.role}</p>
                    </div>
                    <div className="ml-auto flex gap-0.5">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <Star key={i} size={11} className="text-[#F59E0B] fill-[#F59E0B]" />
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ═══════════ FAQS ═══════════ */}
      {faqs.length > 0 && (
        <section className="py-20 bg-[#F8FAFC]">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div {...fadeUp} className="text-center">
              <p className="text-[11px] font-bold tracking-[0.25em] text-[#2563EB]">FREQUENTLY ASKED</p>
              <h2 className="mt-2 text-3xl sm:text-4xl font-black tracking-tight text-[#0F172A]">Questions, answered.</h2>
            </motion.div>
            <div className="mt-10 space-y-3" data-testid={`landing-${slug}-faqs`}>
              {faqs.map((f, i) => (
                <FaqItem key={i} q={f.q} a={f.a} idx={i} slug={slug} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ═══════════ BOTTOM CTA ═══════════ */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            {...fadeUp}
            className="relative rounded-3xl bg-gradient-to-br from-[#1E40AF] via-[#2563EB] to-[#1D4ED8] text-white p-10 sm:p-14 text-center overflow-hidden"
          >
            <div className="absolute inset-0 opacity-15 pointer-events-none">
              <div className="absolute -top-12 -right-12 size-72 rounded-full bg-white blur-3xl" />
              <div className="absolute -bottom-16 -left-12 size-72 rounded-full bg-[#60A5FA] blur-3xl" />
            </div>
            <div className="relative">
              <h2 className="text-3xl sm:text-4xl font-black tracking-tight">Ready to never miss another customer?</h2>
              <p className="mt-3 text-white/85 max-w-xl mx-auto">
                Launch your AI agent in under 15 minutes. No credit card required.
              </p>
              <div className="mt-7 flex flex-wrap justify-center gap-3">
                <Link
                  to={primaryCTAHref}
                  onClick={() => track(EVENTS.START_FREE, { source: `landing:${slug}`, position: "footer-cta" })}
                  data-testid={`landing-${slug}-cta-footer-primary`}
                  className="inline-flex items-center gap-1.5 px-6 py-3.5 rounded-xl bg-white text-[#2563EB] text-[15px] font-bold hover:bg-[#EFF6FF] transition-colors"
                >
                  {primaryCTA} <ArrowRight size={15} />
                </Link>
                <Link
                  to={secondaryCTAHref}
                  onClick={() => track(EVENTS.BOOK_DEMO, { source: `landing:${slug}`, position: "footer-cta" })}
                  data-testid={`landing-${slug}-cta-footer-secondary`}
                  className="inline-flex items-center gap-1.5 px-6 py-3.5 rounded-xl bg-white/10 hover:bg-white/15 text-white text-[15px] font-semibold border border-white/20 transition-colors"
                >
                  {secondaryCTA}
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}

function Badge({ icon: Icon, text }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white border border-[#E2E8F0]">
      <Icon size={11} className="text-[#2563EB]" /> {text}
    </span>
  );
}

function FaqItem({ q, a, idx, slug }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        data-testid={`landing-${slug}-faq-${idx}`}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-[#F8FAFC]"
      >
        <span className="text-[14px] font-semibold text-[#0F172A] pr-4">{q}</span>
        <ChevronDown
          size={16}
          className={`flex-shrink-0 text-[#94A3B8] transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="px-5 pb-4 text-[13.5px] text-[#475569] leading-relaxed border-t border-[#E2E8F0] pt-4">
          {a}
        </div>
      )}
    </div>
  );
}
