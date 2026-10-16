import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/solutions/sales")({
  head: () => pageHead("Sales \u00b7 Solutions", "/solutions/sales"),
  component: () => <SiteTemplate page={sitePage("/solutions/sales")} />,
});
