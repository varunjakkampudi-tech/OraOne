import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/docs/webhooks")({
  head: () => pageHead("Webhook Documentation \u00b7 Docs", "/docs/webhooks"),
  component: () => <SiteTemplate page={sitePage("/docs/webhooks")} />,
});
