import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/demo")({
  head: () => pageHead("Request a Demo", "/demo"),
  component: () => <SiteTemplate page={sitePage("/demo")} />,
});
