import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/platform")({
  head: () => pageHead("Unified Platform", "/platform"),
  component: () => <SiteTemplate page={sitePage("/platform")} />,
});
