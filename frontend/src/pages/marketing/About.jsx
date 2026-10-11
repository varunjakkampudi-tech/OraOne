import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Heart, Code2, DollarSign, ShieldCheck, ArrowRight, Sparkles,
  Users, MessageSquare, Globe2, Target, Lightbulb, Rocket,
} from "lucide-react";
import { useSEO } from "@/lib/seo";
import { BrandMark } from "@/components/marketing/Logo";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.5 },
};

const STATS = [
  { value: "500+",    label: "Businesses in beta", icon: Users, color: "#2563EB", bg: "#EFF6FF" },
  { value: "10,000+", label: "Conversations automated", icon: MessageSquare, color: "#06B6D4", bg: "#ECFEFF" },
  { value: "50+",     label: "Languages supported", icon: Globe2, color: "#22C55E", bg: "#ECFDF5" },
  { value: "Free",    label: "During public beta", icon: Heart, color: "#EC4899", bg: "#FCE7F3" },
];

const VALUES = [
  { icon: Heart,       title: "Customer-obsessed", desc: "Every decision starts with what's best for our customers. We listen, we ship fast, and we measure success by yours.", color: "#EC4899", bg: "#FCE7F3" },
  { icon: Code2,       title: "Engineering-first", desc: "Quality is non-negotiable. We invest in the craft — clean APIs, reliable uptime and thoughtful product design.", color: "#2563EB", bg: "#EFF6FF" },
  { icon: DollarSign,  title: "Honest pricing",    desc: "No surprises. No hidden fees. No bait-and-switch. Simple, transparent pricing that scales fairly with usage.", color: "#22C55E", bg: "#ECFDF5" },
  { icon: ShieldCheck, title: "Privacy by design", desc: "Your data is yours. Encryption in transit and at rest, OWASP-aligned security, and zero data resale — ever.", color: "#8B5CF6", bg: "#F3E8FF" },
];

const TIMELINE = [
  { year: "2024", title: "OraOne is born", desc: "Founded with a single mission — give every business an AI workforce." },
  { year: "2025", title: "Beta launch", desc: "Chat agents launch to our first early-access teams." },
  { year: "2026", title: "Public Beta",  desc: "Free Beta opens to the world. AI agents become the new default." },
];

export default function AboutPage() {
  useSEO({
    title: "About Us",
    description: "OraOne is on a mission to give every business an AI workforce — replying on chat and never missing a lead.",
  });

  return (
    <div className="bg-white">
      {/* ====== HERO ====== */}
      <section className="relative pt-24 pb-20 overflow-hidden bg-gradient-to-b from-[#F8FAFC] via-white to-white">
        <Sparkle top="22%" left="11%" color="#8B5CF6" />
        <Sparkle top="44%" left="6%"  color="#06B6D4" />
        <Sparkle top="28%" right="10%" color="#2563EB" />
        <Sparkle top="58%" right="6%"  color="#22C55E" />

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.span {...fadeUp} className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EFF6FF] text-xs font-bold tracking-[0.2em] text-[#2563EB]">
            <Sparkles size={12} /> ABOUT ORAONE
          </motion.span>
          <motion.h1 {...fadeUp} className="mt-6 text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tighter text-[#0F172A] leading-[1.05]">
            Building the future<br />of <span className="gradient-text">conversations</span>
          </motion.h1>
          <motion.p {...fadeUp} className="mt-6 text-[#64748B] text-base sm:text-lg leading-relaxed max-w-2xl mx-auto">
            OraOne is on a mission to give every business an AI workforce — one that replies on chat and never misses a lead.
          </motion.p>
        </div>
      </section>

      {/* ====== STATS ====== */}
      <section className="pb-20 -mt-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="grid grid-cols-2 lg:grid-cols-4 gap-5">
            {STATS.map((s, i) => (
              <motion.div
                key={s.label}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="p-7 rounded-3xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/30 hover:shadow-premium transition-all text-center"
              >
                <div className="size-12 mx-auto rounded-2xl grid place-items-center mb-4" style={{ background: s.bg }}>
                  <s.icon size={20} style={{ color: s.color }} />
                </div>
                <p className="text-4xl sm:text-5xl font-black tracking-tighter text-[#2563EB]">{s.value}</p>
                <p className="mt-2 text-sm text-[#64748B]">{s.label}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ====== MISSION / STORY ====== */}
      <section className="pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="rounded-3xl bg-[#0F172A] text-white p-8 sm:p-14 relative overflow-hidden">
            <div className="absolute -top-20 -right-20 size-80 rounded-full" style={{ background: "radial-gradient(circle, rgba(37,99,235,0.35), transparent 60%)" }} />
            <div className="absolute -bottom-32 -left-20 size-96 rounded-full" style={{ background: "radial-gradient(circle, rgba(6,182,212,0.25), transparent 60%)" }} />

            <div className="relative grid lg:grid-cols-12 gap-10 items-center">
              <div className="lg:col-span-5 flex justify-center lg:justify-start">
                <div className="size-32 sm:size-40 rounded-full bg-white/5 grid place-items-center backdrop-blur border border-white/10">
                  <BrandMark size={88} />
                </div>
              </div>
              <div className="lg:col-span-7">
                <p className="text-xs font-bold tracking-[0.2em] text-[#7DD3FC]">OUR MISSION</p>
                <h2 className="mt-3 text-3xl sm:text-4xl font-bold tracking-tight leading-tight">
                  Every business deserves an AI workforce.
                </h2>
                <p className="mt-4 text-white/75 leading-relaxed">
                  We started OraOne because too many great businesses lose customers to a slow reply or an unanswered chat at 11pm. We're building the platform that ensures every conversation gets answered — instantly, intelligently, and in your customer's own language.
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Link to="/signup" className="px-5 py-3 rounded-xl bg-white text-[#0F172A] hover:bg-white/90 text-sm font-semibold inline-flex items-center gap-2">
                    Try OraOne <ArrowRight size={14} />
                  </Link>
                  <Link to="/contact" className="px-5 py-3 rounded-xl border border-white/25 hover:bg-white/10 text-sm font-semibold">
                    Get in touch
                  </Link>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ====== VALUES ====== */}
      <section className="pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto mb-12">
            <p className="text-xs font-bold tracking-[0.2em] text-[#2563EB]">WHAT WE STAND FOR</p>
            <h2 className="mt-3 text-4xl sm:text-5xl font-bold tracking-tighter text-[#0F172A]">Our values</h2>
            <p className="mt-4 text-[#64748B]">Customer-obsessed. Engineering-first. Honest pricing. Privacy by design.</p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {VALUES.map((v, i) => (
              <motion.div
                key={v.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className="p-7 rounded-3xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/30 hover:shadow-premium-lg transition-all"
                data-testid={`about-value-${v.title.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <div className="size-12 rounded-2xl grid place-items-center mb-5" style={{ background: v.bg }}>
                  <v.icon size={20} style={{ color: v.color }} />
                </div>
                <h3 className="text-lg font-bold tracking-tight text-[#0F172A]">{v.title}</h3>
                <p className="mt-2 text-sm text-[#64748B] leading-relaxed">{v.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ====== TIMELINE ====== */}
      <section className="pb-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center mb-10">
            <p className="text-xs font-bold tracking-[0.2em] text-[#2563EB]">OUR JOURNEY</p>
            <h2 className="mt-3 text-4xl font-bold tracking-tighter text-[#0F172A]">From idea to industry</h2>
          </motion.div>

          <ol className="relative">
            <span className="absolute left-[19px] top-3 bottom-3 w-px bg-[#E2E8F0]" />
            {TIMELINE.map((t, i) => (
              <motion.li
                key={t.year}
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="relative flex items-start gap-5 pb-8 last:pb-0"
              >
                <div className="relative z-10 size-10 rounded-full bg-white border-2 border-[#2563EB] grid place-items-center flex-shrink-0">
                  <span className="text-[10px] font-bold text-[#2563EB]">{t.year}</span>
                </div>
                <div className="pt-1 flex-1 p-5 rounded-2xl bg-white border border-[#E2E8F0]">
                  <h3 className="text-base font-semibold text-[#0F172A]">{t.title}</h3>
                  <p className="mt-1 text-sm text-[#64748B]">{t.desc}</p>
                </div>
              </motion.li>
            ))}
          </ol>
        </div>
      </section>

      {/* ====== CTA ====== */}
      <section className="pb-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="relative rounded-3xl overflow-hidden p-8 sm:p-10 text-white" style={{ background: "linear-gradient(135deg, #2563EB 0%, #1E40AF 100%)" }}>
            <div className="absolute -top-20 -left-20 size-72 rounded-full bg-white/10" />
            <div className="absolute -bottom-32 -right-20 size-96 rounded-full bg-white/5" />
            <div className="relative grid lg:grid-cols-12 items-center gap-6">
              <div className="lg:col-span-2 flex justify-center lg:justify-start">
                <div className="size-24 rounded-full bg-white/10 grid place-items-center backdrop-blur-sm">
                  <BrandMark size={56} />
                </div>
              </div>
              <div className="lg:col-span-6">
                <h3 className="text-2xl sm:text-3xl font-bold tracking-tight">Join the future of conversations</h3>
                <p className="mt-2 text-sm text-white/80">Start free during our beta. Deploy your first AI agent in minutes.</p>
              </div>
              <div className="lg:col-span-4 flex flex-wrap gap-3 lg:justify-end">
                <Link to="/signup" data-testid="about-cta-start" className="px-5 py-3 rounded-xl bg-white hover:bg-white/90 text-[#2563EB] font-semibold text-sm">Start Free Beta</Link>
                <Link to="/contact" data-testid="about-cta-contact" className="px-5 py-3 rounded-xl border border-white/30 hover:bg-white/10 font-semibold text-sm">Contact Sales</Link>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}

function Sparkle({ top, left, right, color }) {
  return (
    <svg className="absolute" style={{ top, left, right }} width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 0 L9.6 6.4 L16 8 L9.6 9.6 L8 16 L6.4 9.6 L0 8 L6.4 6.4 Z" fill={color} opacity="0.7" />
    </svg>
  );
}
