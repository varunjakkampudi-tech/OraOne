import React, { lazy, Suspense } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Mail,
  MessageSquare,
  Clock,
  Sparkles,
  ShieldCheck,
  Stethoscope,
  Home as HomeIcon,
  GraduationCap,
  Car,
  Wallet,
  ShoppingBag,
  CheckCircle2,
  ChevronDown,
  Lock,
  Layers,
  BookOpen,
  UserPlus,
  BarChart3,
  Users,
  Bot,
  Plug,
  Rocket,
  TrendingUp,
  Headphones,
  Activity,
  Star,
  Quote,
  Building2,
  ArrowUpRight,
  Zap,
  Network,
  Workflow,
} from "lucide-react";
import HeroOrb from "@/components/marketing/HeroOrb";
import ConversionFlow from "@/components/marketing/ConversionFlow";
import SimpleIcon from "@/components/ui/SimpleIcon";
import { useSEO } from "@/lib/seo";
import { HOME } from "@/constants/testIds";

const ChatAgentDemo = lazy(() =>
  import("@/components/marketing/ProductLiveDemos").then((m) => ({ default: m.ChatAgentDemo }))
);

const FAQ = [
  { q: "What is OraOne?", a: "OraOne is an AI Agent Platform that automates customer conversations on your website — so your business never misses a lead." },
  { q: "Can I integrate OraOne with my existing CRM?", a: "Yes — OraOne ships with native integrations for Salesforce, HubSpot, Zoho, Pipedrive, plus webhooks and REST APIs for anything custom." },
  { q: "What languages does OraOne support?", a: "OraOne supports 50+ languages. Your agents communicate naturally with customers worldwide." },
  { q: "How much does OraOne cost?", a: "OraOne offers flexible pricing based on conversation volume. Start free during our beta, then scale as you grow." },
  { q: "Is there setup required?", a: "Minimal. Deploy an AI agent in minutes with our template library, or customize from scratch. Technical and non-technical users both supported." },
];

const fadeUp = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.55, ease: [0.25, 0.1, 0.25, 1] },
};

/* ─────────────────────────────────  Data  ───────────────────────────────── */

const PLATFORM_METRICS = [
  {
    value: "10,000+",
    label: "Conversations Automated",
    sub: "Across every website conversation",
    note: "Platform metric",
  },
  {
    value: "500+",
    label: "Businesses Exploring OraOne",
    sub: "Currently in private & open beta",
    note: "Beta metric",
  },
  {
    value: "24/7",
    label: "Instant Responses",
    sub: "Answers in seconds, day or night",
    note: "Always on",
  },
];

const TRUST_PILLARS = [
  {
    icon: Clock,
    title: "24/7 AI Availability",
    desc: "Agents never sleep — answer customers instantly, day or night.",
    color: "#2563EB",
    bg: "#EFF6FF",
  },
  {
    icon: Activity,
    title: "99.9% Uptime",
    desc: "Built on AWS with redundancy and continuous health monitoring.",
    color: "#16A34A",
    bg: "#ECFDF5",
  },
  {
    icon: Network,
    title: "50+ Languages",
    desc: "Answers each customer naturally in their own language, automatically.",
    color: "#7C3AED",
    bg: "#F5F3FF",
  },
  {
    icon: ShieldCheck,
    title: "Enterprise-Grade Security",
    desc: "AES-256, TLS 1.3, RBAC, audit logs — built for serious businesses.",
    color: "#0EA5E9",
    bg: "#ECFEFF",
  },
];

const BENEFITS = [
  {
    icon: Layers,
    title: "Remembers every returning visitor",
    desc: "One AI brain remembers each visitor's history, so nobody has to explain their issue twice.",
    tone: "#2563EB",
    bg: "#EFF6FF",
  },
  {
    icon: MessageSquare,
    title: "Capture leads while you're offline",
    desc: "Your website chat agent answers, qualifies and books meetings 24/7 — even outside business hours.",
    tone: "#7C3AED",
    bg: "#F5F3FF",
  },
  {
    icon: BookOpen,
    title: "Answers your team would give",
    desc: "Upload PDFs, FAQs and docs once — every agent answers in your voice, from the same source of truth.",
    tone: "#0EA5E9",
    bg: "#ECFEFF",
  },
  {
    icon: UserPlus,
    title: "Hand sales-ready leads to your team",
    desc: "Qualified leads are auto-scored and pushed into your CRM the moment a conversation ends — no manual entry.",
    tone: "#16A34A",
    bg: "#ECFDF5",
  },
  {
    icon: BarChart3,
    title: "See exactly what's converting",
    desc: "Live dashboards on conversations, conversions and channel ROI — no SQL, no waiting on a report.",
    tone: "#F59E0B",
    bg: "#FEF3C7",
  },
  {
    icon: Users,
    title: "Scale support without adding headcount",
    desc: "Owners, admins, managers and viewers collaborate with granular roles and audit logs built-in.",
    tone: "#DB2777",
    bg: "#FCE7F3",
  },
];

const INDUSTRY_USE_CASES = [
  { icon: Stethoscope, name: "Healthcare", desc: "Appointments, reminders & patient triage." },
  { icon: HomeIcon, name: "Real Estate", desc: "Lead qualification & site-visit scheduling." },
  { icon: GraduationCap, name: "Education", desc: "Admissions & student/parent support." },
  { icon: ShieldCheck, name: "Insurance", desc: "Policy support, claims & renewals." },
  { icon: Car, name: "Automotive", desc: "Service booking & test-drive scheduling." },
  { icon: Wallet, name: "Finance & Lending", desc: "KYC, onboarding & customer support." },
  { icon: ShoppingBag, name: "Retail & D2C", desc: "Order updates, returns & loyalty." },
  { icon: Headphones, name: "Customer Support", desc: "Tier-1 deflection & escalation routing." },
];

const CASE_STUDY_HIGHLIGHTS = [
  {
    industry: "Healthcare",
    metric: "3.2×",
    result: "more appointments booked after deploying the Chat Agent on the website.",
    icon: Stethoscope,
    color: "#2563EB",
    bg: "#EFF6FF",
  },
  {
    industry: "Real Estate",
    metric: "62%",
    result: "of incoming website leads qualified before a human agent stepped in.",
    icon: HomeIcon,
    color: "#7C3AED",
    bg: "#F5F3FF",
  },
  {
    industry: "Finance",
    metric: "<30s",
    result: "average first-response time across web chat — down from 6+ minutes.",
    icon: Wallet,
    color: "#16A34A",
    bg: "#ECFDF5",
  },
];

const PRICING_PEEK = [
  {
    name: "Starter",
    line: "1 AI Agent · 500 conversations/mo",
    post: "From $29/mo after launch",
    icon: Rocket,
    color: "#2563EB",
    bg: "#EFF6FF",
  },
  {
    name: "Growth",
    line: "5 AI Agents · 10,000 conversations/mo",
    post: "Indicative post-beta pricing announced at launch",
    icon: TrendingUp,
    color: "#7C3AED",
    bg: "#F5F3FF",
    featured: true,
  },
  {
    name: "Enterprise",
    line: "Unlimited agents · SSO · SLA · Dedicated CSM",
    post: "Custom · Contact Sales",
    icon: Building2,
    color: "#0F172A",
    bg: "#F1F5F9",
  },
];

/* ───────────────────────────  Live Demo  ─────────────────────────── */

function LiveDemoSection() {
  return (
    <section
      id="live-demo"
      data-testid={HOME.demoSection}
      className="bg-white border-t border-[#E2E8F0]"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 sm:pt-10">
        <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto">
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#EFF6FF] text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">
            <Sparkles size={11} /> TRY ORAONE LIVE
          </span>
          <h2 className="mt-4 text-4xl sm:text-5xl font-bold tracking-tighter text-[#0F172A]">
            See the AI in action.
          </h2>
          <p className="mt-4 text-[#64748B] leading-relaxed">
            Watch a real conversation play out — transcript, lead capture and
            dashboard updates, in real time.
          </p>
        </motion.div>
      </div>

      {/* Demo body */}
      <Suspense
        fallback={<div className="py-24 text-center text-[#64748B] text-sm">Loading live demo...</div>}
      >
        <div className="mt-8">
          <ChatAgentDemo />
        </div>
      </Suspense>
    </section>
  );
}

/* ─────────────────────────────────  Page  ───────────────────────────────── */

export default function HomePage() {
  const nav = useNavigate();
  useSEO({
    title: "AI Chat Agents for Lead Conversion | OraOne",
    description:
      "AI Chat Agents that answer, qualify and convert customers 24/7 — so your business grows even when your team is offline.",
  });

  return (
    <div className="bg-white">
      {/* ====================== HERO ====================== */}
      <section className="relative pt-6 pb-8 sm:pt-8 sm:pb-10 overflow-hidden bg-[#F8FAFC]">
        <div className="absolute inset-0 grid-bg opacity-60 [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)]" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="grid lg:grid-cols-2 gap-10 lg:gap-12 items-center">
            {/* LEFT — copy + agent cards + CTAs */}
            <motion.div {...fadeUp}>
              <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#EFF6FF] text-[11px] font-semibold tracking-[0.2em] text-[#2563EB]">
                <Sparkles size={11} className="text-[#2563EB]" />
                AI CHAT AGENTS FOR BUSINESSES
              </span>
              <h1 className="mt-6 text-[2.75rem] sm:text-5xl lg:text-[3.75rem] font-black tracking-tighter leading-[1.05] text-[#0F172A]">
                Never Miss A Lead.
                <br />
                <span className="text-[#2563EB]">Never Miss A Sale.</span>
              </h1>
              <p className="mt-5 text-base sm:text-lg text-[#475569] leading-relaxed max-w-xl">
                AI Chat Agents that answer, qualify and convert
                customers 24/7 — so your business grows even when your team is offline.
              </p>

              {/* Agent cards */}
              <div className="mt-7 grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  {
                    icon: MessageSquare,
                    label: "Chat Agent",
                    sub: "Live website chat in real time.",
                    iconBg: "#DBEAFE",
                    iconColor: "#2563EB",
                  },
                  {
                    icon: Layers,
                    label: "Website Widget",
                    sub: "A chat bubble on any site, one line.",
                    iconBg: "#EDE9FE",
                    iconColor: "#7C3AED",
                  },
                ].map((p) => (
                  <div
                    key={p.label}
                    className="p-4 rounded-2xl bg-white border border-[#E2E8F0] shadow-premium"
                  >
                    <div
                      className="size-10 rounded-xl grid place-items-center mb-3"
                      style={{ background: p.iconBg }}
                    >
                      {p.brandSlug ? (
                        <SimpleIcon slug={p.brandSlug} size={18} useBrandColor title={p.label} />
                      ) : (
                        <p.icon size={18} style={{ color: p.iconColor }} />
                      )}
                    </div>
                    <p className="text-[13px] font-semibold text-[#0F172A]">{p.label}</p>
                    <p className="text-[11px] text-[#64748B] mt-1 leading-snug">{p.sub}</p>
                  </div>
                ))}
              </div>

              {/* CTAs */}
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <button
                  data-testid={HOME.heroCtaPrimary}
                  onClick={() => nav("/signup")}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_8px_24px_-6px_rgba(37,99,235,0.5)] hover:shadow-[0_12px_32px_-6px_rgba(37,99,235,0.6)] hover:-translate-y-0.5 transition-all"
                >
                  Start Free
                </button>
                <button
                  data-testid={HOME.heroCtaSecondary}
                  onClick={() => nav("/contact")}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-white border-2 border-[#2563EB] text-[#2563EB] hover:bg-[#EFF6FF] text-sm font-semibold transition-colors"
                >
                  Book Demo
                </button>
                <span className="text-xs text-[#64748B] inline-flex items-center gap-1">
                  <CheckCircle2 size={14} className="text-[#10B981]" /> Free during Beta · No credit card
                </span>
              </div>
            </motion.div>

            {/* RIGHT — orbit illustration with brand mark */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.7, delay: 0.1 }}
              className="hidden lg:flex justify-center"
            >
              <HeroOrb />
            </motion.div>
          </div>
        </div>
      </section>

      {/* ====================== TRUST & SOCIAL PROOF ====================== */}
      <section
        data-testid={HOME.trustSection}
        className="py-10 sm:py-12 bg-white border-t border-[#E2E8F0]"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] font-bold tracking-[0.2em] text-[#475569] border border-[#E2E8F0]">
              <Zap size={11} /> WHY TEAMS TRUST ORAONE
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              Built for businesses that can&apos;t afford to miss a customer.
            </h2>
            <p className="mt-4 text-[#64748B] leading-relaxed">
              OraOne is designed for reliability, scale and enterprise-grade trust —
              from day one of your beta.
            </p>
          </motion.div>

          {/* Platform metrics */}
          <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-4">
            {PLATFORM_METRICS.map((m, i) => (
              <motion.div
                key={m.label}
                data-testid={HOME.trustMetric}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.1 }}
                transition={{ delay: i * 0.06 }}
                className="rounded-2xl bg-white border border-[#E2E8F0] p-6 sm:p-7 hover:border-[#2563EB]/30 hover:shadow-premium transition-all"
              >
                <p className="text-[10px] font-bold tracking-[0.18em] text-[#64748B] uppercase">
                  {m.note}
                </p>
                <p className="mt-3 text-4xl sm:text-5xl font-black tracking-tighter text-[#0F172A]">
                  {m.value}
                </p>
                <p className="mt-2 text-[15px] font-semibold text-[#0F172A]">{m.label}</p>
                <p className="mt-1 text-[12.5px] text-[#64748B] leading-snug">{m.sub}</p>
              </motion.div>
            ))}
          </div>

          {/* Trust pillars */}
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {TRUST_PILLARS.map((p, i) => (
              <motion.div
                key={p.title}
                data-testid={HOME.trustPillar}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.1 }}
                transition={{ delay: i * 0.05 }}
                className="rounded-2xl bg-[#F8FAFC] border border-[#E2E8F0] p-5"
              >
                <div
                  className="size-11 rounded-xl grid place-items-center"
                  style={{ background: p.bg }}
                >
                  <p.icon size={20} style={{ color: p.color }} />
                </div>
                <p className="mt-4 text-[15px] font-semibold text-[#0F172A]">{p.title}</p>
                <p className="mt-1.5 text-[12.5px] text-[#64748B] leading-snug">{p.desc}</p>
              </motion.div>
            ))}
          </div>

          {/* Security CTA strip */}
          <div className="mt-8 rounded-2xl border border-[#E2E8F0] bg-[#0F172A] text-white px-6 py-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-xl bg-white/10 grid place-items-center">
                <ShieldCheck size={18} className="text-[#60A5FA]" />
              </div>
              <div>
                <p className="text-[14px] font-semibold">
                  GDPR · India DPDP · AES-256 · TLS 1.3 · RBAC
                </p>
                <p className="text-[12px] text-white/65 mt-0.5">
                  Read how we secure your data and your customers&apos; data.
                </p>
              </div>
            </div>
            <Link
              to="/security"
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-white text-[#0F172A] text-[13px] font-semibold hover:bg-white/90 transition-colors"
            >
              Security &amp; Trust <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      {/* ====================== HOW IT WORKS (conversion flow) ====================== */}
      <section className="py-10 sm:py-12 bg-[#F8FAFC] border-t border-[#E2E8F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto mb-8">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] font-bold tracking-[0.18em] text-[#475569] border border-[#E2E8F0] uppercase">
              <Workflow size={11} /> How It Works
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              One conversation. One qualified lead.
            </h2>
            <p className="mt-4 text-[#64748B] leading-relaxed">
              No manual triage. Every conversation is answered, qualified and routed straight
              into your pipeline — automatically.
            </p>
          </motion.div>
          <ConversionFlow />
        </div>
      </section>

      {/* ====================== LIVE PRODUCT DEMO (tabs) ====================== */}
      <LiveDemoSection />

      {/* ====================== CORE FEATURES (Why OraOne) ====================== */}
      <section className="py-10 sm:py-12 bg-[#F8FAFC] border-t border-[#E2E8F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#EFF6FF] text-[11px] font-bold text-[#2563EB] tracking-[0.18em] uppercase">
              <Sparkles size={11} /> Why OraOne
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              One platform. Every channel. Every conversation.
            </h2>
            <p className="mt-4 text-[#64748B] leading-relaxed">
              Everything you need to launch enterprise-grade AI agents — in one platform.
            </p>
          </motion.div>
          <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {BENEFITS.map((b, i) => (
              <motion.div
                key={b.title}
                initial={{ opacity: 0, y: 22 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.05 }}
                transition={{ duration: 0.45, delay: i * 0.05 }}
                className="group p-6 rounded-2xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/30 hover:shadow-premium-lg hover:-translate-y-0.5 transition-all duration-300"
                data-testid={`why-card-${i}`}
              >
                <div
                  className="size-12 rounded-xl grid place-items-center mb-4 transition-transform group-hover:scale-110"
                  style={{ background: b.bg }}
                >
                  <b.icon size={22} style={{ color: b.tone }} />
                </div>
                <h3 className="text-base font-semibold text-[#0F172A]">{b.title}</h3>
                <p className="mt-2 text-[13.5px] leading-relaxed text-[#64748B]">{b.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ====================== INDUSTRY USE CASES ====================== */}
      <section className="py-10 sm:py-12 bg-white border-t border-[#E2E8F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto mb-10">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              Built for every industry.
            </h2>
            <p className="mt-4 text-[#64748B] leading-relaxed">
              Pre-configured agents that understand your industry&apos;s vocabulary,
              workflows and compliance needs.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {INDUSTRY_USE_CASES.map((ind) => (
              <Link
                key={ind.name}
                to="/solutions"
                className="group flex items-start gap-3 p-5 rounded-2xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/30 hover:shadow-premium transition-all"
              >
                <div className="size-11 rounded-xl bg-[#EFF6FF] grid place-items-center shrink-0">
                  <ind.icon size={20} className="text-[#2563EB]" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-[#0F172A]">{ind.name}</p>
                  <p className="text-[12.5px] text-[#64748B] mt-1 leading-snug">{ind.desc}</p>
                </div>
              </Link>
            ))}
          </div>

          <div className="mt-8 text-center">
            <Link
              to="/solutions"
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-[#2563EB] hover:underline"
            >
              View all solutions <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      {/* ====================== CASE STUDIES / RESULTS ====================== */}
      <section
        data-testid={HOME.caseStudiesSnippet}
        className="py-10 sm:py-12 bg-[#F8FAFC] border-t border-[#E2E8F0]"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto mb-10">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] font-bold tracking-[0.18em] text-[#475569] border border-[#E2E8F0] uppercase">
              <Star size={11} /> Real Results
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              Outcomes from real teams.
            </h2>
            <p className="mt-4 text-[#64748B] leading-relaxed">
              Anonymised highlights from teams using OraOne in production.
              Industry-level metrics shared with permission.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {CASE_STUDY_HIGHLIGHTS.map((c, i) => (
              <motion.div
                key={c.industry}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.05 }}
                transition={{ delay: i * 0.06 }}
                className="rounded-2xl bg-white border border-[#E2E8F0] p-6 hover:border-[#2563EB]/30 hover:shadow-premium transition-all"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="size-10 rounded-xl grid place-items-center shrink-0"
                    style={{ background: c.bg }}
                  >
                    <c.icon size={18} style={{ color: c.color }} />
                  </div>
                  <p className="text-[12px] font-bold tracking-[0.16em] text-[#64748B] uppercase">
                    {c.industry}
                  </p>
                </div>
                <p className="mt-5 text-5xl font-black tracking-tighter text-[#0F172A]">
                  {c.metric}
                </p>
                <p className="mt-3 text-[14px] text-[#475569] leading-relaxed">
                  {c.result}
                </p>
              </motion.div>
            ))}
          </div>

          <div className="mt-10 text-center">
            <Link
              to="/case-studies"
              data-testid={HOME.caseStudiesSnippetCta}
              className="inline-flex items-center gap-1.5 px-5 py-3 rounded-xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/40 text-sm font-semibold text-[#0F172A] transition-colors"
            >
              Explore all case studies <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      {/* ====================== PRICING SNIPPET ====================== */}
      <section
        data-testid={HOME.pricingSnippet}
        className="py-10 sm:py-12 bg-white border-t border-[#E2E8F0]"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto mb-10">
            <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#EFF6FF] text-[11px] font-bold tracking-[0.18em] text-[#2563EB] uppercase">
              <Sparkles size={11} /> Free During Beta
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              Simple, transparent pricing.
            </h2>
            <p className="mt-4 text-[#64748B] leading-relaxed">
              Use OraOne free during Beta Access. From <span className="font-semibold text-[#0F172A]">$29/month after launch</span> — no hidden fees, cancel anytime.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {PRICING_PEEK.map((p, i) => (
              <motion.div
                key={p.name}
                initial={{ opacity: 0, y: 22 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.05 }}
                transition={{ delay: i * 0.06 }}
                className={`rounded-2xl border p-6 sm:p-7 flex flex-col ${
                  p.featured
                    ? "border-[#2563EB] bg-[#F8FAFC] shadow-premium-lg"
                    : "border-[#E2E8F0] bg-white"
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="size-11 rounded-xl grid place-items-center shrink-0"
                    style={{ background: p.bg }}
                  >
                    <p.icon size={18} style={{ color: p.color }} />
                  </div>
                  <div>
                    <p className="text-[16px] font-semibold text-[#0F172A]">{p.name}</p>
                    {p.featured && (
                      <p className="text-[10px] font-bold tracking-[0.18em] text-[#2563EB] uppercase mt-0.5">
                        Most Popular
                      </p>
                    )}
                  </div>
                </div>
                <p className="mt-4 text-[13px] text-[#475569] leading-relaxed">{p.line}</p>
                <div className="mt-5 pt-5 border-t border-[#E2E8F0]">
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-black tracking-tighter text-[#0F172A]">$0</span>
                    <span className="text-[12px] text-[#64748B]">/ during Beta</span>
                  </div>
                  <p className="mt-1 text-[11.5px] text-[#64748B]">{p.post}</p>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/pricing"
              data-testid={HOME.pricingSnippetCta}
              className="inline-flex items-center gap-1.5 px-5 py-3 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_8px_24px_-6px_rgba(37,99,235,0.5)] transition-all"
            >
              See full pricing <ArrowRight size={14} />
            </Link>
            <Link
              to="/contact"
              className="inline-flex items-center gap-1.5 px-5 py-3 rounded-xl bg-white border border-[#E2E8F0] hover:bg-[#F1F5F9] text-sm font-semibold text-[#0F172A] transition-colors"
            >
              Contact Sales
            </Link>
          </div>
        </div>
      </section>

      {/* ====================== FAQ ====================== */}
      <section className="py-10 sm:py-12 bg-[#F8FAFC] border-t border-[#E2E8F0]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              Frequently Asked Questions
            </h2>
          </motion.div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {FAQ.map((f, i) => (
              <details
                key={i}
                className="group rounded-2xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/30 transition-colors"
              >
                <summary className="list-none p-5 flex items-center justify-between cursor-pointer gap-3">
                  <span className="text-[15px] font-semibold text-[#0F172A]">{f.q}</span>
                  <ChevronDown size={18} className="text-[#64748B] group-open:rotate-180 transition-transform shrink-0" />
                </summary>
                <div className="px-5 pb-5 text-[#64748B] text-[14px] leading-relaxed">{f.a}</div>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ====================== FINAL CTA ====================== */}
      <section className="pb-10 sm:pb-12 bg-white border-t border-[#E2E8F0] pt-10 sm:pt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            {...fadeUp}
            className="relative rounded-3xl p-10 sm:p-14 overflow-hidden text-white shadow-premium-lg"
            style={{ background: "linear-gradient(135deg, #0F172A 0%, #1E40AF 100%)" }}
          >
            <div className="absolute -top-20 -right-20 size-80 rounded-full bg-white/10" />
            <div className="absolute -bottom-32 -left-32 size-96 rounded-full bg-white/5" />
            <div className="relative grid lg:grid-cols-2 gap-10 items-center">
              <div>
                <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter leading-tight">
                  Stop missing customers.
                  <br />
                  Start growing 24/7.
                </h2>
                <p className="mt-4 text-white/85 max-w-md leading-relaxed">
                  Deploy your AI chat agents in days, not months —
                  free during Beta Access.
                </p>
                <ul className="mt-6 flex flex-wrap gap-x-6 gap-y-2">
                  {["Free Beta Access", "No credit card required", "Cancel anytime"].map((b) => (
                    <li key={b} className="flex items-center gap-2 text-white/90 text-sm">
                      <CheckCircle2 size={16} /> {b}
                    </li>
                  ))}
                </ul>
                <div className="mt-8 flex flex-wrap gap-3">
                  <button
                    onClick={() => nav("/signup")}
                    className="px-5 py-3 rounded-xl bg-white text-[#0F172A] font-semibold text-sm hover:bg-white/90 transition-colors"
                    data-testid="cta-start-free"
                  >
                    Start Free
                  </button>
                  <button
                    onClick={() => nav("/contact")}
                    className="px-5 py-3 rounded-xl border border-white/30 hover:bg-white/10 font-semibold text-sm transition-colors"
                    data-testid="cta-book-demo"
                  >
                    Book Demo
                  </button>
                </div>
              </div>
              <div className="hidden lg:flex justify-center">
                <HeroOrb />
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}