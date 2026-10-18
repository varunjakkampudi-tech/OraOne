import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);
const AdminLogsPanel = lazy(() =>
  import("@/components/oraone/admin-logs").then((m) => ({ default: m.AdminLogsPanel })),
);

export const Route = createFileRoute("/admin/logs")({
  head: () => pageHead("Logs · Admin", "/admin/logs"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="Logs" pagePath="/admin/logs">
        <Suspense fallback={<RouteLoader />}>
          <AdminLogsPanel />
        </Suspense>
      </AdminPage>
    </Suspense>
  );
}
