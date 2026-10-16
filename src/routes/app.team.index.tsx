import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/team/")({
  head: () => pageHead("Team \u00b7 App", "/app/team"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Team" pagePath="/app/team" />
    </Suspense>
  );
}
