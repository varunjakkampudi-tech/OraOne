import { createFileRoute } from "@tanstack/react-router";
import { WorkspacePage } from "@/components/oraone/pages";
import { pageHead } from "@/lib/oraone";
export const Route = createFileRoute("/app/products/chat/assistants/demo/settings")({
  head: () =>
    pageHead(
      "Assistant Settings \u00b7 App / Products / Chat / Assistants / Demo",
      "/app/products/chat/assistants/demo/settings",
    ),
  component: Page,
});
function Page() {
  return (
    <WorkspacePage
      title="Assistant Settings"
      pagePath="/app/products/chat/assistants/demo/settings"
    />
  );
}
