import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/api-keys/")({
  head: () => ({
    meta: [
      { title: "API keys · OraOne" },
      { name: "description", content: "Create and revoke API keys for your OraOne workspace." },
      { property: "og:title", content: "API keys · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(() => import("@/components/oraone/studio-more"), "ApiKeysPage"),
});
