import { createFileRoute } from "@tanstack/react-router";
import { pageHead } from "@/lib/oraone";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";
const OnboardingPage = lazy(() =>
  import("@/components/oraone/onboarding").then((m) => ({ default: m.OnboardingPage })),
);

export const Route = createFileRoute("/onboarding/ai-chat")({
  head: () => pageHead("AI Chat Setup \u00b7 Onboarding", "/onboarding/ai-chat"),
  component: Page,
});
function Page() {
  return (
    <Suspense fallback={<RouteLoader />}>
      <OnboardingPage title="AI Chat Setup" pagePath="/onboarding/ai-chat" />
    </Suspense>
  );
}
