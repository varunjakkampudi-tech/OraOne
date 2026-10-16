import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";

const StudioAssistant = lazy(() =>
  import("@/components/oraone/studio").then((m) => ({ default: m.StudioAssistant })),
);

export const Route = createFileRoute("/_authenticated/studio/assistants/$id")({
  head: () => ({
    meta: [
      { title: "Assistant · OraOne" },
      { name: "description", content: "Configure your OraOne assistant and test live answers." },
      { property: "og:title", content: "Assistant · OraOne" },
      {
        property: "og:description",
        content: "Configure your OraOne assistant and test live answers.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: Page,
});

function Page() {
  const { id } = Route.useParams();
  return (
    <Suspense fallback={<RouteLoader label="Loading assistant" />}>
      <StudioAssistant id={id} />
    </Suspense>
  );
}
