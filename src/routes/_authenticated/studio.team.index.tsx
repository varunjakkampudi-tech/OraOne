import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/team/")({
  head: () => ({
    meta: [
      { title: "Team · OraOne" },
      { name: "description", content: "Members and invitations for your OraOne organization." },
      { property: "og:title", content: "Team · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio-team"), "TeamPage"),
});
