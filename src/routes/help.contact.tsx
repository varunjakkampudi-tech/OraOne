import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/help/contact")({
  head: () => pageHead("Contact Support \u00b7 Help", "/help/contact"),
  component: () => <SiteTemplate page={sitePage("/help/contact")} />,
});
