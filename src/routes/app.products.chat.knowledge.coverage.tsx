import { createFileRoute } from "@tanstack/react-router";
import { WorkspacePage } from "@/components/oraone/pages";
import { pageHead } from "@/lib/oraone";
export const Route = createFileRoute("/app/products/chat/knowledge/coverage")({
  head: () =>
    pageHead(
      "Knowledge Coverage \u00b7 App / Products / Chat / Knowledge",
      "/app/products/chat/knowledge/coverage",
    ),
  component: Page,
});
function Page() {
  return (
    <WorkspacePage title="Knowledge Coverage" pagePath="/app/products/chat/knowledge/coverage" />
  );
}
