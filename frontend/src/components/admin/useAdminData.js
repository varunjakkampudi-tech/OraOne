import { useCallback, useEffect, useRef, useState } from "react";
import { formatApiError } from "@/lib/api";

/**
 * Standard async data hook for admin pages — gives every page first-class
 * loading / empty / error states with a retry.
 */
export function useAdminData(fn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const run = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await fnRef.current();
      setData(result);
    } catch (e) {
      if (e?.response?.status === 403) setError("You don’t have access to this resource.");
      else setError(formatApiError(e?.response?.data?.detail) || "Failed to load. Please retry.");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { run(); }, [run]);

  return { data, loading, error, reload: run, setData };
}
