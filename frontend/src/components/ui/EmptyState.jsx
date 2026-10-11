import React from "react";
import { OraMark } from "@/components/marketing/Logo";

/**
 * EmptyState — branded empty-state block built around the OraOne logo.
 *
 * Props:
 *  - title, description: content
 *  - actionLabel, onAction: primary CTA
 *  - secondaryLabel, onSecondary: optional secondary CTA
 *  - icon: legacy lucide-react component (overrides the logo visual when provided)
 *  - tone: 'blue' | 'violet' | 'green' | 'amber' (only affects legacy icon mode)
 *  - size: 'sm' | 'md' (default) | 'lg' — controls orb scale + padding
 *  - dashed: bool — dashed vs solid border (default true)
 *  - testId, className
 */
const TONES = {
  blue:   { bg: "#EFF6FF", fg: "#2563EB" },
  violet: { bg: "#F5F3FF", fg: "#7C3AED" },
  green:  { bg: "#ECFDF5", fg: "#16A34A" },
  amber:  { bg: "#FEF3C7", fg: "#D97706" },
};

const SIZES = {
  sm: { pad: "px-6 py-10", orb: 84,  title: "text-base",  desc: "text-[13px]" },
  md: { pad: "px-6 py-12", orb: 110, title: "text-lg",    desc: "text-sm" },
  lg: { pad: "px-6 py-16", orb: 140, title: "text-xl",    desc: "text-[15px]" },
};

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  secondaryLabel,
  onSecondary,
  icon: Icon, // legacy
  showOrb = true,
  tone = "blue",
  size = "md",
  dashed = true,
  className = "",
  testId = "empty-state",
}) {
  const s = SIZES[size] || SIZES.md;
  const t = TONES[tone] || TONES.blue;
  const border = dashed ? "border-2 border-dashed border-[#E2E8F0]" : "border border-[#E2E8F0]";

  return (
    <div
      className={`relative overflow-hidden text-center ${s.pad} rounded-2xl bg-white ${border} ${className}`}
      role="status"
      aria-live="polite"
      data-testid={testId}
    >
      {/* Subtle dotted backdrop */}
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-[0.4] pointer-events-none"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, rgba(37,99,235,0.06) 1px, transparent 0)",
          backgroundSize: "22px 22px",
        }}
      />

      <div className="relative">
        {/* Visual: OraOne logo (default) or legacy lucide icon */}
        {Icon ? (
          <div
            className="mx-auto size-14 rounded-2xl grid place-items-center"
            style={{ background: t.bg }}
          >
            <Icon size={22} style={{ color: t.fg }} aria-hidden="true" />
          </div>
        ) : showOrb ? (
          <div className="mx-auto inline-block">
            <OraMark size={s.orb} />
          </div>
        ) : null}

        {title && (
          <h3 className={`${Icon || showOrb ? "mt-5" : ""} ${s.title} font-bold tracking-tight text-[#0F172A]`}>
            {title}
          </h3>
        )}
        {description && (
          <p className={`mt-1.5 ${s.desc} text-[#64748B] max-w-md mx-auto leading-relaxed`}>
            {description}
          </p>
        )}

        {(actionLabel || secondaryLabel) && (
          <div className="mt-6 flex items-center justify-center gap-2 flex-wrap">
            {actionLabel && onAction && (
              <button
                type="button"
                onClick={onAction}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_10px_24px_-8px_rgba(37,99,235,0.55)] transition-all hover:-translate-y-0.5"
                data-testid={`${testId}-action`}
              >
                {actionLabel}
              </button>
            )}
            {secondaryLabel && onSecondary && (
              <button
                type="button"
                onClick={onSecondary}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white border border-[#E2E8F0] hover:bg-[#F8FAFC] text-[#0F172A] text-sm font-semibold transition-colors"
                data-testid={`${testId}-secondary`}
              >
                {secondaryLabel}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default EmptyState;
