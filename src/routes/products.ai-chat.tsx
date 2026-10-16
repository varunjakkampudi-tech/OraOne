import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const PublicPage = lazy(() =>
  import("@/components/oraone/marketing").then((m) => ({ default: m.PublicPage })),
);
export const Route = createFileRoute("/products/ai-chat")({
  head: () => pageHead("AI Chat \u00b7 Products", "/products/ai-chat"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <PublicPage title="AI Chat" pagePath="/products/ai-chat" />
    </Suspense>
  );
}
