import { Link } from "react-router-dom";
import { OraMark } from "@/components/marketing/Logo";
import WorkspaceIllustration from "@/components/marketing/WorkspaceIllustration";
import {
  Check,
  ArrowRight,
  ArrowUpRight,
  ShieldCheck,
  LockKeyhole,
} from "lucide-react";

/* ── Auth brand mark (swirl + ORAONE wordmark, matches design) ── */
export function AuthBrand() {
  return (
    <div className="flex items-center gap-2.5">
      <OraMark size={32} />
      <span className="text-xl font-bold leading-none tracking-tight">
        <span className="text-[#0F172A]">Ora</span>
        <span className="text-[#1E293B]">One</span>
      </span>
    </div>
  );
}

/* ── Brand / inline glyphs ─────────────────────────────────── */

export function Hexagon({ size = 16 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 2 20.5 7v10L12 22 3.5 17V7z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

/* ── Auth-side product illustration ───────────────────────── */
function WorkspacePreview() {
  return <WorkspaceIllustration compact />;
}

/* ── Editorial panel based on the approved Lovable direction ─ */
function MarketingPanel() {
  return (
    <aside className="relative hidden flex-col justify-center overflow-hidden border-r border-[#E2E8F0] bg-[#F8FAFC] px-8 py-10 lg:flex xl:px-12">
      <div
        className="pointer-events-none absolute -right-24 -top-24 size-[26rem] rounded-full bg-[radial-gradient(circle,rgba(37,99,235,0.10),transparent_68%)]"
        aria-hidden="true"
      />
      <div className="relative w-full max-w-xl py-6">
        <p className="mb-4 text-sm font-semibold text-[#2563EB]">
          Your OraOne workspace
        </p>
        <h2 className="max-w-lg text-3xl font-bold leading-[1.25] tracking-tight text-[#0F172A] xl:text-4xl">
          More context.
          <br />
          Better conversations.
        </h2>
        <p className="mt-5 max-w-md text-base leading-relaxed text-[#475569]">
          Bring your assistant, the knowledge it uses, and customer
          conversations together in one place.
        </p>
        <WorkspacePreview />
      </div>
      <p className="relative text-xs text-[#64748B]">
        A clear view of the work behind every conversation.
      </p>
    </aside>
  );
}

/* ── Trust badges footer (inside each card) ────────────────── */
export function TrustBadges() {
  return (
    <div className="mt-7 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 border-t border-[#EEF0F6] pt-5 text-xs text-[#64748B]">
      <span className="inline-flex items-center gap-1.5">
        <LockKeyhole size={14} aria-hidden="true" /> Email-only access
      </span>
      <span className="inline-flex items-center gap-1.5">
        <ShieldCheck size={14} aria-hidden="true" /> No social sign-in
      </span>
    </div>
  );
}

/* ── Shared right-side UI primitives ───────────────────────── */
export function IconBadge({ icon: Icon, check = false }) {
  return (
    <div className="relative mb-5 grid size-12 place-items-center rounded-lg bg-[#EFF6FF]">
      <Icon size={23} className="text-[#2563EB]" />
      {check && (
        <span className="absolute -bottom-0.5 right-1 grid size-7 place-items-center rounded-full bg-[#16A34A] text-white ring-4 ring-white">
          <Check size={14} strokeWidth={3} />
        </span>
      )}
    </div>
  );
}

export function GradientButton({
  children,
  trailingIcon: TrailingIcon,
  busy = false,
  busyLabel,
  ...props
}) {
  return (
    <button
      {...props}
      disabled={busy || props.disabled}
      className="group flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#2563EB] py-3 text-[15px] font-semibold text-white transition-colors hover:bg-[#1D4ED8] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {busy ? busyLabel || "Please wait..." : children}
      {!busy && TrailingIcon && (
        <TrailingIcon
          size={17}
          className="transition-transform group-hover:translate-x-0.5"
        />
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

export function OutlineButton({
  children,
  leadingIcon: LeadingIcon = ArrowRight,
  to,
  ...props
}) {
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
        {title && (
          <span className="font-semibold text-[#0F172A]">{title} </span>
        )}
        {children}
      </p>
    </div>
  );
}

/* ── Shell wrapper ─────────────────────────────────────────── */
export function AuthShell({ children, cardMaxWidth = "max-w-lg", cardTestId }) {
  return (
    <div
      className="oraone-auth flex min-h-dvh flex-col bg-white"
      data-testid="auth-page"
    >
      <header className="mx-auto flex w-full max-w-[1440px] items-center justify-between border-b border-[#E2E8F0] px-5 py-5 sm:px-8">
        <Link to="/" aria-label="OraOne home">
          <AuthBrand />
        </Link>
        <Link
          to="/contact"
          className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-[#475569]"
        >
          Need help? <ArrowUpRight size={15} />
        </Link>
      </header>
      <div className="mx-auto grid min-h-[640px] w-full max-w-[1440px] flex-1 lg:grid-cols-2">
        <MarketingPanel />

        <div className="flex min-w-0 flex-col justify-center bg-white px-5 py-8 sm:px-8 lg:px-12">
          <main
            data-testid={cardTestId}
            className={`oraone-auth-main my-auto w-full ${cardMaxWidth} self-center py-2 sm:py-4`}
          >
            {children}
            <TrustBadges />
          </main>
        </div>
      </div>
      <footer className="flex flex-wrap items-center justify-between gap-4 bg-[#0F172A] px-5 py-5 text-sm text-white sm:px-8">
        <span>© {new Date().getFullYear()} OraOne</span>
        <div className="flex items-center gap-5">
          <Link className="hover:underline" to="/privacy">
            Privacy
          </Link>
          <Link className="hover:underline" to="/terms">
            Terms
          </Link>
          <Link
            className="inline-flex items-center gap-1 hover:underline"
            to="/contact"
          >
            Get help <ArrowUpRight size={13} aria-hidden="true" />
          </Link>
        </div>
      </footer>
    </div>
  );
}
