import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/docs/ai-chat")({
  head: () => pageHead("AI Chat Documentation \u00b7 Docs", "/docs/ai-chat"),
  component: () => <SiteTemplate page={sitePage("/docs/ai-chat")} />,
});
