import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/products/chat/assistants/new")({
  head: () =>
    pageHead(
      "Create Assistant \u00b7 App / Products / Chat / Assistants",
      "/app/products/chat/assistants/new",
    ),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Create Assistant" pagePath="/app/products/chat/assistants/new" />
    </Suspense>
  );
}
