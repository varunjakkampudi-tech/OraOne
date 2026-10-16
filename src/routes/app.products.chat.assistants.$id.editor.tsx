import { createFileRoute } from "@tanstack/react-router";
import { WorkspacePage } from "@/components/oraone/pages";
import { pageHead } from "@/lib/oraone";
export const Route = createFileRoute("/app/products/chat/assistants/$id/editor")({
  head: () =>
    pageHead(
      "Assistant Editor \u00b7 App / Products / Chat / Assistants",
      "/app/products/chat/assistants/$id/editor",
    ),
  component: Page,
});
function Page() {
  return (
    <WorkspacePage title="Assistant Editor" pagePath="/app/products/chat/assistants/$id/editor" />
  );
}
