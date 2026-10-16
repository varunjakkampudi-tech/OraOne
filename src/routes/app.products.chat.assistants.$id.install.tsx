import { createFileRoute } from "@tanstack/react-router";
import { WorkspacePage } from "@/components/oraone/pages";
import { pageHead } from "@/lib/oraone";
export const Route = createFileRoute("/app/products/chat/assistants/$id/install")({
  head: () =>
    pageHead(
      "Installation \u00b7 App / Products / Chat / Assistants",
      "/app/products/chat/assistants/$id/install",
    ),
  component: Page,
});
function Page() {
  return (
    <WorkspacePage title="Installation" pagePath="/app/products/chat/assistants/$id/install" />
  );
}
