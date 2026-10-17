import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/")({
  head: () => ({
    meta: [
      { title: "OraOne OS · OraOne" },
      {
        name: "description",
        content: "One place for your OraOne channels, conversations, assistants and integrations.",
      },
      { property: "og:title", content: "OraOne OS · OraOne" },
      {
        property: "og:description",
        content: "One place for your OraOne channels, conversations, assistants and integrations.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio-os"), "StudioOsHub"),
});
