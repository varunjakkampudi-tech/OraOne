import { createFileRoute, redirect } from "@tanstack/react-router";
// OraOne is passwordless: account recovery is simply signing in with a new email code.
export const Route = createFileRoute("/auth/forgot-password")({
  beforeLoad: () => {
    throw redirect({ to: "/auth/sign-in", replace: true });
  },
});
