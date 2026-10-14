import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  CreditCard,
  Check,
  Loader2,
  Sparkles,
  Crown,
  Rocket,
  Building2,
  RefreshCw,
  Download,
  Receipt,
  Gauge,
} from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";
import {
  PageHeader,
  Card,
  Badge,
  GhostButton,
  EmptyState,
} from "@/components/dashboard/kit";

const PLAN_ICONS = {
  free: Sparkles,
  starter: Rocket,
  business: Building2,
  enterprise: Crown,
};

function money(cents, currency = "usd") {
  if (!cents) return "Free";
  const v = (cents / 100).toLocaleString(undefined, {
    style: "currency",
    currency: currency.toUpperCase(),
    minimumFractionDigits: 0,
  });
  return v;
}

export default function Billing() {
  const [plans, setPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const [p, s, i] = await Promise.allSettled([
      api.get("/billing/plans"),
      api.get("/billing/subscription"),
      api.get("/billing/invoices", { params: { limit: 50 } }),
    ]);
    if (p.status === "fulfilled") setPlans(p.value.data.items || []);
    if (s.status === "fulfilled") {
      setSubscription(s.value.data);
    }
    if (i.status === "fulfilled") setInvoices(i.value.data.items || []);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const currentCode = subscription?.plan?.code;

  const renewal = subscription?.current_period_end
    ? new Date(subscription.current_period_end).toLocaleDateString()
    : "—";

  const statusTone =
    { active: "green", trialing: "blue", past_due: "amber", canceled: "red" }[
      subscription?.status
    ] || "slate";
  const CurrentIcon = PLAN_ICONS[currentCode] || Sparkles;

  return (
    <div className="space-y-8" data-testid="billing-dashboard">
      {/* Header */}
      <PageHeader
        eyebrow="Billing"
        icon={CreditCard}
        title="Plans & subscription"
        subtitle="OraOne is free for every user. This page shows your access tier and real usage accounting."
        actions={
          <>
            <GhostButton as={Link} to="/app/usage">
              <Gauge className="h-4 w-4" /> View usage
            </GhostButton>
            <GhostButton onClick={load}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </GhostButton>
          </>
        }
      />

      {/* Current plan summary */}
      <Card className="relative overflow-hidden p-6">
        <div className="pointer-events-none absolute -right-16 -top-16 size-56 rounded-full bg-gradient-to-br from-[#EFF4FF] to-[#F5F3FF] blur-2xl" />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="grid size-12 place-items-center rounded-2xl bg-gradient-to-br from-[#2563EB] to-[#4F46E5] text-white shadow-[0_8px_20px_-8px_rgba(37,99,235,0.6)]">
              <CurrentIcon className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-[#0F172A]">
                  {subscription?.plan?.name || "—"}
                </span>
                {subscription?.status && (
                  <Badge tone={statusTone}>{subscription.status}</Badge>
                )}
              </div>
              <p className="mt-0.5 text-sm text-[#5B6B82]">
                {subscription?.cancel_at_period_end
                  ? `Cancels on ${renewal}`
                  : `Renews on ${renewal} · billed ${subscription?.billing_cycle || "monthly"}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-[#067647]">
              No payment required
            </span>
          </div>
        </div>
      </Card>

      {/* Plan grid */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-[#2563EB]" />
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {plans.map((plan, i) => {
            const Icon = PLAN_ICONS[plan.code] || Sparkles;
            const isCurrent = plan.code === currentCode;
            const price = plan.price_cents;
            return (
              <motion.div
                key={plan.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className={`relative flex flex-col rounded-2xl border bg-white p-6 transition-all ${
                  isCurrent
                    ? "border-[#2563EB] ring-1 ring-[#2563EB] shadow-[0_16px_36px_-16px_rgba(37,99,235,0.30)]"
                    : "border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04)] hover:-translate-y-0.5 hover:shadow-[0_16px_36px_-16px_rgba(16,24,40,0.18)]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div
                    className={`grid size-10 place-items-center rounded-xl ${
                      isCurrent
                        ? "bg-gradient-to-br from-[#2563EB] to-[#4F46E5] text-white"
                        : "bg-[#EFF4FF] text-[#2563EB]"
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  {isCurrent && <Badge tone="indigo">Current</Badge>}
                </div>
                <h3 className="mt-4 text-lg font-bold text-[#0F172A]">
                  {plan.name}
                </h3>
                <p className="min-h-[40px] text-sm text-[#5B6B82]">
                  {plan.description}
                </p>
                <div className="mt-3">
                  <span className="text-[32px] font-extrabold tracking-tight text-[#0F172A]">
                    {money(price, plan.currency)}
                  </span>
                </div>
                <ul className="mt-4 flex-1 space-y-2">
                  {(plan.features || []).map((f) => (
                    <li
                      key={f}
                      className="flex items-start gap-2 text-sm text-[#334155]"
                    >
                      <span className="mt-0.5 grid size-4 shrink-0 place-items-center rounded-full bg-[#ECFDF3]">
                        <Check className="h-3 w-3 text-[#067647]" />
                      </span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <button
                  disabled
                  className={`mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold transition ${"cursor-default bg-[#F1F5F9] text-[#5B6B82]"}`}
                >
                  {isCurrent ? "Current free access" : "Unavailable"}
                </button>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Invoices */}
      <Card>
        <div className="flex items-center justify-between border-b border-[#EEF2F7] p-5">
          <div className="flex items-center gap-2.5">
            <span className="grid size-7 place-items-center rounded-lg bg-[#EFF4FF]">
              <Receipt className="h-3.5 w-3.5 text-[#2563EB]" />
            </span>
            <h2 className="font-bold text-[#0F172A]">Invoices</h2>
          </div>
          <span className="text-sm text-[#5B6B82]">
            {invoices.length} total
          </span>
        </div>
        {invoices.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={Receipt}
              title="No invoices yet"
              hint="Paid billing is disabled. Real AI token and usage totals are available on the Usage page."
            />
          </div>
        ) : (
          <div className="divide-y divide-[#EEF2F7]">
            {invoices.map((inv) => (
              <div
                key={inv.id}
                className="flex items-center justify-between p-4 transition-colors hover:bg-[#FAFBFE]"
              >
                <div className="flex items-center gap-3">
                  <span className="grid size-9 place-items-center rounded-xl bg-[#F5F7FB] text-[#5B6B82]">
                    <Receipt className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="font-semibold text-[#0F172A]">{inv.number}</p>
                    <p className="text-sm text-[#5B6B82]">
                      {inv.description} ·{" "}
                      {new Date(inv.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-[#0F172A]">
                    {money(inv.amount_cents, inv.currency)}
                  </span>
                  <Badge tone="green">{inv.status}</Badge>
                  {inv.hosted_url && (
                    <a
                      href={inv.hosted_url}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded-lg p-2 text-[#5B6B82] transition-colors hover:bg-[#F1F5F9] hover:text-[#2563EB]"
                    >
                      <Download className="h-4 w-4" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
