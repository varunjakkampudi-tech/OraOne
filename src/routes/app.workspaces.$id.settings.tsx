import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/workspaces/$id/settings")({
  head: () => pageHead("Settings \u00b7 App / Workspaces", "/app/workspaces/$id/settings"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Settings" pagePath="/app/workspaces/$id/settings" />
    </Suspense>
  );
}
