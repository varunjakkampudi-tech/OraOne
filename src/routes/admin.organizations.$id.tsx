import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);

export const Route = createFileRoute("/admin/organizations/$id")({
  head: () =>
    pageHead("Organization Details \u00b7 Admin / Organizations", "/admin/organizations/$id"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="Organization Details" pagePath="/admin/organizations/$id" />
    </Suspense>
  );
}
