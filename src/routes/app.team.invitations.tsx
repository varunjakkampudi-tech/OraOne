import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/team/invitations")({
  head: () => pageHead("Invitations \u00b7 App / Team", "/app/team/invitations"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Invitations" pagePath="/app/team/invitations" />
    </Suspense>
  );
}
