import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AuthPage = lazy(() =>
  import("@/components/oraone/auth").then((m) => ({ default: m.AuthPage })),
);

export const Route = createFileRoute("/auth/callback")({
  head: () => pageHead("Auth Callback \u00b7 Auth", "/auth/callback"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AuthPage title="Auth Callback" pagePath="/auth/callback" />
    </Suspense>
  );
}
