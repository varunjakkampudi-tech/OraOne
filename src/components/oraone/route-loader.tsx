import { Loader2 } from "lucide-react";

// Shown while a route's code or data is loading. Announced to assistive tech
// once, so screen readers hear "Loading" without repeated noise.
export function RouteLoader({ label = "Loading" }: { label?: string }) {
  return (
    <div
      role="status"
      className="flex min-h-[40vh] items-center justify-center gap-3 text-muted-foreground"
    >
      <Loader2 className="size-5 animate-spin" aria-hidden="true" />
      <span className="text-base">{label}…</span>
    </div>
  );
}
