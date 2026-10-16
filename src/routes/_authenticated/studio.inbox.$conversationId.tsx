import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";

const InboxThreadPage = lazy(() =>
  import("@/components/oraone/studio-live").then((m) => ({ default: m.InboxThreadPage })),
);

export const Route = createFileRoute("/_authenticated/studio/inbox/$conversationId")({
  head: () => ({
    meta: [
      { title: "Conversation · OraOne" },
      { name: "description", content: "A conversation with an OraOne assistant." },
      { property: "og:title", content: "Conversation · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: Page,
});

function Page() {
  const { conversationId } = Route.useParams();
  return (
    <Suspense fallback={<RouteLoader label="Loading conversation" />}>
      <InboxThreadPage conversationId={conversationId} />
    </Suspense>
  );
}
