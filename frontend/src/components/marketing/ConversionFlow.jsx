import React from "react";
import { motion } from "framer-motion";
import { MessageSquare, Sparkles, CheckCircle2, UserPlus, Building2 } from "lucide-react";

const STEPS = [
  {
    icon: MessageSquare,
    label: "Customer message",
    detail: "\u201cDo you have a Growth plan?\u201d",
    tone: "#2563EB",
    bg: "#EFF6FF",
  },
  {
    icon: Sparkles,
    label: "AI agent responds",
    detail: "Answers from your knowledge base, in your tone",
    tone: "#7C3AED",
    bg: "#F5F3FF",
  },
  {
    icon: CheckCircle2,
    label: "Qualified",
    detail: "Budget, timeline & intent captured automatically",
    tone: "#0EA5E9",
    bg: "#ECFEFF",
  },
  {
    icon: UserPlus,
    label: "Lead captured",
    detail: "Scored and tagged the moment the chat ends",
    tone: "#16A34A",
    bg: "#ECFDF5",
  },
  {
    icon: Building2,
    label: "Sent to your CRM",
    detail: "Salesforce, HubSpot, Zoho or a webhook of your choice",
    tone: "#0F172A",
    bg: "#F1F5F9",
  },
];

/**
 * ConversionFlow — a compact, on-brand product visualization showing one
 * conversation turning into a CRM-ready lead. Coded (not a raster image) so
 * it stays crisp at every size and matches the existing hand-built
 * illustration system (see HeroOrb.jsx).
 */
export default function ConversionFlow() {
  return (
    <div
      className="rounded-3xl border border-[#E2E8F0] bg-white p-6 sm:p-8"
      role="img"
      aria-label="A customer message is answered by the AI agent, qualified, captured as a lead, and sent to your CRM."
    >
      <div className="flex flex-col md:flex-row md:items-stretch gap-3 md:gap-2">
        {STEPS.map((s, i) => (
          <React.Fragment key={s.label}>
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{ delay: i * 0.08, duration: 0.4 }}
              className="flex-1 min-w-0 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-4 flex flex-col items-start gap-2.5"
            >
              <div
                className="size-9 rounded-lg grid place-items-center shrink-0"
                style={{ background: s.bg }}
              >
                <s.icon size={17} style={{ color: s.tone }} />
              </div>
              <p className="text-[13px] font-semibold text-[#0F172A] leading-snug">{s.label}</p>
              <p className="text-[11.5px] text-[#64748B] leading-snug">{s.detail}</p>
            </motion.div>
            {i < STEPS.length - 1 && (
              <div
                className="hidden md:flex items-center justify-center shrink-0 w-6"
                aria-hidden="true"
              >
                <svg width="20" height="14" viewBox="0 0 20 14" fill="none">
                  <path d="M1 7h14M10 1l6 6-6 6" stroke="#94A3B8" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            )}
            {i < STEPS.length - 1 && (
              <div className="flex md:hidden items-center justify-center shrink-0 h-4" aria-hidden="true">
                <svg width="14" height="20" viewBox="0 0 14 20" fill="none">
                  <path d="M7 1v14M1 10l6 6 6-6" stroke="#94A3B8" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
