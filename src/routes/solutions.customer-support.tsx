import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/solutions/customer-support")({
  head: () => pageHead("Customer Support \u00b7 Solutions", "/solutions/customer-support"),
  component: () => <SiteTemplate page={sitePage("/solutions/customer-support")} />,
});
