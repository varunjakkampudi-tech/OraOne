import { createFileRoute, redirect } from "@tanstack/react-router";
// OraOne is passwordless: there is no password to reset.
export const Route = createFileRoute("/auth/reset-password")({
  beforeLoad: () => {
    throw redirect({ to: "/auth/sign-in", replace: true });
  },
});
