import { useEffect, useState } from "react";
import { messageOf } from "@/lib/api/client";
import { listProjects } from "@/lib/api/studio";

// Timestamp formatting and the signed-in account's workspace lookup for /studio screens.

export const when = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString() : "—";

/** The first workspace for the signed-in account (created at first sign-in). */
export function useWorkspaceId() {
  const [state, setState] = useState<{ id: string | null; error: string; loaded: boolean }>({
    id: null,
    error: "",
    loaded: false,
  });
  useEffect(() => {
    let cancelled = false;
    listProjects()
      .then(({ items }) => {
        if (!cancelled) setState({ id: items[0]?.id ?? null, error: "", loaded: true });
      })
      .catch((err) => {
        if (!cancelled)
          setState({
            id: null,
            error: messageOf(err, "Couldn't load your workspace."),
            loaded: true,
          });
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return state;
}
