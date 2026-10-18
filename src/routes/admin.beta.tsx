import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);
const AdminBetaPanel = lazy(() =>
  import("@/components/oraone/admin-beta").then((m) => ({ default: m.AdminBetaPanel })),
);

export const Route = createFileRoute("/admin/beta")({
  head: () => pageHead("Beta flags · Admin", "/admin/beta"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="Beta flags" pagePath="/admin/beta">
        <Suspense fallback={<RouteLoader />}>
          <AdminBetaPanel />
        </Suspense>
      </AdminPage>
    </Suspense>
  );
}
