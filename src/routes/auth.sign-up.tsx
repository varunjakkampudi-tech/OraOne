import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const AuthPage = lazy(() =>
  import("@/components/oraone/auth").then((m) => ({ default: m.AuthPage })),
);

export const Route = createFileRoute("/auth/sign-up")({
  head: () => pageHead("Sign Up \u00b7 Auth", "/auth/sign-up"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <AuthPage title="Sign Up" pagePath="/auth/sign-up" />
    </Suspense>
  );
}
