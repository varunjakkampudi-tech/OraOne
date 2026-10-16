import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/inbox/")({
  head: () => ({
    meta: [
      { title: "Inbox · OraOne" },
      { name: "description", content: "Conversations with your OraOne assistants." },
      { property: "og:title", content: "Inbox · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio-live"), "InboxPage"),
});
