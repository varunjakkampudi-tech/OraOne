import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/marketing/")({
  head: () => ({
    meta: [
      { title: "Marketing · OraOne" },
      {
        name: "description",
        content: "Email, SMS and WhatsApp campaigns to your leads, with consent checks.",
      },
      { property: "og:title", content: "Marketing · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(
    () => import("@/components/oraone/studio-marketing"),
    "MarketingPage",
  ),
});
