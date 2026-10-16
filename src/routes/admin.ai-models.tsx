import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AdminPage = lazy(() =>
  import("@/components/oraone/admin").then((m) => ({ default: m.AdminPage })),
);

export const Route = createFileRoute("/admin/ai-models")({
  head: () => pageHead("AI Providers \u00b7 Admin", "/admin/ai-models"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AdminPage title="AI Providers" pagePath="/admin/ai-models" />
    </Suspense>
  );
}
