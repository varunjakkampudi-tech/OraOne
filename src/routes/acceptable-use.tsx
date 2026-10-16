import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/acceptable-use")({
  head: () => pageHead("Acceptable Use", "/acceptable-use"),
  component: () => <SiteTemplate page={sitePage("/acceptable-use")} />,
});
