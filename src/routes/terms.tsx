import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/terms")({
  head: () => pageHead("Terms of Service", "/terms"),
  component: () => <SiteTemplate page={sitePage("/terms")} />,
});
