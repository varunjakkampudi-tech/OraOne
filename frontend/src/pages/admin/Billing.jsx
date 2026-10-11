import React from "react";
import { CreditCard, Repeat, DollarSign, TrendingUp, Repeat as RepeatIcon, Percent } from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Badge, LoadingState, ErrorState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtMoney, fmtNum } from "@/components/admin/format";

function Bar({ label, value, max, tone }) {
  const { t } = useAdminTheme();
  const pct = max ? Math.round((value / max) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span style={{ color: t.sub }}>{label}</span>
        <span className="font-semibold" style={{ color: t.ink }}>{fmtNum(value)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full" style={{ background: t.line }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: `linear-gradient(90deg,${t.brand},${t.brand2})` }} />
      </div>
    </div>
  );
}

export default function AdminBilling({ variant = "billing" }) {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.billing(), []);
  const isSubs = variant === "subscriptions";

  const maxStatus = Math.max(1, ...((data?.by_status || []).map((s) => s.count)));
  const maxPlan = Math.max(1, ...((data?.by_plan || []).map((p) => p.count)));

  return (
    <div>
      <PageHeader icon={isSubs ? Repeat : CreditCard} title={isSubs ? "Subscriptions" : "Billing"}
        subtitle={isSubs ? "Subscription health across all customers." : "Platform revenue, plans and churn."} />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <StatCard label="MRR" value={fmtMoney(data.mrr)} icon={DollarSign} tone="green" />
            <StatCard label="ARR" value={fmtMoney(data.arr)} icon={TrendingUp} tone="green" />
            <StatCard label="Active subs" value={fmtNum(data.active_subscriptions)} icon={RepeatIcon} tone="blue" />
            <StatCard label="Total subs" value={fmtNum(data.total_subscriptions)} icon={RepeatIcon} tone="indigo" />
            <StatCard label="Churn" value={`${data.churn_rate}%`} icon={Percent} tone={data.churn_rate > 5 ? "red" : "amber"} />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
            <Glass className="p-5">
              <SectionTitle>Subscriptions by status</SectionTitle>
              {(data.by_status || []).length === 0 ? <p className="text-sm" style={{ color: t.muted }}>No subscriptions yet.</p> : (
                <div className="space-y-3">
                  {data.by_status.map((s) => <Bar key={s.status} label={s.status} value={s.count} max={maxStatus} />)}
                </div>
              )}
            </Glass>
            <Glass className="p-5">
              <SectionTitle>Customers by plan</SectionTitle>
              {(data.by_plan || []).length === 0 ? <p className="text-sm" style={{ color: t.muted }}>No plan data yet.</p> : (
                <div className="space-y-3">
                  {data.by_plan.map((p) => <Bar key={p.plan} label={p.plan} value={p.count} max={maxPlan} />)}
                </div>
              )}
            </Glass>
          </div>
        </>
      )}
    </div>
  );
}
