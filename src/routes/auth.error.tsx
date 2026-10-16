import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AuthPage = lazy(() =>
  import("@/components/oraone/auth").then((m) => ({ default: m.AuthPage })),
);

export const Route = createFileRoute("/auth/error")({
  head: () => pageHead("Authentication Error \u00b7 Auth", "/auth/error"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AuthPage title="Authentication Error" pagePath="/auth/error" />
    </Suspense>
  );
}
