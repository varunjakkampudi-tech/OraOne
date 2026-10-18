import { createFileRoute, redirect } from "@tanstack/react-router";

// /auth has no page of its own. Send visitors to sign-in, the one account entry point.
export const Route = createFileRoute("/auth/")({
  beforeLoad: () => {
    throw redirect({ to: "/auth/sign-in", replace: true });
  },
});
