import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);

export const Route = createFileRoute("/admin/support")({
  head: () => pageHead("Support Cases \u00b7 Admin", "/admin/support"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="Support Cases" pagePath="/admin/support" />
    </Suspense>
  );
}
