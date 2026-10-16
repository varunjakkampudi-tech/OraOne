import { createFileRoute, redirect } from "@tanstack/react-router";
import { recoveryPath } from "@/lib/oraone";
export const Route = createFileRoute("/reset-password")({
  beforeLoad: () => {
    throw redirect({ to: recoveryPath, search: true, replace: true });
  },
});
