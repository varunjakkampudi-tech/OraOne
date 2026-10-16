import { createFileRoute, lazyRouteComponent } from "@tanstack/react-router";

export const Route = createFileRoute("/_authenticated/studio/integrations/")({
  head: () => ({
    meta: [
      { title: "Integrations · OraOne" },
      { name: "description", content: "Connect the tools that feed your OraOne assistants." },
      { property: "og:title", content: "Integrations · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: lazyRouteComponent(
    () => import("@/components/oraone/studio-integrations"),
    "IntegrationsPage",
  ),
});
