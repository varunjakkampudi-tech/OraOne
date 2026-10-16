import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);

export const Route = createFileRoute("/admin/errors")({
  head: () => pageHead("Error Logs \u00b7 Admin", "/admin/errors"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="Error Logs" pagePath="/admin/errors" />
    </Suspense>
  );
}
