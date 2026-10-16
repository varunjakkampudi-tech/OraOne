import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);

export const Route = createFileRoute("/admin/products")({
  head: () => pageHead("Product Registry \u00b7 Admin", "/admin/products"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="Product Registry" pagePath="/admin/products" />
    </Suspense>
  );
}
