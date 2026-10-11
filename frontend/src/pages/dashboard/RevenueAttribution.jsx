import React, { useEffect, useState } from "react";
import { TrendingUp, Loader2, RefreshCw, AlertTriangle, DollarSign, Target, Users } from "lucide-react";
import {
  PageHeader,
  Card,
  Badge,
  SectionTitle,
  StatCard,
  Segmented,
  PrimaryButton,
  GhostButton,
  EmptyState,
  INK,
  SUB,
  LINE,
  BRAND,
} from "@/components/dashboard/kit";
import { workspaceIntelApi } from "@/lib/workspaceIntel";
import { formatApiError } from "@/lib/api";

const money = (n) =>
  `$${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

function Bar({ label, value, max, sub }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium capitalize" style={{ color: INK }}>{label}</span>
        <span style={{ color: SUB }}>{money(value)}{sub ? ` · ${sub}` : ""}</span>
      </div>
      <div className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full" style={{ background: LINE }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: BRAND, transition: "width .6s ease" }} />
      </div>
    </div>
  );
}

export default function RevenueAttribution() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [days, setDays] = useState(90);

  const load = (d = days) => {
    setLoading(true);
    setError("");
    workspaceIntelApi
      .revenueAttribution(d)
      .then(setData)
      .catch((e) => setError(formatApiError(e?.response?.data?.detail) || "Failed to load attribution"))
      .finally(() => setLoading(false));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(days); }, [days]);

  const tot = data?.totals || {};
  const chMax = Math.max(1, ...((data?.by_channel || []).map((c) => c.revenue || 0)));
  const agMax = Math.max(1, ...((data?.by_agent || []).map((a) => a.revenue || 0)));

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        icon={TrendingUp}
        eyebrow="Workspace Intelligence"
        title="Revenue Attribution"
        subtitle="See which channels and agents drive pipeline and revenue."
        actions={
          <div className="flex items-center gap-2">
            <Segmented
              value={String(days)}
              onChange={(v) => setDays(Number(v))}
              options={[{ value: "30", label: "30d" }, { value: "90", label: "90d" }, { value: "180", label: "180d" }]}
            />
            <GhostButton onClick={() => load()} disabled={loading}>
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
            </GhostButton>
          </div>
        }
      />

      {loading ? (
        <div className="grid place-items-center py-24" style={{ color: SUB }}>
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : error ? (
        <Card className="p-8">
          <EmptyState icon={AlertTriangle} title="Couldn't load attribution" hint={error}
            action={<PrimaryButton onClick={() => load()}>Try again</PrimaryButton>} />
        </Card>
      ) : !data ? null : (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={DollarSign} label="Revenue won" value={money(tot.revenue)} tone="#16A34A" bg="#F0FDF4" />
            <StatCard icon={Target} label="Open pipeline" value={money(tot.pipeline)} />
            <StatCard icon={Users} label="Leads" value={tot.leads ?? 0} sub={`${tot.won ?? 0} won`} />
            <StatCard icon={TrendingUp} label="Win rate" value={`${tot.win_rate ?? 0}%`} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="p-6">
              <SectionTitle title="By channel" subtitle="Revenue contribution per source" />
              <div className="mt-4 space-y-4">
                {(data.by_channel || []).length === 0 ? (
                  <EmptyState icon={TrendingUp} title="No attributed revenue yet"
                    hint="Once leads convert, channel attribution appears here." />
                ) : (
                  data.by_channel.map((c) => (
                    <Bar key={c.channel} label={c.channel} value={c.revenue} max={chMax} sub={`${c.leads} leads`} />
                  ))
                )}
              </div>
            </Card>

            <Card className="p-6">
              <SectionTitle title="Top agents" subtitle="Revenue by agent" />
              <div className="mt-4 space-y-4">
                {(data.by_agent || []).length === 0 ? (
                  <EmptyState icon={Users} title="No agent attribution yet"
                    hint="Revenue from agent-sourced leads appears here." />
                ) : (
                  data.by_agent.map((a) => (
                    <Bar key={a.agent_id} label={a.name} value={a.revenue} max={agMax} sub={`${a.won}/${a.leads} won`} />
                  ))
                )}
              </div>
            </Card>
          </div>

          <p className="text-center text-xs" style={{ color: SUB }}>
            Pipeline is estimated from lead score × {money(tot.avg_deal_value)} average deal value. Won revenue counts converted leads.
          </p>
        </div>
      )}
    </div>
  );
}
