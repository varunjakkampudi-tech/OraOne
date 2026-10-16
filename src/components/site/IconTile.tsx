import type { ComponentType } from "react";

type Icon = ComponentType<{ className?: string; "aria-hidden"?: boolean }>;

/** A rounded icon tile used on cards and rows. Decorative: the text next to it carries the meaning. */
export function IconTile({ icon: Icon, tone = "brand" }: { icon: Icon; tone?: "brand" | "muted" }) {
  const style =
    tone === "brand"
      ? "bg-primary/10 text-primary ring-1 ring-inset ring-primary/15"
      : "bg-muted text-muted-foreground ring-1 ring-inset ring-border";
  return (
    <span className={`grid size-11 shrink-0 place-items-center rounded-xl ${style}`}>
      <Icon className="size-5" aria-hidden={true} />
    </span>
  );
}
