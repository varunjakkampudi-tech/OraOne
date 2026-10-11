import React from "react";
import { Lightbulb, MessageCircleQuestion, AlertTriangle, BookOpen } from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Badge, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { fmtNum } from "@/components/admin/format";

const areaTone = { knowledge: "blue", prompt: "purple", engagement: "indigo", workflow: "amber" };
const sevTone = { high: "red", medium: "amber", low: "slate" };

export default function AdminSelfImprovement() {
  const { t } = useAdminTheme();
  const { data, loading, error, reload } = useAdminData(() => superAdminApi.selfImprovement(), []);

  if (loading) return <div><PageHeader icon={Lightbulb} title="AI Self-Improvement" /><LoadingState /></div>;
  if (error) return <div><PageHeader icon={Lightbulb} title="AI Self-Improvement" /><ErrorState message={error} onRetry={reload} /></div>;

  const grounded = data.answered_messages ? Math.round(data.grounded_messages / data.answered_messages * 100) : 0;
  const maxFaq = Math.max(1, ...data.frequently_asked.map((f) => f.count));

  return (
    <div>
      <PageHeader icon={Lightbulb} title="AI Self-Improvement"
        subtitle="The platform learns from real conversations and proposes improvements" />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Failed responses" value={fmtNum(data.failed_responses)} icon={AlertTriangle}
          tone={data.failed_responses ? "red" : "green"} />
        <StatCard label="Grounded answers" value={`${grounded}%`} icon={BookOpen} tone={grounded >= 70 ? "green" : "amber"} />
        <StatCard label="Missing knowledge" value={fmtNum(data.missing_knowledge_estimate)} icon={BookOpen}
          tone={data.missing_knowledge_estimate ? "amber" : "green"} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div>
          <SectionTitle>Suggested improvements</SectionTitle>
          {data.suggestions.length === 0 ? <EmptyState icon={Lightbulb} title="No suggestions" hint="The platform is performing well." /> : (
            <div className="space-y-2">
              {data.suggestions.map((s, i) => (
                <Glass key={i} className="p-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium" style={{ color: t.ink }}>{s.title}</span>
                    <div className="flex items-center gap-2">
                      <Badge tone={areaTone[s.area] || "slate"}>{s.area}</Badge>
                      <Badge tone={sevTone[s.severity] || "slate"}>{s.severity}</Badge>
                    </div>
                  </div>
                  <p className="mt-1 text-xs" style={{ color: t.sub }}>{s.detail}</p>
                </Glass>
              ))}
            </div>
          )}
        </div>
        <div>
          <SectionTitle right={<MessageCircleQuestion className="h-4 w-4" style={{ color: t.muted }} />}>Frequently asked</SectionTitle>
          {data.frequently_asked.length === 0 ? <EmptyState title="No questions yet" /> : (
            <Glass className="p-4">
              {data.frequently_asked.map((f, i) => (
                <div key={i} className="mb-3 last:mb-0">
                  <div className="mb-1 flex items-center justify-between gap-3 text-sm">
                    <span className="truncate" style={{ color: t.sub }}>{f.question}</span>
                    <span className="shrink-0 font-semibold" style={{ color: t.ink }}>{f.count}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full" style={{ background: t.line }}>
                    <div className="h-full rounded-full" style={{ width: `${(f.count / maxFaq) * 100}%`, background: `linear-gradient(90deg,${t.brand},${t.brand2})` }} />
                  </div>
                </div>
              ))}
            </Glass>
          )}
        </div>
      </div>
    </div>
  );
}
