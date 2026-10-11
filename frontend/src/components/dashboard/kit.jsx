import React from "react";
import { Link } from "react-router-dom";
import { TrendingUp } from "lucide-react";
import { COLOR, RADIUS, SHADOW } from "@/constants/tokens";

/* ──────────────────────────────────────────────────────────────────────────
   OraOne dashboard UI kit — "Luminous"
   Small set of premium, consistent building blocks used across every
   dashboard page so the whole product feels cohesive and high-end.
   All visual values come from the VDS token layer (@/constants/tokens).
   ────────────────────────────────────────────────────────────────────────── */

export { COLOR, RADIUS, SHADOW };

// Legacy aliases kept so existing pages keep importing the same names — now
// sourced from the single token layer instead of scattered literals.
export const BRAND = COLOR.brand;
export const BRAND2 = "#06B6D4"; // cyan (brand secondary)
export const INK = COLOR.ink;
export const SUB = COLOR.sub;
export const MUTED = COLOR.faint;
export const LINE = COLOR.line;

export const cx = (...c) => c.filter(Boolean).join(" ");

/* Page header — clean, reference style: soft icon chip + bold title + actions. */
export function PageHeader({ eyebrow, title, subtitle, actions, icon: Icon }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-[12px] font-semibold uppercase tracking-[0.14em] text-faint">
            {eyebrow}
          </p>
        )}
        <div className={cx("flex items-center gap-3", eyebrow && "mt-1.5")}>
          {Icon && (
            <span className="grid size-10 place-items-center rounded-xl bg-brand-soft text-brand">
              <Icon size={19} />
            </span>
          )}
          <h1 className="text-[24px] sm:text-[28px] font-extrabold tracking-tight text-ink truncate">
            {title}
          </h1>
        </div>
        {subtitle && <p className="mt-1.5 text-sm text-sub">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/* Clean surface card. */
export function Card({ className = "", children, hover = false, ...rest }) {
  return (
    <div
      className={cx(
        "rounded-2xl border border-line bg-white shadow-card",
        hover && "transition-all hover:-translate-y-0.5 hover:shadow-cardhover",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

/* Trend chip. */
export function Delta({ up, children }) {
  return (
    <span
      className="inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] font-semibold"
      style={{ color: up ? "#067647" : "#B42318", background: up ? "#ECFDF3" : "#FEF3F2" }}
    >
      <TrendingUp size={11} style={{ transform: up ? "none" : "scaleY(-1)" }} />
      {children}
    </span>
  );
}

/* KPI / stat card — reference style: icon chip + label on top, big value, delta + sub. */
export function StatCard({ icon: Icon, label, value, sub, delta, up, tone = BRAND, bg = "#EFF4FF", to }) {
  const inner = (
    <Card hover className="h-full p-5">
      <div className="flex items-center gap-2.5">
        <span className="grid size-9 place-items-center rounded-xl" style={{ background: bg }}>
          {Icon && <Icon size={17} style={{ color: tone }} />}
        </span>
        <span className="text-[13.5px] font-semibold text-[#475569]">{label}</span>
      </div>
      <p className="mt-4 text-[28px] font-extrabold leading-none tracking-tight text-[#0F172A]">{value}</p>
      <div className="mt-3 flex items-center gap-2 text-[11.5px] text-[#94A3B8]">
        {delta && <Delta up={up}>{delta}</Delta>}
        {sub && <span>{sub}</span>}
      </div>
    </Card>
  );
  return to ? <Link to={to} className="block">{inner}</Link> : inner;
}

/* Section heading with icon chip. */
export function SectionTitle({ icon: Icon, title, subtitle, tone = BRAND, right }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-3">
      <div className="flex items-center gap-2.5">
        {Icon && (
          <span className="grid size-7 place-items-center rounded-lg" style={{ background: `${tone}15` }}>
            <Icon size={14} style={{ color: tone }} />
          </span>
        )}
        <div>
          <h2 className="text-[15px] font-bold text-[#0F172A]">{title}</h2>
          {subtitle && <p className="text-[11.5px] text-[#64748B]">{subtitle}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}

/* Segmented toggle — pill style. */
export function Segmented({ value, onChange, options }) {
  return (
    <div className="inline-flex rounded-full bg-[#F1F5F9] p-0.5">
      {options.map((o) => {
        const v = typeof o === "string" ? o : o.value;
        const label = typeof o === "string" ? o : o.label;
        const active = value === v;
        return (
          <button
            key={v}
            onClick={() => onChange(v)}
            aria-pressed={active}
            className={cx(
              "rounded-full px-4 py-1.5 text-sm font-semibold capitalize transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40",
              active ? "bg-white text-[#0F172A] shadow-sm" : "text-[#64748B] hover:text-[#0F172A]"
            )}
          >
            {label}
            {typeof o !== "string" && o.badge && (
              <span className="ml-1.5 text-[11px] font-semibold text-[#16A34A]">{o.badge}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* Status badge. */
const TONES = {
  green: "bg-[#DCFCE7] text-[#15803D]",
  blue: "bg-[#DBEAFE] text-[#1D4ED8]",
  indigo: "bg-[#F0F9FF] text-[#0369A1]",
  amber: "bg-[#FEF3C7] text-[#B45309]",
  red: "bg-[#FEE2E2] text-[#B91C1C]",
  slate: "bg-[#F1F5F9] text-[#475569]",
};
export function Badge({ tone = "slate", children, className = "" }) {
  return (
    <span className={cx("rounded-full px-2 py-0.5 text-[11px] font-semibold capitalize", TONES[tone] || TONES.slate, className)}>
      {children}
    </span>
  );
}

/* Ghost / outline button — pill. */
export function GhostButton({ as: As = "button", className = "", children, ...rest }) {
  return (
    <As
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-full border border-stroke bg-white px-4 py-2 text-sm font-semibold text-body transition-colors hover:bg-wash focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 focus-visible:ring-offset-2",
        className
      )}
      {...rest}
    >
      {children}
    </As>
  );
}

/* Primary button — flat brand, pill. */
export function PrimaryButton({ as: As = "button", className = "", children, ...rest }) {
  return (
    <As
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-hover disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 focus-visible:ring-offset-2",
        className
      )}
      {...rest}
    >
      {children}
    </As>
  );
}

/* Empty state. */
export function EmptyState({ icon: Icon, title, hint, action }) {
  return (
    <div className="rounded-2xl border border-dashed border-stroke bg-white p-10 text-center">
      {Icon && (
        <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-subtle text-faint">
          <Icon size={22} />
        </span>
      )}
      {title && <p className="mt-3 text-sm font-semibold text-ink">{title}</p>}
      {hint && <p className="mt-1 text-[13px] text-sub">{hint}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
