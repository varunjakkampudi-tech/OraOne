import { useRouter } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

// Shown when a route fails to load (for example a rate limit or a dropped connection).
// It explains the problem in plain words and offers a retry, so the visitor is never stuck.
export function RouteError({ error, reset }: { error: unknown; reset: () => void }) {
  const router = useRouter();
  const detail = error instanceof Error ? error.message : "";
  const rateLimited = /too many requests/i.test(detail);
  return (
    <div
      role="alert"
      className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center gap-4 px-5 py-12 text-center"
    >
      <h1 className="text-2xl font-semibold">
        {rateLimited ? "Please wait a moment" : "This page could not load"}
      </h1>
      <p className="text-muted-foreground">
        {rateLimited
          ? "There have been a lot of requests in the last minute. Try again shortly."
          : "Check your connection and try again. Your data is safe."}
      </p>
      <Button
        onClick={async () => {
          // Re-run the route loaders, then clear the error boundary.
          await router.invalidate();
          reset();
        }}
      >
        Try again
      </Button>
    </div>
  );
}
