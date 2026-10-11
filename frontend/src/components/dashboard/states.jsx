import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { cx, PrimaryButton, GhostButton } from "./kit";

/* ──────────────────────────────────────────────────────────────────────────
   Shared async states — one template for loading / error / empty so every
   module in OraOne behaves identically.
   ────────────────────────────────────────────────────────────────────────── */

/* Skeleton primitive. */
export function Skeleton({ className = "" }) {
  return <div aria-hidden="true" className={cx("animate-pulse rounded-lg bg-line motion-reduce:animate-none", className)} />;
}

/* Table loading skeleton — mimics rows so layout doesn't jump. */
export function TableSkeleton({ rows = 6, cols = 4 }) {
  return (
    <div role="status" aria-busy="true" aria-label="Loading" className="overflow-hidden rounded-2xl border border-line bg-white">
      <span className="sr-only">Loading…</span>
      <div className="flex items-center gap-4 border-b border-hairline px-4 py-3">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3.5 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex items-center gap-4 border-b border-canvas px-4 py-4 last:border-0">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className={cx("h-4", c === 0 ? "w-40" : "flex-1")} />
          ))}
        </div>
      ))}
    </div>
  );
}

/* Card grid loading skeleton. */
export function CardsSkeleton({ count = 6 }) {
  return (
    <div role="status" aria-busy="true" aria-label="Loading" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <span className="sr-only">Loading…</span>
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-40 rounded-2xl" />
      ))}
    </div>
  );
}

/* Error state with retry. */
export function ErrorState({ title = "Something went wrong", message, onRetry }) {
  return (
    <div role="alert" className="rounded-2xl border border-danger-border bg-[#FFFBFA] p-10 text-center">
      <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-danger-soft text-danger">
        <AlertTriangle size={22} aria-hidden="true" />
      </span>
      <p className="mt-3 text-sm font-semibold text-ink">{title}</p>
      {message && <p className="mt-1 text-[13px] text-sub">{message}</p>}
      {onRetry && (
        <div className="mt-4 flex justify-center">
          <GhostButton onClick={onRetry}>
            <RefreshCw size={15} /> Try again
          </GhostButton>
        </div>
      )}
    </div>
  );
}

/* Empty state — one template: icon, title, explanation, primary + optional secondary CTA. */
export function EmptyState({ icon: Icon, title, hint, action, secondaryAction }) {
  return (
    <div className="rounded-2xl border border-dashed border-stroke bg-white p-9 text-center">
      {Icon && (
        <span className="mx-auto grid size-14 place-items-center rounded-full bg-brand-soft text-brand">
          <Icon size={28} />
        </span>
      )}
      {title && <p className="mt-4 text-[16px] font-bold text-ink">{title}</p>}
      {hint && <p className="mx-auto mt-1.5 max-w-md text-[13.5px] text-body">{hint}</p>}
      {(action || secondaryAction) && (
        <div className="mt-5 flex items-center justify-center gap-2">
          {action}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}

export { PrimaryButton, GhostButton };
