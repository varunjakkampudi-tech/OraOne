import React from "react";
import { Lightbulb, TrendingUp, Users, DollarSign, AlertTriangle, Sparkles } from "lucide-react";
import {
  PageHeader, Glass, GradientText, Badge, LoadingState, ErrorState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtMoney, fmtNum } from "@/components/admin/format";

function Insight({ icon: Icon, tone, title, body }) {
  const { t } = useAdminTheme();
  const map = { green: "#16A34A", blue: t.brand, purple: t.brand2, amber: "#D97706", red: "#DC2626" };
  const c = map[tone] || t.brand;
  return (
    <Glass className="flex items-start gap-3 p-4" hover>
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl" style={{ background: `${c}1A`, color: c }}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <div className="font-semibold" style={{ color: t.ink }}>{title}</div>
        <p className="mt-0.5 text-sm" style={{ color: t.sub }}>{body}</p>
      </div>
    </Glass>
  );
}

export default function AdminInsights() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.overview(), []);

  if (loading) return <div><PageHeader icon={Lightbulb} title="Founder Insights" /><LoadingState /></div>;
  if (error) return <div><PageHeader icon={Lightbulb} title="Founder Insights" /><ErrorState message={error} onRetry={reload} /></div>;

  const cust = data.customers, rev = data.revenue, rel = data.reliability, live = data.live;
  const insights = [];

  insights.push({ icon: Users, tone: "blue", title: `${fmtNum(cust.total)} customers · ${fmtNum(cust.active)} active`,
    body: `${fmtNum(cust.new_signups_7d)} new signups in the last 7 days. ${fmtNum(cust.enterprise)} on enterprise, ${fmtNum(cust.trial)} on trial.` });

  insights.push({ icon: DollarSign, tone: "green", title: `${fmtMoney(rev.mrr, rev.currency)} MRR · ${fmtMoney(rev.arr, rev.currency)} ARR`,
    body: rev.mrr > 0 ? "Recurring revenue is flowing. Watch trial-to-paid conversion to accelerate growth." : "No recurring revenue yet — focus on converting trials into paid plans." });

  insights.push({ icon: TrendingUp, tone: "purple", title: `${fmtNum(live.llm_tokens_24h)} LLM tokens in 24h`,
    body: `${fmtNum(live.concurrent_chats)} live chats and ${fmtNum(live.concurrent_calls)} live calls right now. ${fmtNum(live.online_users)} users online.` });

  if (rel.error_rate > 2) {
    insights.push({ icon: AlertTriangle, tone: "red", title: `Elevated error rate: ${rel.error_rate}%`,
      body: "Error rate is above the 2% comfort threshold. Investigate failing endpoints in Reliability and Logs." });
  } else {
    insights.push({ icon: Sparkles, tone: "green", title: `Healthy reliability · ${rel.success_rate}% success`,
      body: `${fmtNum(rel.api_requests_24h)} API requests served in the last 24h with ${rel.error_rate}% errors.` });
  }

  return (
    <div>
      <PageHeader icon={Lightbulb} title={<GradientText>Founder Insights</GradientText>}
        subtitle="An executive read on the state of the platform, right now." />
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {insights.map((x, i) => <Insight key={i} {...x} />)}
      </div>
    </div>
  );
}
