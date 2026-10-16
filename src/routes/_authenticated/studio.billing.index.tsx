import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/billing/")({
  head: () => ({
    meta: [
      { title: "Billing · OraOne" },
      {
        name: "description",
        content: "Plan, subscription and usage for your OraOne organization.",
      },
      { property: "og:title", content: "Billing · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio-billing"), "BillingPage"),
});
