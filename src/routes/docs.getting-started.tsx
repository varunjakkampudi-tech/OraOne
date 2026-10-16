import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/docs/getting-started")({
  head: () => pageHead("Getting Started \u00b7 Docs", "/docs/getting-started"),
  component: () => <SiteTemplate page={sitePage("/docs/getting-started")} />,
});
