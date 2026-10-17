import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/assistants/")({
  head: () => ({
    meta: [
      { title: "Your assistants · OraOne" },
      {
        name: "description",
        content: "Create workspaces and AI assistants in your OraOne account.",
      },
      { property: "og:title", content: "Your assistants · OraOne" },
      {
        property: "og:description",
        content: "Create workspaces and AI assistants in your OraOne account.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio"), "StudioHome"),
});
