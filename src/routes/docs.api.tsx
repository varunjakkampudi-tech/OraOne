import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/docs/api")({
  head: () => pageHead("API Documentation \u00b7 Docs", "/docs/api"),
  component: () => <SiteTemplate page={sitePage("/docs/api")} />,
});
