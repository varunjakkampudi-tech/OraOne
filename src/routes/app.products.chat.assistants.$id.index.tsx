import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/products/chat/assistants/$id/")({
  head: () =>
    pageHead(
      "Assistant Details \u00b7 App / Products / Chat / Assistants",
      "/app/products/chat/assistants/$id",
    ),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Assistant Details" pagePath="/app/products/chat/assistants/$id" />
    </Suspense>
  );
}
