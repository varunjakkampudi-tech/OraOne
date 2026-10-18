import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/getting-started/")({
  head: () => ({
    meta: [
      { title: "Getting started · OraOne" },
      {
        name: "description",
        content: "The first steps for your kind of business, and what is done so far.",
      },
      { property: "og:title", content: "Getting started · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(
    () => import("@/components/oraone/studio-getting-started"),
    "GettingStartedPage",
  ),
});
