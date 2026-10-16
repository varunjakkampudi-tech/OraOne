import { createFileRoute } from "@tanstack/react-router";
import { WorkspacePage } from "@/components/oraone/pages";
import { pageHead } from "@/lib/oraone";
export const Route = createFileRoute("/app/products/chat/assistants/demo/instructions")({
  head: () =>
    pageHead(
      "AI Instructions \u00b7 App / Products / Chat / Assistants / Demo",
      "/app/products/chat/assistants/demo/instructions",
    ),
  component: Page,
});
function Page() {
  return (
    <WorkspacePage
      title="AI Instructions"
      pagePath="/app/products/chat/assistants/demo/instructions"
    />
  );
}
