import React, { useCallback, useEffect, useMemo, useState } from "react";
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
  ArrowUpRight,
} from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { usePermissions } from "@/hooks/usePermissions";
import {
  PageHeader,
  Card,
  Segmented,
  Badge,
  GhostButton,
  PrimaryButton,
  EmptyState,
} from "@/components/dashboard/kit";

const POPULAR_CODE = "business";

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
  const { can } = usePermissions();
  const canManage = can("billing.manage");
  const [plans, setPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cycle, setCycle] = useState("monthly");
  const [busyCode, setBusyCode] = useState(null);

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
      if (s.value.data?.billing_cycle) setCycle(s.value.data.billing_cycle);
    }
    if (i.status === "fulfilled") setInvoices(i.value.data.items || []);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const currentCode = subscription?.plan?.code;

  const upgrade = async (plan) => {
    if (plan.code === "enterprise" && !plan.price_cents) {
      window.location.href = "mailto:sales@oraone.in?subject=Enterprise%20plan";
      return;
    }
    setBusyCode(plan.code);
    try {
      const { data } = await api.post("/billing/checkout", {
        plan_code: plan.code,
        billing_cycle: cycle,
      });
      if (data.mode === "stripe" && data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }
      toast.success(data.message || `Switched to ${plan.name}.`);
      await load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyCode(null);
    }
  };

  const openPortal = async () => {
    try {
      const { data } = await api.post("/billing/portal");
      if (data.portal_url && data.mode === "stripe") {
        window.location.href = data.portal_url;
      } else {
        toast.info(data.message || "Customer portal not available in mock mode.");
      }
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const cancel = async () => {
    if (!window.confirm("Cancel your subscription at the end of the period?")) return;
    try {
      const { data } = await api.post("/billing/cancel");
      setSubscription(data);
      toast.success("Subscription will cancel at period end.");
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const renewal = subscription?.current_period_end
    ? new Date(subscription.current_period_end).toLocaleDateString()
    : "—";

  const statusTone =
    { active: "green", trialing: "blue", past_due: "amber", canceled: "red" }[subscription?.status] || "slate";
  const CurrentIcon = PLAN_ICONS[currentCode] || Sparkles;

  return (
    <div className="space-y-8" data-testid="billing-dashboard">
      {/* Header */}
      <PageHeader
        eyebrow="Billing"
        icon={CreditCard}
        title="Plans & subscription"
        subtitle="Choose the plan that fits your team and manage invoices — upgrades apply instantly."
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
                {subscription?.status && <Badge tone={statusTone}>{subscription.status}</Badge>}
              </div>
              <p className="mt-0.5 text-sm text-[#64748B]">
                {subscription?.cancel_at_period_end
                  ? `Cancels on ${renewal}`
                  : `Renews on ${renewal} · billed ${subscription?.billing_cycle || "monthly"}`}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <GhostButton onClick={openPortal}>Manage billing</GhostButton>
            {canManage &&
              currentCode &&
              currentCode !== "free" &&
              !subscription?.cancel_at_period_end && (
                <button
                  onClick={cancel}
                  className="rounded-xl border border-[#FECACA] px-4 py-2 text-sm font-semibold text-[#B91C1C] transition-colors hover:bg-[#FEF2F2]"
                >
                  Cancel
                </button>
              )}
          </div>
        </div>
      </Card>

      {/* Billing cycle toggle */}
      <div className="flex items-center justify-center">
        <Segmented
          value={cycle}
          onChange={setCycle}
          options={[
            { value: "monthly", label: "Monthly" },
            { value: "yearly", label: "Yearly", badge: "2 months free" },
          ]}
        />
      </div>

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
            const isPopular = plan.code === POPULAR_CODE && !isCurrent;
            const price = cycle === "yearly" ? plan.price_cents_yearly : plan.price_cents;
            const isEnterprise = plan.code === "enterprise" && !plan.price_cents;
            return (
              <motion.div
                key={plan.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className={`relative flex flex-col rounded-2xl border bg-white p-6 transition-all ${
                  isCurrent
                    ? "border-[#2563EB] ring-1 ring-[#2563EB] shadow-[0_16px_36px_-16px_rgba(37,99,235,0.30)]"
                    : isPopular
                    ? "border-[#C7D2FE] shadow-[0_16px_36px_-16px_rgba(79,70,229,0.25)]"
                    : "border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04)] hover:-translate-y-0.5 hover:shadow-[0_16px_36px_-16px_rgba(16,24,40,0.18)]"
                }`}
              >
                {isPopular && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-gradient-to-r from-[#2563EB] to-[#4F46E5] px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-white shadow-[0_8px_20px_-8px_rgba(37,99,235,0.7)]">
                    Most popular
                  </span>
                )}
                <div className="flex items-center justify-between">
                  <div
                    className={`grid size-10 place-items-center rounded-xl ${
                      isCurrent || isPopular
                        ? "bg-gradient-to-br from-[#2563EB] to-[#4F46E5] text-white"
                        : "bg-[#EFF4FF] text-[#2563EB]"
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  {isCurrent && <Badge tone="indigo">Current</Badge>}
                </div>
                <h3 className="mt-4 text-lg font-bold text-[#0F172A]">{plan.name}</h3>
                <p className="min-h-[40px] text-sm text-[#64748B]">{plan.description}</p>
                <div className="mt-3">
                  {isEnterprise ? (
                    <span className="text-2xl font-extrabold text-[#0F172A]">Custom</span>
                  ) : (
                    <>
                      <span className="text-[32px] font-extrabold tracking-tight text-[#0F172A]">
                        {money(price, plan.currency)}
                      </span>
                      {price > 0 && (
                        <span className="text-sm text-[#64748B]">
                          /{cycle === "yearly" ? "yr" : "mo"}
                        </span>
                      )}
                    </>
                  )}
                </div>
                <ul className="mt-4 flex-1 space-y-2">
                  {(plan.features || []).map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-[#334155]">
                      <span className="mt-0.5 grid size-4 shrink-0 place-items-center rounded-full bg-[#ECFDF3]">
                        <Check className="h-3 w-3 text-[#067647]" />
                      </span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <button
                  disabled={isCurrent || busyCode === plan.code || !canManage}
                  onClick={() => upgrade(plan)}
                  className={`mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold transition ${
                    isCurrent || !canManage
                      ? "cursor-default bg-[#F1F5F9] text-[#94A3B8]"
                      : isPopular || isCurrent
                      ? "bg-gradient-to-r from-[#2563EB] to-[#4F46E5] text-white shadow-[0_8px_20px_-8px_rgba(37,99,235,0.6)] hover:opacity-95"
                      : "bg-[#0F172A] text-white hover:bg-[#1E293B]"
                  }`}
                >
                  {busyCode === plan.code && <Loader2 className="h-4 w-4 animate-spin" />}
                  {isCurrent
                    ? "Current plan"
                    : isEnterprise
                    ? "Contact sales"
                    : "Choose plan"}
                  {!isCurrent && !isEnterprise && busyCode !== plan.code && (
                    <ArrowUpRight className="h-4 w-4" />
                  )}
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
          <span className="text-sm text-[#64748B]">{invoices.length} total</span>
        </div>
        {invoices.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={Receipt}
              title="No invoices yet"
              hint="Upgrade to a paid plan and your billing history will appear here."
            />
          </div>
        ) : (
          <div className="divide-y divide-[#EEF2F7]">
            {invoices.map((inv) => (
              <div key={inv.id} className="flex items-center justify-between p-4 transition-colors hover:bg-[#FAFBFE]">
                <div className="flex items-center gap-3">
                  <span className="grid size-9 place-items-center rounded-xl bg-[#F5F7FB] text-[#64748B]">
                    <Receipt className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="font-semibold text-[#0F172A]">{inv.number}</p>
                    <p className="text-sm text-[#64748B]">
                      {inv.description} · {new Date(inv.created_at).toLocaleDateString()}
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
                      className="rounded-lg p-2 text-[#64748B] transition-colors hover:bg-[#F1F5F9] hover:text-[#2563EB]"
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
