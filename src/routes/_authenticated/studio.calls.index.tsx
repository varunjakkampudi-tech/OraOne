import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/calls/")({
  head: () => ({
    meta: [
      { title: "Calls · OraOne" },
      { name: "description", content: "Call campaigns for your imported leads." },
      { property: "og:title", content: "Calls · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio-calls"), "CallsPage"),
});
