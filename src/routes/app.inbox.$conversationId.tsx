import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const WorkspacePage = lazy(() =>
  import("@/components/oraone/pages").then((m) => ({ default: m.WorkspacePage })),
);
export const Route = createFileRoute("/app/inbox/$conversationId")({
  head: () => pageHead("Conversation Detail \u00b7 App / Inbox", "/app/inbox/$conversationId"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <WorkspacePage title="Conversation Detail" pagePath="/app/inbox/$conversationId" />
    </Suspense>
  );
}
