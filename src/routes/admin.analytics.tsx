import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);
const AdminAnalyticsPanel = lazy(() =>
  import("@/components/oraone/admin-analytics").then((m) => ({ default: m.AdminAnalyticsPanel })),
);

export const Route = createFileRoute("/admin/analytics")({
  head: () => pageHead("Analytics · Admin", "/admin/analytics"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="Analytics" pagePath="/admin/analytics">
        <Suspense fallback={<RouteLoader />}>
          <AdminAnalyticsPanel />
        </Suspense>
      </AdminPage>
    </Suspense>
  );
}
