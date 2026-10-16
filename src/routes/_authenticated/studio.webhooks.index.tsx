import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/webhooks/")({
  head: () => ({
    meta: [
      { title: "Webhooks · OraOne" },
      { name: "description", content: "Send OraOne workspace events to your own systems." },
      { property: "og:title", content: "Webhooks · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(
    () => import("@/components/oraone/studio-integrations"),
    "WebhooksPage",
  ),
});
