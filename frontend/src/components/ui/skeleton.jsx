import React from "react";

/**
 * Skeleton — small composable shimmer block.
 * Usage: <Skeleton className="h-4 w-32" />
 */
export function Skeleton({ className = "", ...rest }) {
  return (
    <div
      className={`relative overflow-hidden bg-[#E2E8F0]/70 rounded-md ${className}`}
      aria-hidden="true"
      {...rest}
    >
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/60 to-transparent" />
    </div>
  );
}

/** Card skeleton — generic KPI / dashboard card placeholder */
export function CardSkeleton() {
  return (
    <div className="p-5 rounded-2xl bg-white border border-[#E2E8F0]">
      <div className="flex items-start gap-3">
        <Skeleton className="size-11 rounded-2xl" />
        <div className="flex-1 space-y-2.5">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-7 w-20" />
          <Skeleton className="h-3 w-16" />
        </div>
      </div>
    </div>
  );
}

/** Row skeleton — list item placeholder */
export function RowSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl bg-white border border-[#E2E8F0]">
      <Skeleton className="size-10 rounded-full" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-2.5 w-24" />
      </div>
      <Skeleton className="h-6 w-16 rounded-full" />
    </div>
  );
}

export default Skeleton;
