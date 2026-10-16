import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const OnboardingPage = lazy(() =>
  import("@/components/oraone/onboarding").then((m) => ({ default: m.OnboardingPage })),
);

export const Route = createFileRoute("/onboarding/use-case")({
  head: () => pageHead("Business Use Case \u00b7 Onboarding", "/onboarding/use-case"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <OnboardingPage title="Business Use Case" pagePath="/onboarding/use-case" />
    </Suspense>
  );
}
