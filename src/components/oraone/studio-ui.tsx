import { Loader2 } from "lucide-react";

// Shared pieces of the live /studio screens: notices and loading lines.

export function Notice({
  kind = "info",
  children,
}: {
  kind?: "info" | "error";
  children: React.ReactNode;
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

export function Loading({ label }: { label: string }) {
  return (
    <p className="flex items-center gap-2 text-muted-foreground">
      <Loader2 className="size-4 animate-spin" />
      {label}
    </p>
  );
}
