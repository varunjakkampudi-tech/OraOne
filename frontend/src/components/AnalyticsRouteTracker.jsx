import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { trackPageView } from "@/lib/analytics";

/**
 * Fires `page_view` on every route change. Sits inside <BrowserRouter> so
 * it has access to `useLocation`. Does nothing until consent.analytics is true.
 *
 * Uses a ref to guard against React 18 StrictMode double-invocation of effects
 * in development — without it, every nav would emit 2 page_view events.
 */
export default function AnalyticsRouteTracker() {
  const { pathname } = useLocation();
  const lastTracked = useRef(null);

  useEffect(() => {
    if (lastTracked.current === pathname) return;
    lastTracked.current = pathname;
    trackPageView(pathname);
  }, [pathname]);

  return null;
}
