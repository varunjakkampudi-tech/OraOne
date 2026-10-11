import React, { useEffect, useState } from "react";
import { OraMark } from "@/components/marketing/Logo";

/* ──────────────────────────────────────────────────────────────────
   OraOne Loader System — "Aura + Conversation Waves"
   ──────────────────────────────────────────────────────────────────
   A loader vocabulary built around the OraOne identity:
   - A breathing "Aura Orb" (the AI brain) with concentric ripples
   - Dancing chat waveform bars on either side
   - Shimmering wordmark + indeterminate progress sweep
   All exports preserve their original names + data-testids.
   ────────────────────────────────────────────────────────────────── */

const C = {
  blue: "#2563EB",
  cyan: "#06B6D4",
  violet: "#0EA5E9",
  ink: "#0F172A",
  mute: "#64748B",
  ringBg: "#EEF2F7",
  darkBg: "#070B19",
  darkInk: "#E2E8F0",
};

/* ──────────────────────────────────────────────────────────────────
   AuraOrb — the signature visual: a breathing gradient orb with
   3 expanding ripple rings + a thin orbiting arc.
   ────────────────────────────────────────────────────────────────── */
export function AuraOrb({ size = 120, dark = false, animated = true }) {
  const id = React.useId();
  const ripples = [0, 0.6, 1.2]; // stagger seconds
  return (
    <div
      className="relative grid place-items-center"
      style={{ width: size, height: size }}
      data-testid="aura-orb"
    >
      {/* expanding ripples */}
      {animated && ripples.map((delay, i) => (
        <span
          key={i}
          aria-hidden="true"
          className="absolute inset-0 rounded-full aura-ripple"
          style={{
            animationDelay: `${delay}s`,
            border: `1.5px solid ${dark ? "rgba(96,165,250,0.55)" : "rgba(37,99,235,0.45)"}`,
            background: dark
              ? "radial-gradient(circle, rgba(6,182,212,0.18) 0%, rgba(37,99,235,0) 60%)"
              : "radial-gradient(circle, rgba(6,182,212,0.16) 0%, rgba(37,99,235,0) 60%)",
          }}
        />
      ))}

      {/* orbiting thin arc */}
      {animated && (
      <svg
        aria-hidden="true"
        viewBox="0 0 100 100"
        className="absolute inset-0 w-full h-full animate-spin"
        style={{ animationDuration: "3.2s" }}
      >
        <defs>
          <linearGradient id={`${id}-arc`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={C.blue} />
            <stop offset="55%" stopColor={C.cyan} />
            <stop offset="100%" stopColor={C.blue} stopOpacity="0" />
          </linearGradient>
        </defs>
        <circle
          cx="50"
          cy="50"
          r="46"
          fill="none"
          stroke={`url(#${id}-arc)`}
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeDasharray="120 200"
        />
      </svg>
      )}

      {/* orb core */}
      <div
        className={`relative rounded-full ${animated ? "aura-breathe" : ""}`}
        style={{
          width: size * 0.6,
          height: size * 0.6,
          background: dark
            ? "radial-gradient(circle at 35% 30%, #93C5FD 0%, #3B82F6 35%, #1E3A8A 75%, #0B1220 100%)"
            : "radial-gradient(circle at 35% 30%, #FFFFFF 0%, #93C5FD 28%, #2563EB 70%, #1E40AF 100%)",
          boxShadow: dark
            ? "0 0 38px 4px rgba(59,130,246,0.55), inset 0 0 18px rgba(6,182,212,0.45)"
            : "0 0 30px 2px rgba(37,99,235,0.42), inset 0 0 14px rgba(6,182,212,0.55)",
        }}
      >
        {/* inner sheen */}
        <span
          aria-hidden="true"
          className="absolute inset-0 rounded-full"
          style={{
            background:
              "conic-gradient(from 180deg, rgba(255,255,255,0.25), rgba(255,255,255,0) 35%, rgba(255,255,255,0.18) 70%, rgba(255,255,255,0) 100%)",
            mixBlendMode: "screen",
          }}
        />
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   ConversationBars — chat EQ bars that dance on each side
   of the orb. Visually communicates "every conversation".
   ────────────────────────────────────────────────────────────────── */
function ConversationBars({ count = 5, dark = false, side = "left" }) {
  const heights = [16, 28, 40, 26, 18]; // base px
  const colors = dark
    ? ["#60A5FA", "#22D3EE", "#38BDF8", "#22D3EE", "#60A5FA"]
    : [C.blue, C.cyan, "#0EA5E9", C.cyan, C.blue];
  return (
    <div
      aria-hidden="true"
      className="flex items-end gap-1.5"
      style={{ direction: side === "left" ? "rtl" : "ltr" }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <span
          key={i}
          className="block rounded-full wave-bar"
          style={{
            width: 4,
            height: heights[i % heights.length],
            background: `linear-gradient(180deg, ${colors[i % colors.length]} 0%, ${colors[(i + 1) % colors.length]} 100%)`,
            animationDelay: `${i * 0.12 + (side === "left" ? 0 : 0.06)}s`,
            opacity: dark ? 0.9 : 0.85,
          }}
        />
      ))}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   OraOneLoader — Full Page (default Suspense fallback)
   Matches the brand loading screen: spinning gradient ring around the
   OraOne swirl mark, ORAONE wordmark, tagline, progress bar + label.
   ────────────────────────────────────────────────────────────────── */
export default function OraOneLoader({
  label = "Loading…",
  fullScreen = true,
  dark = false,
}) {
  const ink = dark ? C.darkInk : "#0F172A";
  const muted = dark ? "rgba(226,232,240,0.6)" : "#64748B";
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={label}
      data-testid="oraone-loader"
      className={`${fullScreen ? "min-h-screen" : "min-h-[60vh]"} relative flex flex-col items-center justify-center gap-5 px-6`}
      style={{ background: dark ? "#070B19" : "#F6F8FC", color: ink }}
    >
      {/* Simple rotating brand mark */}
      <OraMark
        size={48}
        className="animate-spin"
        style={{ animationDuration: "0.9s" }}
      />

      {/* Label */}
      <p className="text-[13px] font-medium tracking-wide" style={{ color: muted }}>
        {label}
      </p>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   ButtonSpinner — inline tri-arc spinner (used in submit buttons)
   ────────────────────────────────────────────────────────────────── */
export function ButtonSpinner({ size = 14, className = "" }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      data-testid="button-spinner"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.18" strokeWidth="2.5" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

/* ──────────────────────────────────────────────────────────────────
   InlineLoader — pill loader for in-content async sections.
   Glass card + dancing micro bars.
   ────────────────────────────────────────────────────────────────── */
export function InlineLoader({ label = "Loading data…", className = "" }) {
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="inline-loader"
      className={`inline-flex items-center gap-3 px-4 py-2.5 rounded-full bg-white/80 backdrop-blur-sm border border-[#E2E8F0] shadow-[0_4px_14px_-4px_rgba(15,23,42,0.08)] ${className}`}
    >
      <span className="inline-flex items-end gap-[3px] h-4">
        {[0, 1, 2, 3].map((i) => (
          <span
            key={i}
            className="block w-[3px] rounded-full wave-bar"
            style={{
              height: 8 + (i % 2) * 6,
              background: i % 2 ? C.cyan : C.blue,
              animationDelay: `${i * 0.12}s`,
            }}
          />
        ))}
      </span>
      <span className="text-[13px] font-medium text-[#0F172A]">{label}</span>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   DotsLoader — wave of 3 dots (kept name; new motion)
   ────────────────────────────────────────────────────────────────── */
export function DotsLoader({ label, className = "" }) {
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="dots-loader"
      className={`flex flex-col items-center gap-2 ${className}`}
    >
      <div className="flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-2.5 rounded-full dot-bounce"
            style={{
              animationDelay: `${i * 0.16}s`,
              background:
                i === 0 ? C.blue : i === 1 ? C.cyan : "#0EA5E9",
              boxShadow: `0 0 8px ${i === 0 ? "rgba(37,99,235,0.5)" : i === 1 ? "rgba(6,182,212,0.55)" : "rgba(14,165,233,0.5)"}`,
            }}
          />
        ))}
      </div>
      {label && <p className="text-[12.5px] text-[#475569] mt-1">{label}</p>}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   ChatTyping — "OraOne is typing…" indicator
   ────────────────────────────────────────────────────────────────── */
export function ChatTyping({ label = "OraOne is typing…" }) {
  return (
    <div className="flex items-center gap-3" data-testid="chat-typing">
      <span
        className="size-9 rounded-full grid place-items-center flex-shrink-0"
        style={{
          background:
            "radial-gradient(circle at 35% 30%, #93C5FD 0%, #2563EB 70%, #1E40AF 100%)",
          boxShadow: "0 4px 14px -4px rgba(37,99,235,0.55)",
        }}
        aria-hidden="true"
      />
      <div className="px-3.5 py-2.5 rounded-2xl rounded-tl-sm bg-[#F1F5F9] flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 rounded-full bg-[#2563EB] dot-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
      {label && <span className="text-[12px] text-[#64748B]">{label}</span>}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   Skeleton primitives
   ────────────────────────────────────────────────────────────────── */
export function Skeleton({ className = "", style }) {
  return <div className={`skeleton rounded-lg ${className}`} style={style} aria-hidden="true" />;
}

export function CardSkeleton({ rows = 3 }) {
  return (
    <div className="p-5 rounded-2xl border border-[#E2E8F0] bg-white space-y-3" data-testid="card-skeleton">
      <div className="flex items-center gap-3">
        <Skeleton className="size-9 rounded-xl" />
        <Skeleton className="h-3 w-32" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-2.5 w-full" style={{ width: `${80 - i * 12}%` }} />
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }) {
  return (
    <div className="rounded-2xl border border-[#E2E8F0] bg-white overflow-hidden" data-testid="table-skeleton">
      <div className="px-5 py-3 border-b border-[#E2E8F0] bg-[#F8FAFC]">
        <Skeleton className="h-3 w-32" />
      </div>
      <div className="divide-y divide-[#E2E8F0]">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="px-5 py-4 flex items-center gap-4">
            <Skeleton className="size-9 rounded-full" />
            {Array.from({ length: cols - 1 }).map((__, c) => (
              <Skeleton key={c} className="h-2.5 flex-1" style={{ maxWidth: `${120 + c * 30}px` }} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   EmptyStateLoader — card-style loader for data sections
   ────────────────────────────────────────────────────────────────── */
export function EmptyStateLoader({
  label = "Loading your data…",
  sub = "Please wait a moment while we fetch everything for you.",
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="empty-state-loader"
      className="rounded-2xl border border-[#E2E8F0] bg-white p-10 flex flex-col items-center text-center"
    >
      <OraMark size={64} className="animate-pulse" />
      <p className="mt-6 text-lg font-bold text-[#0F172A]">{label}</p>
      <p className="mt-1 text-[13px] text-[#64748B] max-w-sm">{sub}</p>
      <div className="mt-4">
        <DotsLoader />
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   ProgressStages — multi-step progress (Connecting → … → Done)
   ────────────────────────────────────────────────────────────────── */
export function ProgressStages({ stages, current = 0 }) {
  const list = stages || ["Connecting", "Fetching Data", "Processing", "Almost Done"];
  return (
    <div className="rounded-2xl border border-[#E2E8F0] bg-white p-6" data-testid="progress-stages">
      <div className="flex items-center justify-between gap-2">
        {list.map((s, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <React.Fragment key={s}>
              <div className="flex flex-col items-center min-w-[70px]">
                <span
                  className={`size-9 rounded-full grid place-items-center text-[12px] font-bold transition-all ${
                    done
                      ? "bg-[#2563EB] text-white"
                      : active
                      ? "bg-white border-2 border-[#2563EB] text-[#2563EB] ring-4 ring-[#2563EB]/15"
                      : "bg-[#F1F5F9] text-[#94A3B8] border border-[#E2E8F0]"
                  }`}
                >
                  {i + 1}
                </span>
                <p
                  className={`mt-2 text-[11.5px] font-semibold ${
                    done || active ? "text-[#2563EB]" : "text-[#94A3B8]"
                  }`}
                >
                  {s}
                </p>
              </div>
              {i < list.length - 1 && (
                <span
                  className={`flex-1 h-[2px] rounded-full ${
                    i < current ? "bg-[#2563EB]" : "border-t-2 border-dashed border-[#E2E8F0]"
                  }`}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   TopProgressBar — global thin progress bar
   ────────────────────────────────────────────────────────────────── */
export function TopProgressBar({ active = true, label }) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!active) return;
    setProgress(10);
    const id = setInterval(() => {
      setProgress((p) => (p < 85 ? p + (Math.random() * 12 + 3) : p));
    }, 220);
    return () => {
      clearInterval(id);
      setProgress(100);
    };
  }, [active]);

  if (!active) return null;
  return (
    <div
      className="fixed top-0 left-0 right-0 z-[100] pointer-events-none"
      role="progressbar"
      aria-valuenow={progress}
      aria-valuemin={0}
      aria-valuemax={100}
      data-testid="top-progress-bar"
    >
      <div className="h-[3px] w-full bg-[#EFF6FF]">
        <div
          className="h-full transition-all duration-300"
          style={{
            width: `${progress}%`,
            background:
              "linear-gradient(90deg, #2563EB 0%, #06B6D4 55%, #22D3EE 100%)",
            boxShadow: "0 0 10px rgba(37,99,235,0.65)",
          }}
        />
      </div>
      {label && (
        <p className="text-center text-[11px] text-[#64748B] mt-1 font-medium">{label}</p>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
   PageTransition — soft full-screen ripple overlay
   ────────────────────────────────────────────────────────────────── */
export function PageTransition() {
  return (
    <div
      className="fixed inset-0 z-[200] bg-white/85 backdrop-blur-md grid place-items-center"
      data-testid="page-transition"
    >
      <OraMark size={76} className="animate-pulse" />
    </div>
  );
}
