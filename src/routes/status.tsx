import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/status")({
  head: () => pageHead("Platform Status", "/status"),
  component: () => <SiteTemplate page={sitePage("/status")} />,
});
