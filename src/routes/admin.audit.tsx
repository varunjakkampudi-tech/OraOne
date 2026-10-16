import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);

export const Route = createFileRoute("/admin/audit")({
  head: () => pageHead("Audit Logs \u00b7 Admin", "/admin/audit"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="Audit Logs" pagePath="/admin/audit" />
    </Suspense>
  );
}
