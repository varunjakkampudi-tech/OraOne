import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Gauge,
  Loader2,
  RefreshCw,
  Users,
  Bot,
  BookOpen,
  Workflow,
  Plug,
  MessageSquare,
  Zap,
  FileText,
  ArrowUpRight,
  Infinity as InfinityIcon,
  TriangleAlert,
} from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import {
  PageHeader,
  Card,
  SectionTitle,
  GhostButton,
  PrimaryButton,
} from "@/components/dashboard/kit";

const METRIC_ICONS = {
  users: Users,
  agents: Bot,
  knowledge_bases: BookOpen,
  workflows: Workflow,
  integrations: Plug,
  ai_messages: MessageSquare,
  workflow_runs: Zap,
  api_calls: Zap,
  documents_processed: FileText,
};

function barStyle(percent, over) {
  if (over || percent >= 90)
    return { className: "bg-[#DC2626]", text: "#B42318" };
  if (percent >= 75) return { className: "bg-[#D97706]", text: "#B45309" };
  return { className: "bg-brand", text: "#2563EB" };
}

function UsageCard({ m }) {
  const Icon = METRIC_ICONS[m.metric] || Gauge;
  const over = !m.unlimited && m.used > m.limit;
  const pct = m.unlimited ? 0 : m.percent;
  const tone = barStyle(pct, over);
  return (
    <Card className="rounded-lg p-4 shadow-none">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-brand-soft text-brand">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-[#0F172A]">{m.label}</p>
            {m.period && (
              <p className="text-xs text-[#94A3B8]">Period {m.period}</p>
            )}
          </div>
        </div>
        {!m.unlimited && (
          <span className="text-sm font-bold" style={{ color: tone.text }}>
            {Math.min(999, Math.round(pct))}%
          </span>
        )}
      </div>

      <div className="mt-4 flex items-baseline gap-1">
        <span className="text-[28px] font-semibold tracking-tight text-ink">
          {m.used.toLocaleString()}
        </span>
        <span className="text-sm text-[#64748B]">
          {m.unlimited ? (
            <span className="inline-flex items-center gap-1">
              / <InfinityIcon className="h-4 w-4" /> unlimited
            </span>
          ) : (
            <>/ {m.limit.toLocaleString()}</>
          )}
        </span>
      </div>

      {m.unlimited ? (
        <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-[#ECFDF3] px-2.5 py-1 text-[11px] font-semibold text-[#067647]">
          <InfinityIcon className="h-3.5 w-3.5" /> Unlimited on your plan
        </div>
      ) : (
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-subtle">
          <div
            style={{ width: `${Math.min(100, pct)}%` }}
            className={`h-full rounded-full ${tone.className}`}
          />
        </div>
      )}
    </Card>
  );
}

function Section({ icon, title, subtitle, metrics }) {
  if (!metrics.length) return null;
  return (
    <div>
      <SectionTitle icon={icon} title={title} subtitle={subtitle} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {metrics.map((m) => (
          <UsageCard key={m.metric} m={m} />
        ))}
      </div>
    </div>
  );
}

export default function Usage() {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/usage");
      setSnapshot(data);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const { resources, metered } = useMemo(() => {
    const metrics = snapshot?.metrics || [];
    return {
      resources: metrics.filter((m) => m.category === "resource"),
      metered: metrics.filter((m) => m.category === "metered"),
    };
  }, [snapshot]);

  const allMetrics = snapshot?.metrics || [];
  const overCount = allMetrics.filter(
    (m) => !m.unlimited && m.used > m.limit,
  ).length;
  const nearCount = allMetrics.filter(
    (m) => !m.unlimited && m.used <= m.limit && m.percent >= 75,
  ).length;
  const healthy = allMetrics.length - overCount - nearCount;

  if (loading) {
    return (
      <div className="grid h-[60vh] place-items-center">
        <Loader2 className="h-6 w-6 animate-spin text-[#2563EB]" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Usage"
        icon={Gauge}
        title="Usage & limits"
        subtitle={
          <>
            Tracking your{" "}
            <span className="font-semibold capitalize text-[#2563EB]">
              {snapshot?.plan_name || snapshot?.plan_code || "current"}
            </span>{" "}
            plan against its quotas.
          </>
        }
        actions={
          <>
            <GhostButton onClick={load} data-testid="usage-refresh">
              <RefreshCw className="h-4 w-4" /> Refresh
            </GhostButton>
            <PrimaryButton as={Link} to="/app/billing">
              Manage plan <ArrowUpRight className="h-4 w-4" />
            </PrimaryButton>
          </>
        }
      />

      {/* Health summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          {
            label: "Within limits",
            value: Math.max(0, healthy),
            tone: "#067647",
          },
          { label: "Approaching limit", value: nearCount, tone: "#B45309" },
          { label: "Over limit", value: overCount, tone: "#B42318" },
        ].map((s) => (
          <Card key={s.label} className="rounded-lg p-4 shadow-none">
            <p
              className="text-[28px] font-semibold tracking-tight"
              style={{ color: s.tone }}
            >
              {s.value}
            </p>
            <p className="mt-0.5 text-[12px] text-[#64748B]">{s.label}</p>
          </Card>
        ))}
      </div>

      {overCount > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-[#FECACA] bg-[#FEF3F2] px-5 py-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-[#B42318]">
            <TriangleAlert className="h-4 w-4" />
            You've exceeded {overCount} plan limit{overCount > 1 ? "s" : ""}.
            Upgrade to keep everything running smoothly.
          </p>
          <PrimaryButton as={Link} to="/app/billing" className="shrink-0">
            Upgrade
          </PrimaryButton>
        </div>
      )}

      <Section
        icon={BookOpen}
        title="Resources"
        subtitle="Things that exist in your workspace right now."
        metrics={resources}
      />
      <Section
        icon={Zap}
        title="Activity"
        subtitle="Metered usage that resets each period."
        metrics={metered}
      />
    </div>
  );
}
