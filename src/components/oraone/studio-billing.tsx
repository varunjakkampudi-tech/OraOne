import { useEffect, useState } from "react";
import {
  getSubscription,
  getUsage,
  listPlans,
  type Plan,
  type Subscription,
  type UsageSnapshot,
} from "@/lib/api/billing";
import { messageOf } from "@/lib/api/client";
import { Loading, Notice } from "./studio-ui";
import { when } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";

// Live billing screen under /studio. Plans, subscription and usage are read
// from the API, each with its own error. Changing a plan is not connected yet.

const money = (cents: number, currency: string) =>
  new Intl.NumberFormat(undefined, { style: "currency", currency: currency.toUpperCase() }).format(
    cents / 100,
  );

type Section<T> = { data: T | null; error: string };

function useSection<T>(load: () => Promise<T>, failure: string): Section<T> {
  const [state, setState] = useState<Section<T>>({ data: null, error: "" });
  useEffect(() => {
    let cancelled = false;
    load()
      .then((data) => {
        if (!cancelled) setState({ data, error: "" });
      })
      .catch((err) => {
        if (!cancelled) setState({ data: null, error: messageOf(err, failure) });
      });
    return () => {
      cancelled = true;
    };
    // The loaders are module-level functions, so the effect runs once per mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return state;
}

export function BillingPage() {
  const subscription = useSection<Subscription>(
    getSubscription,
    "Couldn't load your subscription.",
  );
  const usage = useSection<UsageSnapshot>(getUsage, "Couldn't load your usage.");
  const plans = useSection<Plan[]>(async () => (await listPlans()).items, "Couldn't load plans.");

  const current = subscription.data;

  return (
    <StudioFrame>
      <span className="marketing-eyebrow">LIVE · BILLING</span>
      <h1 className="mt-2 text-3xl font-semibold">Billing</h1>
      <p className="mt-2 text-muted-foreground">Your plan, subscription and usage this period.</p>

      <section className="mt-8" aria-labelledby="subscription-heading">
        <h2 id="subscription-heading" className="text-xl font-semibold">
          Subscription
        </h2>
        <div className="mt-3">
          {subscription.error ? (
            <Notice kind="error">{subscription.error}</Notice>
          ) : current ? (
            <dl className="grid gap-3 rounded-lg border border-border bg-card p-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">Plan</dt>
                <dd className="font-medium">{current.plan.name}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Status</dt>
                <dd className="font-medium">{current.status}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Billing cycle</dt>
                <dd className="font-medium">{current.billing_cycle}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Current period ends</dt>
                <dd className="font-medium">{when(current.current_period_end)}</dd>
              </div>
              {current.cancel_at_period_end && (
                <div className="sm:col-span-2 text-destructive">
                  This subscription is set to end at the close of the current period.
                </div>
              )}
            </dl>
          ) : (
            <Loading label="Loading subscription…" />
          )}
        </div>
      </section>

      <section className="mt-10" aria-labelledby="usage-heading">
        <h2 id="usage-heading" className="text-xl font-semibold">
          Usage
        </h2>
        <div className="mt-3">
          {usage.error ? (
            <Notice kind="error">{usage.error}</Notice>
          ) : usage.data ? (
            usage.data.metrics.length === 0 ? (
              <p className="text-muted-foreground">No usage has been recorded yet.</p>
            ) : (
              <ul className="grid gap-3" aria-label="Usage metrics">
                {usage.data.metrics.map((m) => (
                  <li key={m.metric} className="rounded-lg border border-border bg-card p-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
                      <span className="font-medium">{m.label}</span>
                      <span className="text-muted-foreground">
                        {m.used.toLocaleString()}{" "}
                        {m.unlimited ? "· unlimited" : `of ${m.limit.toLocaleString()}`}
                        {m.period ? ` · ${m.period}` : ""}
                      </span>
                    </div>
                    {!m.unlimited && (
                      <div
                        className="mt-2 h-2 overflow-hidden rounded bg-muted"
                        role="progressbar"
                        aria-label={m.label}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={Math.min(100, m.percent)}
                      >
                        <div
                          className="h-full bg-primary"
                          style={{ width: `${Math.min(100, Math.max(0, m.percent))}%` }}
                        />
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )
          ) : (
            <Loading label="Loading usage…" />
          )}
        </div>
      </section>

      <section className="mt-10" aria-labelledby="plans-heading">
        <h2 id="plans-heading" className="text-xl font-semibold">
          Plans
        </h2>
        <div className="mt-3">
          {plans.error ? (
            <Notice kind="error">{plans.error}</Notice>
          ) : plans.data ? (
            plans.data.length === 0 ? (
              <p className="text-muted-foreground">No plans are published yet.</p>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2" aria-label="Plans">
                {plans.data.map((plan) => (
                  <li key={plan.id} className="rounded-lg border border-border bg-card p-4">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold">{plan.name}</h3>
                      {current?.plan_id === plan.id && (
                        <span className="rounded-full border border-border px-2 py-0.5 text-sm">
                          Current
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xl font-semibold">
                      {plan.price_cents === 0
                        ? "Free"
                        : `${money(plan.price_cents, plan.currency)} / month`}
                    </p>
                    {plan.description && (
                      <p className="mt-1 text-sm text-muted-foreground">{plan.description}</p>
                    )}
                  </li>
                ))}
              </ul>
            )
          ) : (
            <Loading label="Loading plans…" />
          )}
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Plan changes and invoices are not available in the studio yet.
        </p>
      </section>
    </StudioFrame>
  );
}
