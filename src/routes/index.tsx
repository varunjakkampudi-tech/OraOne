import { createFileRoute } from "@tanstack/react-router";
import { MarketingHome } from "@/components/oraone/marketing";
import { pageHead } from "@/lib/oraone";
export const Route = createFileRoute("/")({
  head: () => pageHead("OraOne — Unified AI Business Platform", "/"),
  component: Index,
});
function Index() {
  return <MarketingHome />;
}
