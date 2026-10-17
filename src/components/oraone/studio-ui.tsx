import type { ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

// Shared pieces of the /studio screens. Tailwind utilities and src/components/ui only.

export function Notice({
  kind = "info",
  children,
}: {
  kind?: "info" | "error";
  children: ReactNode;
}) {
  return (
    <p
      role={kind === "error" ? "alert" : "status"}
      className={`rounded-lg border px-4 py-3 text-sm ${kind === "error" ? "border-destructive text-destructive" : "border-border bg-muted"}`}
    >
      {children}
    </p>
  );
}

/** Error with a plain-language retry. Used when a live query fails. */
export function ErrorNotice({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: (() => void) | undefined;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive px-4 py-3 text-sm text-destructive">
      <span role="alert">{message}</span>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <p className="flex items-center gap-2 text-muted-foreground">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      {label}
    </p>
  );
}

/** Rows shaped like the list they stand in for, so the layout does not jump when data arrives. */
export function ListSkeleton({ rows = 3, label }: { rows?: number; label: string }) {
  return (
    <div role="status" aria-label={label} className="grid gap-3">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-16 w-full rounded-xl" />
      ))}
    </div>
  );
}

/** "Live" appears only when a real query returned data. Callers pass `live` from that result. */
export function LiveBadge({ live }: { live: boolean }) {
  if (!live) return null;
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-0.5 text-xs font-medium text-accent-foreground">
      <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
      Live
    </span>
  );
}

export function PageHeader({
  title,
  description,
  live = false,
  action,
}: {
  title: string;
  description: string;
  live?: boolean;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
          <LiveBadge live={live} />
        </div>
        <p className="mt-2 max-w-2xl text-muted-foreground">{description}</p>
      </div>
      {action && <div className="w-full sm:w-auto">{action}</div>}
    </div>
  );
}

/** Empty state: what is missing, why, and one next action. */
export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="grid justify-items-start gap-2 rounded-xl border border-dashed border-border p-6">
      <p className="font-medium">{title}</p>
      {children && <p className="text-sm text-muted-foreground">{children}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
