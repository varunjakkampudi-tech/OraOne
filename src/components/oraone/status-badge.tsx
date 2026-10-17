import type { Status } from "@/content/site/types";
import { STATUS_LABEL } from "@/content/site/navigation";

// One badge for product and feature availability on signed-in surfaces. Labels come from
// STATUS_LABEL so the app and the public site describe the same thing the same way.
const TONE: Record<Status, string> = {
  available: "is-demo",
  active: "is-active",
  beta: "is-active",
  "in-development": "is-planned",
  planned: "is-planned",
  vision: "is-planned",
};

export function StatusBadge({ status, className = "" }: { status: Status; className?: string }) {
  return (
    <span className={`status-pill ${TONE[status]} ${className}`.trim()}>
      {STATUS_LABEL[status]}
    </span>
  );
}
