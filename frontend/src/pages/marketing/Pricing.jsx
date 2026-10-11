import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Sparkles, CheckCircle2, Check, Rocket, TrendingUp, Building2,
  Shield, FileText, ArrowUpCircle, Headphones, ArrowRight,
} from "lucide-react";
import { useSEO } from "@/lib/seo";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.5 },
};

const TIERS = [
  {
    slug: "starter",
    name: "Starter",
    tagline: "Perfect for trying out OraOne",
    icon: Rocket,
    iconBg: "#EFF6FF",
    iconColor: "#2563EB",
    priceColor: "text-[#2563EB]",
    postPrice: "$29",
    postPriceUnit: "/mo after launch",
    features: [
      "1 AI Agent",
      "500 conversations/mo",
      "Email support",
      "Basic analytics",
      "Standard knowledge base",
    ],
    cta: { label: "Start Free", to: "/signup", style: "bg-[#2563EB] hover:bg-[#1D4ED8] text-white" },
    dark: false,
  },
  {
    slug: "growth",
    name: "Growth",
    tagline: "For growing teams that need scale",
    icon: TrendingUp,
    iconBg: "#2563EB",
    iconColor: "#FFFFFF",
    priceColor: "text-white",
    postPrice: "Pricing",
    postPriceUnit: "announced at launch",
    features: [
      "5 AI Agents",
      "10,000 conversations/mo",
      "Priority support",
      "Advanced analytics",
      "CRM integrations (Salesforce, HubSpot, Zoho)",
      "Custom knowledge base",
    ],
    cta: { label: "Start Free", to: "/signup", style: "bg-white hover:bg-white/90 text-[#0F172A]" },
    dark: true,
    badge: "MOST POPULAR",
  },
  {
    slug: "enterprise",
    name: "Enterprise",
    tagline: "Custom solutions for large teams",
    icon: Building2,
    iconBg: "#F3E8FF",
    iconColor: "#7C3AED",
    priceColor: "text-[#7C3AED]",
    postPrice: "Custom",
    postPriceUnit: "Contact Sales",
    features: [
      "Unlimited AI Agents",
      "Unlimited conversations",
      "Custom integrations",
      "Dedicated support & CSM",
      "SLA options (uptime + response)",
      "SSO + RBAC + Audit logs",
    ],
    cta: { label: "Contact Sales", to: "/contact", style: "bg-[#7C3AED] hover:bg-[#6D28D9] text-white" },
    dark: false,
  },
];

const TRUST = [
  { icon: Shield,        title: "Enterprise-Grade Security", desc: "AES-256, TLS 1.3, RBAC and audit logs — built for serious businesses.", color: "#2563EB", bg: "#EFF6FF" },
  { icon: FileText,      title: "No Hidden Fees",             desc: "Transparent pricing — no setup fees, no surprise overages.",            color: "#22C55E", bg: "#ECFDF5" },
  { icon: ArrowUpCircle, title: "Scale Anytime",              desc: "Upgrade, downgrade or pause as your business changes.",                 color: "#F59E0B", bg: "#FEF3C7" },
  { icon: Headphones,    title: "Real Human Support",         desc: "Email + chat support on every plan. Dedicated CSM on Enterprise.",      color: "#8B5CF6", bg: "#F3E8FF" },
];

const FAQ_PRICING = [
  {
    q: "Is OraOne really free during Beta?",
    a: "Yes — Beta Access is completely free. No credit card required, no overage charges, no commitments. You can stay on Beta until we publicly launch, after which you'll be invited to migrate to the appropriate paid tier with founder pricing.",
  },
  {
    q: "What happens to my account after Beta?",
    a: "You'll get 30 days' notice before pricing kicks in. Beta users get early-adopter pricing — Starter from $29/month. You can keep, change or cancel your plan at that time.",
  },
  {
    q: "Do you offer custom plans for Enterprise?",
    a: "Absolutely. Enterprise plans include custom integrations, SSO, dedicated CSM, uptime + response SLA options, custom data residency and procurement-friendly contracts. Contact Sales to discuss.",
  },
  {
    q: "What's included with Enterprise SLA?",
    a: "Enterprise SLA options cover 99.9% uptime guarantee, priority response (under 1 hour for severity 1 issues), dedicated escalation channel, quarterly business reviews and custom data-retention controls.",
  },
];

export default function PricingPage() {
  useSEO({
    title: "Pricing — Free during Beta · From $29/mo",
    description:
      "OraOne is free during Beta Access. From $29/month after launch. Simple, transparent pricing with no hidden fees. Custom plans for Enterprise.",
  });

  return (
    <div className="bg-white">
      {/* ====== HERO ====== */}
      <section className="relative pt-24 pb-12 overflow-hidden bg-gradient-to-b from-[#F8FAFC] via-white to-white">
        <WaveDots side="left" />
        <WaveDots side="right" />
        <Sparkle top="22%" left="11%" color="#8B5CF6" />
        <Sparkle top="40%" left="6%" color="#06B6D4" />
        <Sparkle top="28%" right="10%" color="#2563EB" />
        <Sparkle top="55%" right="6%" color="#22C55E" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.span {...fadeUp} className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EFF6FF] text-xs font-bold tracking-[0.2em] text-[#2563EB]">
            <Sparkles size={12} /> BETA ACCESS · FREE DURING BETA
          </motion.span>
          <motion.h1 {...fadeUp} className="mt-6 text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tighter text-[#0F172A]">
            Simple, transparent <span className="gradient-text">pricing</span>
          </motion.h1>
          <motion.p {...fadeUp} className="mt-5 text-[#475569] max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
            OraOne is free for everyone during our Beta. After launch, pricing starts at{" "}
            <span className="font-semibold text-[#0F172A]">$29/month</span> — with custom Enterprise plans available.
          </motion.p>

          <motion.div {...fadeUp} className="mt-6 flex flex-wrap items-center justify-center gap-6 text-sm">
            {["Free during Beta", "No credit card required", "Cancel anytime"].map((t) => (
              <span key={t} className="inline-flex items-center gap-1.5 text-[#475569]">
                <CheckCircle2 size={16} className="text-[#22C55E]" /> {t}
              </span>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ====== PRICING BANNER ====== */}
      <section className="pb-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            {...fadeUp}
            className="rounded-2xl border border-[#2563EB]/20 bg-[#EFF6FF]/60 px-5 sm:px-7 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
          >
            <div className="flex items-start sm:items-center gap-3">
              <span className="px-2.5 py-1 rounded-md bg-[#2563EB] text-white text-[10px] font-bold tracking-[0.18em]">
                BETA
              </span>
              <p className="text-[13.5px] text-[#0F172A]">
                <span className="font-semibold">Free during Beta Access.</span>{" "}
                <span className="text-[#475569]">
                  Indicative post-beta pricing starts at $29/mo — Beta users get early-adopter pricing at launch.
                </span>
              </p>
            </div>
            <Link
              to="/contact"
              className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-[#2563EB] hover:underline whitespace-nowrap"
            >
              Talk to Sales <ArrowRight size={13} />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ====== PRICING CARDS ====== */}
      <section className="pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
            {TIERS.map((t, i) => (
              <motion.div
                key={t.slug}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08, duration: 0.55 }}
                className={`relative rounded-3xl p-8 flex flex-col ${
                  t.dark
                    ? "bg-[#0F172A] text-white border-2 border-[#2563EB] shadow-[0_20px_60px_-12px_rgba(37,99,235,0.45)] lg:-mt-4 lg:mb-[-1rem]"
                    : "bg-white border border-[#E2E8F0] shadow-premium"
                }`}
                data-testid={`pricing-card-${t.slug}`}
              >
                {t.badge && (
                  <span className="absolute top-7 right-7 px-3 py-1 rounded-md bg-[#2563EB] text-white text-[10px] font-bold tracking-wider">
                    {t.badge}
                  </span>
                )}

                {/* Header: icon + title */}
                <div className="flex items-start gap-4">
                  <div className="size-12 rounded-xl grid place-items-center flex-shrink-0" style={{ background: t.iconBg }}>
                    <t.icon size={20} style={{ color: t.iconColor }} />
                  </div>
                  <div className="pt-0.5">
                    <h3 className={`text-2xl font-bold tracking-tight ${t.dark ? "text-white" : "text-[#0F172A]"}`}>{t.name}</h3>
                    <p className={`mt-1 text-sm ${t.dark ? "text-white/65" : "text-[#64748B]"}`}>{t.tagline}</p>
                  </div>
                </div>

                {/* Price block — Beta hero + post-beta line */}
                <div className="mt-7">
                  <div className="flex items-baseline gap-2">
                    <span className={`text-6xl font-black tracking-tighter ${t.priceColor}`}>$0</span>
                    <span className={`text-sm ${t.dark ? "text-white/65" : "text-[#64748B]"}`}>during Beta</span>
                  </div>
                  <p className={`mt-2 text-[12.5px] ${t.dark ? "text-white/60" : "text-[#64748B]"}`}>
                    <span className={`font-semibold ${t.dark ? "text-white/85" : "text-[#0F172A]"}`}>{t.postPrice}</span>{" "}
                    {t.postPriceUnit}
                  </p>
                </div>

                {/* Divider */}
                <div className={`my-6 border-t ${t.dark ? "border-white/15" : "border-[#E2E8F0]"}`} />

                {/* Features */}
                <ul className="space-y-3 flex-1">
                  {t.features.map((f) => (
                    <li key={f} className={`flex items-center gap-3 text-sm ${t.dark ? "text-white/90" : "text-[#0F172A]"}`}>
                      <span className="size-5 rounded-full grid place-items-center flex-shrink-0" style={{ background: t.dark ? "rgba(37,99,235,0.9)" : "#2563EB" }}>
                        <Check size={12} className="text-white" />
                      </span>
                      {f}
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <Link
                  to={t.cta.to}
                  data-testid={`pricing-${t.slug}-cta`}
                  className={`mt-8 block text-center px-5 py-3.5 rounded-xl font-semibold text-sm transition-all hover:-translate-y-0.5 ${t.cta.style}`}
                >
                  {t.cta.label}
                </Link>
                <p className={`mt-3 text-center text-xs ${t.dark ? "text-white/55" : "text-[#94A3B8]"}`}>
                  Free during Beta — no credit card
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ====== TRUST STRIP ====== */}
      <section className="pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="rounded-3xl bg-[#F8FAFC] border border-[#E2E8F0] px-6 sm:px-8 py-7">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {TRUST.map((t) => (
                <div key={t.title} className="flex items-start gap-4">
                  <div className="size-12 rounded-full grid place-items-center flex-shrink-0" style={{ background: t.bg }}>
                    <t.icon size={20} style={{ color: t.color }} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-[#0F172A]">{t.title}</p>
                    <p className="mt-1 text-xs text-[#64748B] leading-relaxed">{t.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ====== PRICING FAQ ====== */}
      <section className="pb-24">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center mb-10">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tighter text-[#0F172A]">
              Pricing Questions, Answered
            </h2>
            <p className="mt-3 text-[#64748B]">Everything you need to know about Beta Access and post-launch pricing.</p>
          </motion.div>
          <div className="space-y-3">
            {FAQ_PRICING.map((f, i) => (
              <details
                key={i}
                className="group rounded-2xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/30 transition-colors"
              >
                <summary className="list-none p-5 flex items-center justify-between cursor-pointer gap-3">
                  <span className="text-[15px] font-semibold text-[#0F172A]">{f.q}</span>
                  <span className="text-[#64748B] group-open:rotate-180 transition-transform shrink-0">
                    <ArrowRight size={16} className="rotate-90" />
                  </span>
                </summary>
                <div className="px-5 pb-5 text-[#475569] text-[14px] leading-relaxed">{f.a}</div>
              </details>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function Sparkle({ top, left, right, color }) {
  return (
    <svg
      className="absolute"
      style={{ top, left, right }}
      width="14" height="14" viewBox="0 0 16 16" fill="none"
      aria-hidden="true"
    >
      <path d="M8 0 L9.6 6.4 L16 8 L9.6 9.6 L8 16 L6.4 9.6 L0 8 L6.4 6.4 Z" fill={color} opacity="0.7" />
    </svg>
  );
}

function WaveDots({ side }) {
  const dots = [];
  for (let i = 0; i < 12; i++) {
    for (let j = 0; j < 8; j++) {
      dots.push({ x: i * 14, y: j * 18, o: 0.05 + (j / 8) * 0.35 });
    }
  }
  return (
    <div
      className={`absolute top-12 ${side === "left" ? "left-0" : "right-0"} pointer-events-none hidden md:block`}
      style={{ width: 180, height: 200 }}
      aria-hidden="true"
    >
      <svg width="100%" height="100%" viewBox="0 0 180 200">
        {dots.map((d, i) => (
          <circle
            key={i}
            cx={side === "left" ? 180 - d.x : d.x}
            cy={d.y + Math.sin((d.x + d.y) * 0.15) * 6 + 20}
            r="1.6"
            fill="#94A3B8"
            opacity={d.o}
          />
        ))}
      </svg>
    </div>
  );
}
