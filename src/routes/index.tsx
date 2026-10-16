import { createFileRoute } from "@tanstack/react-router";
import { SiteTemplate } from "@/components/site/templates";
import { sitePage } from "@/content/site";
import { pageHead } from "@/lib/oraone";

export const Route = createFileRoute("/")({
  head: () => pageHead("OraOne — Unified AI Business Platform", "/"),
  component: () => <SiteTemplate page={sitePage("/")} />,
});
