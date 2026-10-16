import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AuthPage = lazy(() =>
  import("@/components/oraone/auth").then((m) => ({ default: m.AuthPage })),
);

export const Route = createFileRoute("/auth/mfa")({
  head: () => pageHead("MFA Challenge \u00b7 Auth", "/auth/mfa"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AuthPage title="MFA Challenge" pagePath="/auth/mfa" />
    </Suspense>
  );
}
