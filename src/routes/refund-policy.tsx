import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/refund-policy")({
  head: () => pageHead("Refund Policy, if applicable", "/refund-policy"),
  component: () => <SiteTemplate page={sitePage("/refund-policy")} />,
});
