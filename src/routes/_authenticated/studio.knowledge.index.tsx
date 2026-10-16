import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/knowledge/")({
  head: () => ({
    meta: [
      { title: "Knowledge · OraOne" },
      { name: "description", content: "Documents and search for your OraOne assistants." },
      { property: "og:title", content: "Knowledge · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(
    () => import("@/components/oraone/studio-knowledge"),
    "KnowledgePage",
  ),
});
