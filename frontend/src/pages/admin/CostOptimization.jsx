import React from "react";
import { DollarSign, TrendingDown, Cpu, Database, Percent, Wallet, Lightbulb } from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Badge, Table, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtNum } from "@/components/admin/format";

const usd = (n, d = 2) => (n == null ? "—" : `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })}`);
const sevTone = { high: "red", medium: "amber", low: "blue" };

export default function AdminCostOptimization() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.costOptimization(), []);

  if (loading) return <div><PageHeader icon={DollarSign} title="Cost Optimization Engine" /><LoadingState /></div>;
  if (error) return <div><PageHeader icon={DollarSign} title="Cost Optimization Engine" /><ErrorState message={error} onRetry={reload} /></div>;

  const { totals, unit_costs, by_model, by_provider, by_customer, recommendations } = data;

  const modelCols = [
    { key: "model", label: "Model", render: (r) => <span className="font-mono text-xs" style={{ color: t.ink }}>{r.model}</span> },
    { key: "tokens", label: "Tokens", render: (r) => fmtNum(r.tokens) },
    { key: "messages", label: "Messages", render: (r) => fmtNum(r.messages) },
    { key: "price_per_mtok", label: "$/Mtok", render: (r) => usd(r.price_per_mtok, 2) },
    { key: "cost", label: "Est. cost", render: (r) => <span className="font-semibold" style={{ color: t.ink }}>{usd(r.cost, 2)}</span> },
  ];
  const custCols = [
    { key: "name", label: "Customer", render: (r) => <span style={{ color: t.ink }}>{r.name}</span> },
    { key: "tokens", label: "Tokens", render: (r) => fmtNum(r.tokens) },
    { key: "cost", label: "Est. cost", render: (r) => <span className="font-semibold" style={{ color: t.ink }}>{usd(r.cost)}</span> },
  ];

  return (
    <div>
      <PageHeader icon={DollarSign} title="Cost Optimization Engine"
        subtitle={`Estimated spend over the last ${totals ? data.window_days : 30} days · from real token volume`} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Total cost" value={usd(totals.total_cost)} icon={DollarSign} tone="blue" />
        <StatCard label="Monthly burn" value={usd(totals.monthly_burn)} icon={Wallet} tone="amber" />
        <StatCard label="Gross margin" value={totals.gross_margin == null ? "—" : `${totals.gross_margin}%`} icon={Percent}
          tone={totals.gross_margin == null ? "slate" : totals.gross_margin >= 60 ? "green" : "red"} />
        <StatCard label="Profit / customer" value={usd(totals.profit_per_customer)} icon={TrendingDown}
          tone={totals.profit_per_customer >= 0 ? "green" : "red"} />
        <StatCard label="LLM cost" value={usd(totals.llm_cost)} icon={Cpu} tone="purple" />
        <StatCard label="Tokens (window)" value={fmtNum(totals.total_tokens)} icon={Database} tone="slate" />
      </div>

      <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-3">
        {Object.entries({
          "Per conversation": usd(unit_costs.per_conversation, 4),
          "Per customer": usd(unit_costs.per_customer),
          "Per workspace": usd(unit_costs.per_workspace),
          "Per knowledge search": usd(unit_costs.per_knowledge_search, 5),
          "Per integration": usd(unit_costs.per_integration),
        }).map(([k, v]) => (
          <Glass key={k} className="p-3.5">
            <div className="text-xs uppercase tracking-wide" style={{ color: t.sub }}>{k}</div>
            <div className="mt-1 text-lg font-semibold" style={{ color: t.ink }}>{v}</div>
          </Glass>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <SectionTitle>Cost by model</SectionTitle>
          <Table columns={modelCols} rows={by_model} empty={<EmptyState title="No model spend yet" />} />
        </div>
        <div>
          <SectionTitle>Cost by provider</SectionTitle>
          <Glass className="p-4">
            {by_provider.map((p) => (
              <div key={p.provider} className="mb-3 last:mb-0">
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span style={{ color: t.sub }}>{p.provider}</span>
                  <span className="font-semibold" style={{ color: t.ink }}>{usd(p.cost)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full" style={{ background: t.line }}>
                  <div className="h-full rounded-full" style={{ width: `${p.share}%`, background: `linear-gradient(90deg,${t.brand},${t.brand2})` }} />
                </div>
              </div>
            ))}
          </Glass>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div>
          <SectionTitle>Top customers by spend</SectionTitle>
          <Table columns={custCols} rows={by_customer} empty={<EmptyState title="No customer spend yet" />} />
        </div>
        <div>
          <SectionTitle right={<Badge tone="purple"><Lightbulb className="h-3.5 w-3.5" /> AI recommendations</Badge>}>Optimization opportunities</SectionTitle>
          {recommendations.length === 0 ? <EmptyState title="No recommendations" hint="Spend is already optimized." /> : (
            <div className="space-y-2">
              {recommendations.map((r, i) => (
                <Glass key={i} className="p-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium" style={{ color: t.ink }}>{r.title}</span>
                    <div className="flex items-center gap-2">
                      {r.estimated_saving != null && <Badge tone="green">save {usd(r.estimated_saving)}</Badge>}
                      <Badge tone={sevTone[r.severity] || "slate"}>{r.severity}</Badge>
                    </div>
                  </div>
                  <p className="mt-1 text-xs" style={{ color: t.sub }}>{r.detail}</p>
                </Glass>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
