import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/account/")({
  head: () => ({
    meta: [
      { title: "Account · OraOne" },
      { name: "description", content: "Your OraOne account profile." },
      { property: "og:title", content: "Account · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio-more"), "AccountPage"),
});
