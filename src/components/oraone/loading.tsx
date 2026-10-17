import { useEffect, useState } from "react";
import { useRouterState } from "@tanstack/react-router";

export function NavigationProgress() {
  // Render nothing on the server and first client pass so hydration matches the SSR markup.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const pending = useRouterState({ select: (s) => s.status === "pending" });
  return mounted && pending ? (
    <div className="navigation-progress" role="status" aria-label="Loading page">
      <span />
      <span className="sr-only">Loading page</span>
    </div>
  ) : null;
}

export function ChartSkeleton() {
  return (
    <div className="chart-skeleton" role="status" aria-label="Loading chart">
      <div className="skeleton-line" />
      <div className="skeleton-chart" />
      <span className="sr-only">Loading chart</span>
    </div>
  );
}

export function PageSkeleton() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const form = path.startsWith("/auth") || path.startsWith("/onboarding");
  return (
    <div
      className={`page-skeleton ${form ? "form-skeleton" : ""}`}
      role="status"
      aria-label="Loading page"
      aria-busy="true"
    >
      <div className="skeleton-line skeleton-short" />
      <div className="skeleton-line skeleton-title" />
      <div className="skeleton-line" />
      {form ? (
        <div className="skeleton-fields">
          {[0, 1, 2].map((i) => (
            <div className="skeleton-field" key={i} />
          ))}
        </div>
      ) : (
        <>
          <div className="skeleton-metrics">
            {[0, 1, 2].map((i) => (
              <div className="skeleton-field" key={i} />
            ))}
          </div>
          <div className="skeleton-chart" />
        </>
      )}
      <span className="sr-only">Loading page</span>
    </div>
  );
}
