import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const OnboardingPage = lazy(() =>
  import("@/components/oraone/onboarding").then((m) => ({ default: m.OnboardingPage })),
);

export const Route = createFileRoute("/onboarding/install")({
  head: () => pageHead("Install Chat Widget \u00b7 Onboarding", "/onboarding/install"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <OnboardingPage title="Install Chat Widget" pagePath="/onboarding/install" />
    </Suspense>
  );
}
