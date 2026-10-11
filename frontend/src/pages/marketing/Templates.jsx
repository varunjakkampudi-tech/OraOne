import React, { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Stethoscope, Home, Car, ShieldCheck, Utensils, Users,
  MessageSquare, Rocket, ArrowRight, X,
  CheckCircle2, Sparkles, Copy, Check, Eye, ArrowDown,
} from "lucide-react";
import { useSEO } from "@/lib/seo";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.5 },
};

const CHANNEL = {
  chat:     { icon: MessageSquare, label: "Chat Agent",     color: "#7C3AED", bg: "#EDE9FE" },
};

const TEMPLATES = [
  {
    slug: "dental",
    name: "Dental Clinic Receptionist",
    industry: "Healthcare",
    channel: "chat",
    desc: "Handle incoming enquiries, book appointments and answer common dental queries.",
    icon: Stethoscope,
    color: "#3B82F6",
    bg: "#EFF6FF",
    prompt: "You are a friendly receptionist for a dental clinic. Greet visitors warmly, help them book the soonest appointment in their preferred location, collect their name and phone number, and confirm the booking. Defer all medical questions to the dentist.",
    flow: ["Greet visitor", "Identify intent (book / reschedule / query)", "Collect name + phone", "Offer available slots", "Confirm booking", "Send confirmation"],
    useCases: ["Appointment booking", "Reschedule / cancel", "Clinic timings & locations", "Insurance acceptance queries", "Doctor availability"],
  },
  {
    slug: "realestate",
    name: "Real Estate Assistant",
    industry: "Real Estate",
    channel: "chat",
    desc: "Qualify leads, answer property questions and book site visits automatically.",
    icon: Home,
    color: "#22C55E",
    bg: "#ECFDF5",
    prompt: "You are a real estate buying assistant. Qualify leads by budget, location and timeline. Share matching properties from the catalogue and offer to book a site visit. Capture lead details and push them to HubSpot.",
    flow: ["Capture lead intent (buy / rent)", "Ask budget & location", "Recommend 3 best matches", "Show property details", "Book site visit", "Push lead to CRM"],
    useCases: ["New buyer qualification", "Site visit scheduling", "Property comparison", "Loan pre-approval guidance", "Post-visit follow-up"],
  },
  {
    slug: "carservice",
    name: "Car Service Booking",
    industry: "Automotive",
    channel: "chat",
    desc: "Book car services, answer queries and send reminders automatically.",
    icon: Car,
    color: "#22C55E",
    bg: "#ECFDF5",
    prompt: "You are a car service booking agent. Identify the vehicle make/model, suggest the right service package, offer pickup-and-drop, and book the slot. Send reminders 24 hours before.",
    flow: ["Ask car make / model", "Identify service type", "Quote price", "Schedule pickup", "Confirm booking", "Send reminder 24h before"],
    useCases: ["Periodic service booking", "Breakdown assistance", "Pickup & drop scheduling", "Insurance claim guidance", "Service history lookup"],
  },
  {
    slug: "insurance",
    name: "Insurance Support Agent",
    industry: "Insurance",
    channel: "chat",
    desc: "Answer policy questions, help with claims and connect customers to agents.",
    icon: ShieldCheck,
    color: "#8B5CF6",
    bg: "#F3E8FF",
    prompt: "You are an insurance customer-support agent. Help customers find their policy, answer common questions about coverage, premiums and renewals, and initiate claim requests. Escalate complex queries to a human.",
    flow: ["Verify customer identity", "Look up policy details", "Answer coverage questions", "Initiate claim if needed", "Schedule callback", "Send summary email"],
    useCases: ["Policy renewal reminders", "Claim status enquiries", "Premium calculation", "Coverage explanation", "Document collection"],
  },
  {
    slug: "restaurant",
    name: "Restaurant Reservation",
    industry: "Hospitality",
    channel: "chat",
    desc: "Take reservations, manage bookings and answer menu & availability queries.",
    icon: Utensils,
    color: "#EC4899",
    bg: "#FCE7F3",
    prompt: "You are the AI host for a fine-dining restaurant. Greet guests, help them book a table, offer menu highlights, and handle modifications. Always confirm party size, date, time and special requests.",
    flow: ["Greet guest", "Capture party size", "Offer available slots", "Confirm dietary preferences", "Send reservation card", "Reminder 1 hour before"],
    useCases: ["Table reservations", "Special occasion bookings", "Menu queries", "Group bookings", "Cancellation handling"],
  },
  {
    slug: "leadqual",
    name: "Lead Qualification Agent",
    industry: "B2B SaaS",
    channel: "chat",
    desc: "Qualify leads, answer questions and route hot leads to your sales team.",
    icon: Users,
    color: "#3B82F6",
    bg: "#EFF6FF",
    prompt: "You are a B2B SaaS lead qualifier. Use the BANT framework (Budget, Authority, Need, Timeline) to qualify visitors. Hot leads are routed to sales; cold leads get a nurture sequence.",
    flow: ["Identify visitor company", "Run BANT questions", "Score the lead", "Route hot leads to sales", "Send brochure to cold leads", "Schedule demo if interested"],
    useCases: ["Inbound lead routing", "Demo scheduling", "Pricing-page chat", "Free-trial conversion", "Sales-rep handoff"],
  },
];

export default function TemplatesPage() {
  useSEO({
    title: "Templates",
    description: "Quick-start with pre-built AI agent templates for your business needs.",
  });

  const [open, setOpen] = useState(null);

  return (
    <div className="bg-white">
      {/* HERO */}
      <section className="relative pt-24 pb-16 overflow-hidden bg-gradient-to-b from-[#F8FAFC] via-white to-white">
        <Sparkle top="18%" left="8%"  color="#3B82F6" />
        <Sparkle top="14%" left="32%" color="#22C55E" />
        <Sparkle top="46%" left="6%"  color="#06B6D4" />
        <Sparkle top="22%" right="10%" color="#F59E0B" />
        <Sparkle top="60%" right="8%"  color="#3B82F6" />
        <Sparkle top="68%" right="32%" color="#8B5CF6" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.span {...fadeUp} className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EFF6FF] text-xs font-bold tracking-[0.2em] text-[#2563EB]">
            <Sparkles size={11} /> AI AGENT TEMPLATES
          </motion.span>
          <motion.h1 {...fadeUp} className="mt-6 text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tighter text-[#0F172A]">
            Pre-built <span className="gradient-text">AI Agent</span> Templates
          </motion.h1>
          <motion.p {...fadeUp} className="mt-5 text-[#64748B] max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
            Quick-start with ready-to-use AI agent templates — preview the prompt, conversation flow and one-click deploy.
          </motion.p>
        </div>
      </section>

      {/* TEMPLATE GRID */}
      <section className="pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {TEMPLATES.map((t, i) => {
              const ch = CHANNEL[t.channel];
              return (
                <motion.div
                  key={t.slug}
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.05, duration: 0.5 }}
                  className="group rounded-3xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/40 hover:shadow-premium-lg transition-all p-6 flex flex-col"
                  data-testid={`template-card-${t.slug}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="size-14 aspect-square rounded-2xl grid place-items-center" style={{ background: t.bg }}>
                        <t.icon size={28} style={{ color: t.color }} strokeWidth={1.75} />
                      </div>
                      <div>
                        <span className="text-[10.5px] font-bold tracking-wider text-[#94A3B8] uppercase">{t.industry}</span>
                        <span className={`ml-1.5 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold`} style={{ background: ch.bg, color: ch.color }}>
                          <ch.icon size={9} /> {ch.label}
                        </span>
                      </div>
                    </div>
                  </div>
                  <h3 className="mt-4 text-lg font-bold tracking-tight text-[#0F172A] leading-snug">{t.name}</h3>
                  <p className="mt-2 text-sm text-[#64748B] leading-relaxed flex-1">{t.desc}</p>
                  <div className="mt-5 flex items-center gap-2">
                    <button
                      onClick={() => setOpen(t.slug)}
                      data-testid={`template-${t.slug}-preview`}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-[#E2E8F0] hover:border-[#2563EB] hover:text-[#2563EB] text-[#0F172A] text-sm font-semibold transition-all"
                    >
                      <Eye size={13} /> Preview
                    </button>
                    <Link
                      to="/signup"
                      data-testid={`template-${t.slug}-deploy`}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_6px_16px_-6px_rgba(37,99,235,0.5)] transition-all"
                    >
                      <Rocket size={13} /> Deploy
                    </Link>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* MORE TEMPLATES */}
      <section className="pb-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="rounded-3xl bg-[#F8FAFC] border border-[#E2E8F0] p-6 sm:p-8">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
              <div className="size-16 rounded-2xl bg-white border border-[#E2E8F0] grid place-items-center shadow-sm flex-shrink-0">
                <Rocket size={28} className="text-[#2563EB]" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-xl font-bold tracking-tight text-[#0F172A]">More templates coming soon!</h3>
                <p className="mt-1.5 text-sm text-[#64748B] leading-relaxed max-w-2xl">
                  We&apos;re building more industry-specific AI agent templates — Logistics, EdTech, FinTech and more.
                </p>
              </div>
              <Link to="/contact" data-testid="templates-request-cta" className="px-5 py-3 rounded-xl border border-[#CBD5E1] bg-white hover:border-[#2563EB] hover:text-[#2563EB] text-[#0F172A] font-semibold text-sm inline-flex items-center gap-2 transition-all whitespace-nowrap">
                Request a Template <ArrowRight size={14} />
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* PREVIEW MODAL */}
      <AnimatePresence>
        {open && (
          <PreviewModal template={TEMPLATES.find((t) => t.slug === open)} onClose={() => setOpen(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}

function PreviewModal({ template, onClose }) {
  const [copied, setCopied] = useState(false);
  if (!template) return null;
  const ch = CHANNEL[template.channel];

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(template.prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) { /* clipboard unavailable */ }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 bg-[#0F172A]/60 backdrop-blur-sm grid place-items-center px-4 py-8"
      data-testid="template-preview-modal"
    >
      <motion.div
        initial={{ y: 16, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 16, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-white rounded-3xl shadow-2xl"
      >
        {/* header */}
        <div className="px-6 py-5 border-b border-[#E2E8F0] flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="size-12 rounded-2xl grid place-items-center" style={{ background: template.bg }}>
              <template.icon size={24} style={{ color: template.color }} />
            </div>
            <div>
              <p className="text-[10.5px] font-bold tracking-wider text-[#94A3B8] uppercase">{template.industry}</p>
              <h3 className="text-lg font-bold text-[#0F172A]">{template.name}</h3>
              <span className="mt-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10.5px] font-semibold" style={{ background: ch.bg, color: ch.color }}>
                <ch.icon size={10} /> {ch.label}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-[#0F172A]" data-testid="template-preview-close">
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Agent Prompt */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">AGENT PROMPT</p>
              <button onClick={copy} className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-[#64748B] hover:text-[#2563EB]">
                {copied ? <Check size={11} /> : <Copy size={11} />}
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div className="rounded-xl bg-[#0F172A] p-4 text-[13px] text-[#E2E8F0] leading-relaxed font-mono">
              {template.prompt}
            </div>
          </div>

          {/* Conversation Flow */}
          <div>
            <p className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB] mb-3">CONVERSATION FLOW</p>
            <div className="space-y-1.5">
              {template.flow.map((step, i, arr) => (
                <React.Fragment key={step}>
                  <div className="px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-[#EFF6FF] to-white border border-[#E0E7FF] text-[13px] font-semibold text-[#0F172A] flex items-center gap-2.5">
                    <span className="size-6 rounded-full bg-[#2563EB] text-white text-[10.5px] font-bold grid place-items-center">{i + 1}</span>
                    {step}
                  </div>
                  {i < arr.length - 1 && (
                    <div className="flex justify-center">
                      <ArrowDown size={12} className="text-[#94A3B8]" />
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          {/* Use Cases */}
          <div>
            <p className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB] mb-3">USE CASES</p>
            <ul className="grid sm:grid-cols-2 gap-2">
              {template.useCases.map((u) => (
                <li key={u} className="flex items-start gap-2 px-3 py-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-[13px] text-[#0F172A]">
                  <CheckCircle2 size={13} className="text-[#16A34A] mt-0.5 flex-shrink-0" /> {u}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="px-6 py-4 bg-[#F8FAFC] border-t border-[#E2E8F0] flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-sm font-semibold text-[#475569] hover:bg-[#E2E8F0]">
            Close
          </button>
          <Link
            to="/signup"
            data-testid="template-preview-deploy"
            className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_6px_16px_-6px_rgba(37,99,235,0.5)]"
          >
            <Rocket size={13} /> Deploy Template
          </Link>
        </div>
      </motion.div>
    </motion.div>
  );
}

function Sparkle({ top, left, right, color }) {
  return (
    <svg className="absolute" style={{ top, left, right }} width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 0 L9.6 6.4 L16 8 L9.6 9.6 L8 16 L6.4 9.6 L0 8 L6.4 6.4 Z" fill={color} opacity="0.7" />
    </svg>
  );
}
