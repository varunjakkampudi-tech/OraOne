import React, { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";

// Listens for the API-unavailable / -available window events (fired by the
// axios interceptor) and shows a calm, non-blocking banner while the backend
// is briefly down — e.g. during a deploy. Auto-probes /api/health and hides
// itself the moment the API is back, so users never see raw error noise.
export default function MaintenanceBanner() {
  const [down, setDown] = useState(false);

  useEffect(() => {
    const onDown = () => setDown(true);
    const onUp = () => setDown(false);
    window.addEventListener("oraone:api-unavailable", onDown);
    window.addEventListener("oraone:api-available", onUp);
    return () => {
      window.removeEventListener("oraone:api-unavailable", onDown);
      window.removeEventListener("oraone:api-available", onUp);
    };
  }, []);

  useEffect(() => {
    if (!down) return undefined;
    let cancelled = false;
    const probe = async () => {
      try {
        await api.get("/health", { _retry: true });
        if (!cancelled) setDown(false);
      } catch {
        /* still down — keep probing */
      }
    };
    const t = setInterval(probe, 5000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [down]);

  if (!down) return null;

  return (
    <div className="sticky top-0 z-[60] flex items-center justify-center gap-2 bg-amber-50 px-4 py-2 text-[13px] font-medium text-amber-800 border-b border-amber-200">
      <AlertTriangle size={15} className="shrink-0" />
      <span>OraOne is updating — some actions may pause for a moment. Your live AI agents keep running. Reconnecting…</span>
    </div>
  );
}
