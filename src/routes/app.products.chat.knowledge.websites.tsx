import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/products/chat/knowledge/websites")({
  head: () =>
    pageHead(
      "Websites \u00b7 App / Products / Chat / Knowledge",
      "/app/products/chat/knowledge/websites",
    ),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Websites" pagePath="/app/products/chat/knowledge/websites" />
    </Suspense>
  );
}
