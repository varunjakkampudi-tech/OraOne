import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/about")({
  head: () => pageHead("About Us", "/about"),
  component: () => <SiteTemplate page={sitePage("/about")} />,
});
