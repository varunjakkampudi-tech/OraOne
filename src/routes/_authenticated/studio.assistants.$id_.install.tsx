import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";

const StudioInstall = lazy(() =>
  import("@/components/oraone/studio-install").then((m) => ({ default: m.StudioInstall })),
);

export const Route = createFileRoute("/_authenticated/studio/assistants/$id_/install")({
  head: () => ({
    meta: [
      { title: "Install assistant · OraOne" },
      { name: "description", content: "Add your OraOne assistant to your website." },
      { property: "og:title", content: "Install assistant · OraOne" },
      { property: "og:type", content: "website" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: Page,
});

function Page() {
  const { id } = Route.useParams();
  return (
    <Suspense fallback={<RouteLoader label="Loading install options" />}>
      <StudioInstall assistantId={id} />
    </Suspense>
  );
}
