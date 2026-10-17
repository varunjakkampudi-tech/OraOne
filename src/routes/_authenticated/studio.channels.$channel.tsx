import { createFileRoute } from "@tanstack/react-router";
import { lazy, Suspense } from "react";
import { RouteLoader } from "@/components/oraone/route-loader";

const StudioChannelPage = lazy(() =>
  import("@/components/oraone/studio-channel-page").then((m) => ({
    default: m.StudioChannelPage,
  })),
);

export const Route = createFileRoute("/_authenticated/studio/channels/$channel")({
  head: () => ({
    meta: [
      { title: "Channel setup · OraOne" },
      { name: "description", content: "Set up an OraOne channel for your assistant." },
      { property: "og:title", content: "Channel setup · OraOne" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: Page,
});

function Page() {
  const { channel } = Route.useParams();
  return (
    <Suspense fallback={<RouteLoader label="Loading channel setup" />}>
      <StudioChannelPage channel={channel} />
    </Suspense>
  );
}
