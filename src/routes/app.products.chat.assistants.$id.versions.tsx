import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/products/chat/assistants/$id/versions")({
  head: () =>
    pageHead(
      "Versions \u00b7 App / Products / Chat / Assistants",
      "/app/products/chat/assistants/$id/versions",
    ),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Versions" pagePath="/app/products/chat/assistants/$id/versions" />
    </Suspense>
  );
}
