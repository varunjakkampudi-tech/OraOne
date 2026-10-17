import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/workflows/")({
  head: () => ({
    meta: [
      { title: "Workflows · OraOne" },
      { name: "description", content: "Workflow automation for your workspace." },
      { property: "og:title", content: "Workflows · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(
    () => import("@/components/oraone/studio-workflows"),
    "WorkflowsPage",
  ),
});
