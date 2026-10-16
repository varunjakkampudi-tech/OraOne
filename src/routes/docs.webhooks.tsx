import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const PublicPage = lazy(() =>
  import("@/components/oraone/marketing").then((m) => ({ default: m.PublicPage })),
);
export const Route = createFileRoute("/docs/webhooks")({
  head: () => pageHead("Webhook Documentation \u00b7 Docs", "/docs/webhooks"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <PublicPage title="Webhook Documentation" pagePath="/docs/webhooks" />
    </Suspense>
  );
}
