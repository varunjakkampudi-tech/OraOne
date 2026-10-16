import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/solutions/lead-generation")({
  head: () => pageHead("Lead Generation \u00b7 Solutions", "/solutions/lead-generation"),
  component: () => <SiteTemplate page={sitePage("/solutions/lead-generation")} />,
});
