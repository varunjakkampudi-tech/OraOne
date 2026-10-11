import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * usePermissions — Phase 12 Module 4 RBAC.
 *
 * Fetches the caller's effective permissions from `/rbac/me` and exposes a
 * `can(permission)` helper so components can gate UI affordances. Mirrors the
 * backend permission matrix in `app/core/permissions.py`.
 */
export function usePermissions() {
  const [role, setRole] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const { data } = await api.get("/rbac/me");
        if (!active) return;
        setRole(data.role);
        setPermissions(data.permissions || []);
      } catch {
        if (active) setPermissions([]);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const can = useCallback(
    (permission) => permissions.includes(permission),
    [permissions]
  );

  return { role, permissions, can, loading };
}
