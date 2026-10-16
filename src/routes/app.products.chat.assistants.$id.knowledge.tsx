import { createFileRoute } from "@tanstack/react-router";
import { WorkspacePage } from "@/components/oraone/pages";
import { pageHead } from "@/lib/oraone";
export const Route = createFileRoute("/app/products/chat/assistants/$id/knowledge")({
  head: () =>
    pageHead(
      "Assistant Knowledge \u00b7 App / Products / Chat / Assistants",
      "/app/products/chat/assistants/$id/knowledge",
    ),
  component: Page,
});
function Page() {
  return (
    <WorkspacePage
      title="Assistant Knowledge"
      pagePath="/app/products/chat/assistants/$id/knowledge"
    />
  );
}
