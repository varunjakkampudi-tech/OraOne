import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/solutions/small-business")({
  head: () => pageHead("Small Business \u00b7 Solutions", "/solutions/small-business"),
  component: () => <SiteTemplate page={sitePage("/solutions/small-business")} />,
});
