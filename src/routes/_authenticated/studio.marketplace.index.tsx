import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/marketplace/")({
  head: () => ({
    meta: [
      { title: "Marketplace · OraOne" },
      { name: "description", content: "Install ready-made assistants and workflow blueprints." },
      { property: "og:title", content: "Marketplace · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(
    () => import("@/components/oraone/studio-marketplace"),
    "MarketplacePage",
  ),
});
