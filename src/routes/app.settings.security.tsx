import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/settings/security")({
  head: () => pageHead("Security \u00b7 App / Settings", "/app/settings/security"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Security" pagePath="/app/settings/security" />
    </Suspense>
  );
}
