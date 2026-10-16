import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/products/ai-chat")({
  head: () => pageHead("AI Chat \u00b7 Products", "/products/ai-chat"),
  component: () => <SiteTemplate page={sitePage("/products/ai-chat")} />,
});
