import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);
const AdminConfigPanel = lazy(() =>
  import("@/components/oraone/admin-config").then((m) => ({ default: m.AdminConfigPanel })),
);

export const Route = createFileRoute("/admin/config")({
  head: () => pageHead("Configuration · Admin", "/admin/config"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="Configuration" pagePath="/admin/config">
        <Suspense fallback={<RouteLoader />}>
          <AdminConfigPanel />
        </Suspense>
      </AdminPage>
    </Suspense>
  );
}
