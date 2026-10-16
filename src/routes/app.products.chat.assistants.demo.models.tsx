import { createFileRoute } from "@tanstack/react-router";
import { WorkspacePage } from "@/components/oraone/pages";
import { pageHead } from "@/lib/oraone";
export const Route = createFileRoute("/app/products/chat/assistants/demo/models")({
  head: () =>
    pageHead(
      "Model Configuration \u00b7 App / Products / Chat / Assistants / Demo",
      "/app/products/chat/assistants/demo/models",
    ),
  component: Page,
});
function Page() {
  return (
    <WorkspacePage
      title="Model Configuration"
      pagePath="/app/products/chat/assistants/demo/models"
    />
  );
}
