import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const PublicPage = lazy(() =>
  import("@/components/oraone/marketing").then((m) => ({ default: m.PublicPage })),
);
export const Route = createFileRoute("/docs/ai-chat")({
  head: () => pageHead("AI Chat Documentation \u00b7 Docs", "/docs/ai-chat"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <PublicPage title="AI Chat Documentation" pagePath="/docs/ai-chat" />
    </Suspense>
  );
}
