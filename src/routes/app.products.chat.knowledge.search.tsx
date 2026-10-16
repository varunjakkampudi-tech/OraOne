import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/products/chat/knowledge/search")({
  head: () =>
    pageHead(
      "Knowledge Search \u00b7 App / Products / Chat / Knowledge",
      "/app/products/chat/knowledge/search",
    ),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Knowledge Search" pagePath="/app/products/chat/knowledge/search" />
    </Suspense>
  );
}
