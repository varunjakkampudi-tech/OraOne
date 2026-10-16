import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
import { pageHead } from "@/lib/oraone";

const PublicPage = lazy(() =>
  import("@/components/oraone/marketing").then((m) => ({ default: m.PublicPage })),
);
export const Route = createFileRoute("/terms")({
  head: () => pageHead("Terms of Service", "/terms"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <PublicPage title="Terms of Service" pagePath="/terms" />
    </Suspense>
  );
}
