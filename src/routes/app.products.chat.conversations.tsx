import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/products/chat/conversations")({
  head: () =>
    pageHead("Chat Conversations \u00b7 App / Products / Chat", "/app/products/chat/conversations"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Chat Conversations" pagePath="/app/products/chat/conversations" />
    </Suspense>
  );
}
