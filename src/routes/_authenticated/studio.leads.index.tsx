import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/leads/")({
  head: () => ({
    meta: [
      { title: "Leads · OraOne" },
      { name: "description", content: "Leads captured by your OraOne assistants." },
      { property: "og:title", content: "Leads · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio-live"), "LeadsPage"),
});
