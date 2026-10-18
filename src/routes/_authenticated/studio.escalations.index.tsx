import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/escalations/")({
  head: () => ({
    meta: [
      { title: "Escalations · OraOne" },
      {
        name: "description",
        content: "Questions your assistant could not answer, with owners and response targets.",
      },
      { property: "og:title", content: "Escalations · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(
    () => import("@/components/oraone/studio-escalations"),
    "EscalationsPage",
  ),
});
