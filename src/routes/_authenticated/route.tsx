import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { ApiError } from "@/lib/api/client";
import { getMe } from "@/lib/api/auth";

export const Route = createFileRoute("/_authenticated")({
  ssr: false,
  beforeLoad: async ({ location }) => {
    try {
      await getMe();
    } catch (err) {
      // Only a rejected session sends the visitor to sign-in; outages surface as errors.
      if (err instanceof ApiError && err.status === 401) {
        throw redirect({ to: "/auth/sign-in", search: { redirect: location.pathname } as never });
      }
      throw err;
    }
  },
  component: () => <Outlet />,
});
