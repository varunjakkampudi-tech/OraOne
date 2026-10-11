import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
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
    return { className: "from-[#F97066] to-[#DC2626]", text: "#B42318" };
  if (percent >= 75)
    return { className: "from-[#FDB022] to-[#D97706]", text: "#B45309" };
  return { className: "from-[#2563EB] to-[#4F46E5]", text: "#2563EB" };
}

function UsageCard({ m }) {
  const Icon = METRIC_ICONS[m.metric] || Gauge;
  const over = !m.unlimited && m.used > m.limit;
  const pct = m.unlimited ? 0 : m.percent;
  const tone = barStyle(pct, over);
  return (
    <Card hover className="p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-[#EFF4FF] to-[#F5F3FF] text-[#2563EB] ring-1 ring-[#E0E7FF]">
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
        <span className="text-2xl font-extrabold tracking-tight text-[#0F172A]">
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
        <div className="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-[#F1F5F9]">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(100, pct)}%` }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className={`h-full rounded-full bg-gradient-to-r ${tone.className}`}
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
  const overCount = allMetrics.filter((m) => !m.unlimited && m.used > m.limit).length;
  const nearCount = allMetrics.filter(
    (m) => !m.unlimited && m.used <= m.limit && m.percent >= 75
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
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
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
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Within limits", value: Math.max(0, healthy), tone: "#067647" },
          { label: "Approaching limit", value: nearCount, tone: "#B45309" },
          { label: "Over limit", value: overCount, tone: "#B42318" },
        ].map((s) => (
          <Card key={s.label} className="p-4">
            <p
              className="text-[24px] font-extrabold tracking-tight"
              style={{ color: s.tone }}
            >
              {s.value}
            </p>
            <p className="mt-0.5 text-[12px] text-[#64748B]">{s.label}</p>
            <div
              className="mt-2 h-1.5 w-10 rounded-full"
              style={{ background: s.tone }}
            />
          </Card>
        ))}
      </div>

      {overCount > 0 && (
        <div className="flex items-center justify-between gap-4 rounded-2xl border border-[#FECACA] bg-[#FEF3F2] px-5 py-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-[#B42318]">
            <TriangleAlert className="h-4 w-4" />
            You've exceeded {overCount} plan limit{overCount > 1 ? "s" : ""}. Upgrade
            to keep everything running smoothly.
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
    </motion.div>
  );
}
