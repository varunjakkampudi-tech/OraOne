import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/analytics/")({
  head: () => ({
    meta: [
      { title: "Analytics · OraOne" },
      {
        name: "description",
        content: "Assistant, conversation and lead activity for your OraOne workspace.",
      },
      { property: "og:title", content: "Analytics · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio-more"), "AnalyticsPage"),
});
