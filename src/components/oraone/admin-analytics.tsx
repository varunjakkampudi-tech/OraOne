import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { ApiError, messageOf } from "@/lib/api/client";
import {
  getAdminAnalyticsOverview,
  type DailyPoint,
  type PlatformAnalytics,
} from "@/lib/api/admin-analytics";
import { channelRows, formatCount, seriesMax, seriesTotal } from "@/lib/admin-analytics";
import { useFeatureFlag } from "@/lib/feature-flags";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; data: PlatformAnalytics }
  | { kind: "signin"; message: string }
  | { kind: "error"; message: string };

const CHART_WIDTH = 300;
const CHART_HEIGHT = 80;

/** A 30-day bar chart as inline SVG. Each bar has a title, so values are readable by hover and by screen readers. */
export function InlineBars({ label, points }: { label: string; points: DailyPoint[] }) {
  const max = seriesMax(points);
  const slot = points.length ? CHART_WIDTH / points.length : CHART_WIDTH;
  const total = seriesTotal(points);
  return (
    <figure className="m-0">
      <svg
        role="img"
        aria-label={`${label}: ${formatCount(total)} over ${points.length} days`}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        className="h-24 w-full text-primary"
      >
        {points.map((point, index) => {
          const height = (point.count / max) * (CHART_HEIGHT - 2);
          return (
            <rect
              key={point.date}
              x={index * slot + 1}
              y={CHART_HEIGHT - height}
              width={Math.max(slot - 2, 1)}
              height={height}
              fill="currentColor"
            >
              <title>{`${point.date}: ${formatCount(point.count)}`}</title>
            </rect>
          );
        })}
      </svg>
      <figcaption className="mt-1 flex justify-between text-xs text-muted-foreground">
        <span>{points[0]?.date ?? ""}</span>
        <span>
          {label}: {formatCount(total)} in total
        </span>
        <span>{points[points.length - 1]?.date ?? ""}</span>
      </figcaption>
    </figure>
  );
}

function KpiTable({ data }: { data: PlatformAnalytics }) {
  const rows: [string, number][] = [
    ["Organizations", data.totals.organizations],
    ["Active users (last 30 days, by sign-in)", data.totals.active_users_30d],
    ["Conversations (30 days)", data.totals.conversations_30d],
    ["Messages (30 days)", data.totals.messages_30d],
    ["Leads (30 days)", data.totals.leads_30d],
    ["Calls placed (30 days)", data.totals.calls_placed_30d],
    ["Workflows run (30 days)", data.totals.workflows_run_30d],
  ];
  return (
    <table className="w-full text-sm">
      <caption className="mb-2 text-left font-semibold">Totals</caption>
      <thead className="sr-only">
        <tr>
          <th scope="col">Measure</th>
          <th scope="col">Value</th>
        </tr>
      </thead>
      <tbody className="divide-y">
        {rows.map(([label, value]) => (
          <tr key={label}>
            <th scope="row" className="py-2 pr-4 text-left font-normal">
              {label}
            </th>
            <td className="py-2 text-right tabular-nums">{formatCount(value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ChannelTable({ mix }: { mix: Record<string, number> }) {
  const rows = channelRows(mix);
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">No conversations in the last 30 days.</p>;
  }
  return (
    <table className="w-full text-sm">
      <caption className="mb-2 text-left font-semibold">
        Channel mix (conversations, 30 days)
      </caption>
      <thead>
        <tr className="text-left text-xs text-muted-foreground">
          <th scope="col" className="py-1 pr-3 font-medium">
            Channel
          </th>
          <th scope="col" className="py-1 pr-3 text-right font-medium">
            Count
          </th>
          <th scope="col" className="py-1 font-medium">
            Share
          </th>
        </tr>
      </thead>
      <tbody className="divide-y">
        {rows.map((row) => (
          <tr key={row.channel}>
            <th scope="row" className="py-2 pr-3 text-left font-normal">
              {row.label}
            </th>
            <td className="py-2 pr-3 text-right tabular-nums">{formatCount(row.count)}</td>
            <td className="py-2">
              <div className="flex items-center gap-2">
                <svg
                  role="img"
                  aria-label={`${row.label} share ${row.share}%`}
                  viewBox="0 0 100 8"
                  preserveAspectRatio="none"
                  className="h-2 w-full max-w-48 text-primary"
                >
                  <rect x="0" y="0" width={row.share} height="8" fill="currentColor" />
                </svg>
                <span className="w-12 text-right tabular-nums text-xs">{row.share}%</span>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ErrorTable({ data }: { data: PlatformAnalytics }) {
  return (
    <table className="w-full text-sm">
      <caption className="mb-2 text-left font-semibold">Errors (API requests, 30 days)</caption>
      <tbody className="divide-y">
        <tr>
          <th scope="row" className="py-2 pr-4 text-left font-normal">
            Requests logged
          </th>
          <td className="py-2 text-right tabular-nums">{formatCount(data.errors.requests_30d)}</td>
        </tr>
        <tr>
          <th scope="row" className="py-2 pr-4 text-left font-normal">
            Server errors (5xx)
          </th>
          <td className="py-2 text-right tabular-nums">
            {formatCount(data.errors.server_errors_30d)}
          </td>
        </tr>
        <tr>
          <th scope="row" className="py-2 pr-4 text-left font-normal">
            Error rate
          </th>
          <td className="py-2 text-right tabular-nums">{data.errors.error_rate_pct}%</td>
        </tr>
      </tbody>
    </table>
  );
}

export function AdminAnalyticsPanel() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const betaOn = useFeatureFlag("admin_analytics_console");

  useEffect(() => {
    let active = true;
    getAdminAnalyticsOverview()
      .then((data) => {
        if (active) setState({ kind: "ready", data });
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          setState({
            kind: "signin",
            message:
              error.status === 403
                ? "This account is not a platform administrator. Only super-admins and admins can view platform analytics."
                : "Sign in with a platform administrator account to view platform analytics.",
          });
        } else {
          setState({
            kind: "error",
            message: messageOf(error, "Analytics could not be loaded. Try again shortly."),
          });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section
      aria-labelledby="admin-analytics-heading"
      className="admin-section"
      aria-busy={state.kind === "loading"}
    >
      <h2 id="admin-analytics-heading">
        Platform analytics{" "}
        {betaOn ? <span className="ml-2 rounded bg-muted px-1.5 py-0.5 text-xs">Beta</span> : null}
      </h2>
      <p className="admin-table-summary">
        Aggregate counts for the last 30 days. This view loads no message text, names, emails or
        phone numbers, and no customer content.
      </p>

      {state.kind === "loading" && (
        <p className="text-sm text-muted-foreground">Loading analytics…</p>
      )}

      {state.kind === "signin" && (
        <div className="admin-access-notice">
          <ShieldCheck />
          <div>
            <strong>Platform administrator access required</strong>
            <p>{state.message}</p>
          </div>
        </div>
      )}

      {state.kind === "error" && (
        <p role="alert" className="text-sm text-destructive">
          {state.message}
        </p>
      )}

      {state.kind === "ready" && (
        <div className="grid gap-8">
          <div className="grid gap-8 lg:grid-cols-2">
            <KpiTable data={state.data} />
            <div className="grid gap-8">
              <ErrorTable data={state.data} />
              <ChannelTable mix={state.data.channel_mix} />
            </div>
          </div>
          <div className="grid gap-6">
            <InlineBars label="Conversations" points={state.data.daily.conversations} />
            <InlineBars label="Messages" points={state.data.daily.messages} />
            <InlineBars label="Server errors" points={state.data.daily.server_errors} />
          </div>
          <p className="text-xs text-muted-foreground">
            Generated {new Date(state.data.generated_at).toLocaleString()}. Active users are counted
            from each user&apos;s last sign-in, not from activity content.
          </p>
        </div>
      )}
    </section>
  );
}
