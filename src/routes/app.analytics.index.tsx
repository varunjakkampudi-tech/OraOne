import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/analytics/")({
  head: () => pageHead("Shared Analytics \u00b7 App", "/app/analytics"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Shared Analytics" pagePath="/app/analytics" />
    </Suspense>
  );
}
