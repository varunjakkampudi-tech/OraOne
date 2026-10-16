import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/docs/integrations")({
  head: () => pageHead("Integration guidance · Documentation", "/docs/integrations"),
  component: () => <SiteTemplate page={sitePage("/docs/integrations")} />,
});
