import React from "react";
import { Link } from "react-router-dom";
import { OraMark } from "@/components/marketing/Logo";
import {
  Headset,
  BookOpen,
  Users,
  ShieldCheck,
  Zap,
  Crown,
  MessagesSquare,
  BarChart3,
  Bot,
  Check,
  Lock,
  ArrowRight,
} from "lucide-react";

/* ── Auth brand mark (swirl + ORAONE wordmark, matches design) ── */
export function AuthBrand() {
  return (
    <div className="flex items-center gap-2.5">
      <OraMark size={38} />
      <span className="text-[21px] font-extrabold uppercase leading-none tracking-[0.04em]">
        <span className="text-[#0F172A]">Ora</span>
        <span className="text-[#1E293B]">One</span>
      </span>
    </div>
  );
}

/* ── Brand / inline glyphs ─────────────────────────────────── */

export function Hexagon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 2 20.5 7v10L12 22 3.5 17V7z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

/* ── Left-panel data ───────────────────────────────────────── */
const FEATURES = [
  { icon: Headset, tone: "blue", title: "AI Chat Agents", desc: "Human-like conversations that convert." },
  { icon: MessagesSquare, tone: "green", title: "Website Widget", desc: "Drop it on any site in one line." },
  { icon: BookOpen, tone: "cyan", title: "Knowledge Base AI", desc: "Instant answers from your data." },
  { icon: Users, tone: "blue", title: "Lead Intelligence", desc: "Capture, qualify & convert leads." },
  { icon: ShieldCheck, tone: "cyan", title: "Enterprise Security", desc: "Your data is safe with us." },
];

const TONES = {
  violet: "bg-[#EFF6FF] text-[#2563EB]",
  green: "bg-[#ECFDF5] text-[#16A34A]",
  blue: "bg-[#EFF4FF] text-[#2563EB]",
  cyan: "bg-[#ECFEFF] text-[#0891B2]",
  pink: "bg-[#ECFEFF] text-[#0891B2]",
  amber: "bg-[#FFF7ED] text-[#F59E0B]",
  indigo: "bg-[#EFF4FF] text-[#2563EB]",
};

const STATS = [
  { icon: ShieldCheck, tone: "blue", value: "99.9%", label: "Uptime" },
  { icon: Zap, tone: "cyan", value: "24/7", label: "AI Availability" },
  { icon: Crown, tone: "amber", value: "Enterprise", label: "Ready" },
];

const TRUST = [
  { icon: ShieldCheck, lines: ["Protected by", "Argon2 + JWT"] },
  { icon: Hexagon, lines: ["SOC 2", "Ready"] },
  { icon: Lock, lines: ["256-bit", "Encryption"] },
];

/* ── Decorative conversation flow ──────────────────────────── */
function ChatFlow() {
  return (
    <div className="relative h-[300px] w-[300px]" aria-hidden="true">
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 300 300" fill="none">
        <path d="M250 40 C250 90 120 90 120 130" stroke="#CBD5E1" strokeWidth="2" strokeDasharray="4 5" />
        <path d="M210 150 C260 160 260 210 220 220" stroke="#CBD5E1" strokeWidth="2" strokeDasharray="4 5" />
      </svg>

      <div className="absolute right-6 top-0 grid size-10 place-items-center rounded-xl bg-white text-[#2563EB] shadow-[0_10px_30px_-12px_rgba(15,23,42,0.35)]">
        <MessagesSquare size={18} />
      </div>

      <div className="absolute left-4 top-16 w-[190px] rounded-2xl border border-[#EEF0F6] bg-white p-3 shadow-[0_16px_40px_-20px_rgba(15,23,42,0.35)]">
        <div className="flex items-start gap-2.5">
          <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-[#EFF6FF] text-[#2563EB]">
            <Bot size={15} />
          </span>
          <div>
            <p className="text-xs font-bold text-[#0F172A]">AI Agent</p>
            <p className="mt-0.5 text-[11px] leading-snug text-[#64748B]">Hello! How can I help you today?</p>
          </div>
        </div>
      </div>

      <div className="absolute right-1 top-[150px] flex items-center gap-2">
        <span className="rounded-xl border border-[#EEF0F6] bg-white px-3 py-2 text-[11px] font-medium text-[#334155] shadow-[0_12px_30px_-18px_rgba(15,23,42,0.4)]">
          Book a demo please
        </span>
        <span className="grid size-7 place-items-center rounded-full bg-[#E2E8F0] text-[#64748B]">
          <Users size={14} />
        </span>
      </div>

      <div className="absolute left-8 top-[210px] flex items-center gap-2.5 rounded-2xl border border-[#EEF0F6] bg-white p-3 shadow-[0_16px_40px_-20px_rgba(15,23,42,0.35)]">
        <div>
          <p className="text-[11px] font-semibold leading-snug text-[#0F172A]">Demo scheduled</p>
          <p className="text-[11px] leading-snug text-[#64748B]">for tomorrow at 11:00 AM</p>
        </div>
        <span className="grid size-6 shrink-0 place-items-center rounded-full bg-[#16A34A] text-white">
          <Check size={13} strokeWidth={3} />
        </span>
      </div>

      <div className="absolute bottom-0 right-10 grid size-10 place-items-center rounded-xl bg-white text-[#0891B2] shadow-[0_10px_30px_-12px_rgba(15,23,42,0.35)]">
        <BarChart3 size={18} />
      </div>
    </div>
  );
}

/* ── Left marketing panel ──────────────────────────────────── */
function MarketingPanel() {
  return (
    <div className="relative hidden flex-col px-8 py-8 lg:flex xl:px-16 xl:py-10">
      <AuthBrand />

      <div className="flex flex-1 flex-col justify-center gap-12">
        <div className="relative">
          <div className="max-w-lg">
            <span className="inline-block rounded-full bg-[#EFF6FF] px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#2563EB]">
              One AI. Every Conversation
            </span>
            <h1 className="mt-4 text-[42px] font-extrabold leading-[1.04] tracking-tight text-[#0F172A] xl:text-[46px]">
              Build.
              <br />
              Automate.
              <br />
              <span className="bg-gradient-to-r from-[#2563EB] to-[#06B6D4] bg-clip-text text-transparent">
                Scale.
              </span>
            </h1>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-[#475569]">
              OraOne helps businesses automate conversations, capture leads, and scale operations with
              advanced AI agents.
            </p>
          </div>

          <div className="pointer-events-none absolute right-0 top-0 hidden origin-top-right scale-[0.82] lg:block xl:scale-90">
            <ChatFlow />
          </div>
        </div>

        <div className="space-y-3.5">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-2xl border border-[#EEF0F6] bg-white p-4 shadow-[0_10px_30px_-22px_rgba(15,23,42,0.4)]">
              <span className={`grid size-10 place-items-center rounded-xl ${TONES[f.tone]}`}>
                <f.icon size={20} />
              </span>
              <p className="mt-3 text-[13px] font-bold leading-tight text-[#0F172A]">{f.title}</p>
              <p className="mt-1 text-[11px] leading-snug text-[#475569]">{f.desc}</p>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between gap-2 rounded-2xl border border-[#EEF0F6] bg-white px-5 py-4">
          {STATS.map((s, i) => (
            <React.Fragment key={s.label}>
              {i > 0 && <span className="h-9 w-px bg-[#EEF0F6]" />}
              <div className="flex items-center gap-2.5">
                <span className={`grid size-9 place-items-center rounded-xl ${TONES[s.tone]}`}>
                  <s.icon size={18} />
                </span>
                <div>
                  <p className="text-[15px] font-extrabold leading-none text-[#0F172A]">{s.value}</p>
                  <p className="mt-1 text-[11px] text-[#475569]">{s.label}</p>
                </div>
              </div>
            </React.Fragment>
          ))}
        </div>
        </div>
      </div>
    </div>
  );
}

/* ── Trust badges footer (inside each card) ────────────────── */
export function TrustBadges() {
  return (
    <div className="mt-5 grid grid-cols-3 gap-2 border-t border-[#F1F5F9] pt-4">
      {TRUST.map((t) => (
        <div key={t.lines[1]} className="flex flex-col items-center gap-1.5 text-center">
          <span className="grid size-6 place-items-center rounded-lg bg-[#F5F7FA] text-[#64748B]">
            <t.icon size={13} />
          </span>
          <p className="text-[10px] leading-tight text-[#64748B]">
            {t.lines[0]}
            <br />
            {t.lines[1]}
          </p>
        </div>
      ))}
    </div>
  );
}

/* ── Shared right-side UI primitives ───────────────────────── */
export function IconBadge({ icon: Icon, check = false }) {
  return (
    <div className="relative mx-auto grid size-20 place-items-center rounded-full bg-gradient-to-br from-[#EFF6FF] to-[#ECFEFF]">
      <Icon size={34} className="text-[#2563EB]" />
      {check && (
        <span className="absolute -bottom-0.5 right-1 grid size-7 place-items-center rounded-full bg-[#16A34A] text-white ring-4 ring-white">
          <Check size={14} strokeWidth={3} />
        </span>
      )}
    </div>
  );
}

export function GradientButton({ children, trailingIcon: TrailingIcon, busy = false, busyLabel, ...props }) {
  return (
    <button
      {...props}
      disabled={busy || props.disabled}
      className="group flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#2563EB] to-[#06B6D4] py-3.5 text-sm font-semibold text-white shadow-[0_12px_30px_-12px_rgba(37,99,235,0.7)] transition-all hover:brightness-[1.05] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {busy ? busyLabel || "Please wait..." : children}
      {!busy && TrailingIcon && (
        <TrailingIcon size={17} className="transition-transform group-hover:translate-x-0.5" />
      )}
    </button>
  );
}

export function OrLine() {
  return (
    <div className="my-6 flex items-center gap-3">
      <div className="h-px flex-1 bg-[#EEF0F6]" />
      <span className="text-xs font-semibold text-[#94A3B8]">OR</span>
      <div className="h-px flex-1 bg-[#EEF0F6]" />
    </div>
  );
}

export function OutlineButton({ children, leadingIcon: LeadingIcon = ArrowRight, to, ...props }) {
  const cls =
    "inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[#E2E8F0] bg-white py-3.5 text-sm font-semibold text-[#2563EB] transition-all hover:border-[#CBD5E1] hover:bg-[#F8FAFC]";
  if (to) {
    return (
      <Link to={to} className={cls} {...props}>
        {LeadingIcon && <LeadingIcon size={16} />} {children}
      </Link>
    );
  }
  return (
    <button type="button" {...props} className={cls}>
      {LeadingIcon && <LeadingIcon size={16} />} {children}
    </button>
  );
}

export function TipBox({ icon: Icon = ShieldCheck, title, children }) {
  return (
    <div className="mt-5 flex items-start gap-3 rounded-2xl bg-[#EFF6FF] p-4 text-left">
      <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-white text-[#2563EB] shadow-sm">
        <Icon size={16} />
      </span>
      <p className="text-xs leading-relaxed text-[#64748B]">
        {title && <span className="font-semibold text-[#0F172A]">{title} </span>}
        {children}
      </p>
    </div>
  );
}

/* ── Shell wrapper ─────────────────────────────────────────── */
export function AuthShell({ children, cardMaxWidth = "max-w-lg", cardTestId }) {
  return (
    <div className="min-h-screen bg-[#F6F7FB]" data-testid="auth-page">
      <div className="mx-auto grid min-h-screen w-full max-w-[1500px] lg:grid-cols-[1.15fr_0.85fr]">
        <MarketingPanel />

        <div className="flex items-center justify-center p-6 sm:p-8 lg:border-l lg:border-[#E9ECF3] lg:shadow-[-24px_0_60px_-48px_rgba(15,23,42,0.25)]">
          <main
            data-testid={cardTestId}
            className={`w-full ${cardMaxWidth} rounded-3xl border border-[#EEF0F6] bg-white px-6 py-5 shadow-[0_40px_90px_-50px_rgba(15,23,42,0.4)] sm:px-7 sm:py-6`}
          >
            {children}
            <TrustBadges />
          </main>
        </div>
      </div>
    </div>
  );
}
