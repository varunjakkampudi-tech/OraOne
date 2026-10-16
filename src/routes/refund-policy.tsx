import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const PublicPage = lazy(() =>
  import("@/components/oraone/marketing").then((m) => ({ default: m.PublicPage })),
);
export const Route = createFileRoute("/refund-policy")({
  head: () => pageHead("Refund Policy, if applicable", "/refund-policy"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <PublicPage title="Refund Policy, if applicable" pagePath="/refund-policy" />
    </Suspense>
  );
}
