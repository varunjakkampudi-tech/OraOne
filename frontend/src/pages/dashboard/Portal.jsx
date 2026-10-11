import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  LifeBuoy,
  BookOpen,
  Activity,
  Rocket,
  Lightbulb,
  Code2,
  CreditCard,
  Gauge,
  MessageCircle,
  ArrowRight,
  ArrowUpRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PageHeader, Card, Badge, PrimaryButton } from "@/components/dashboard/kit";

const RESOURCE_METRICS = ["agents", "knowledge_bases", "users", "workflows"];

const ACTIONS = [
  {
    key: "support",
    icon: LifeBuoy,
    title: "Get help",
    desc: "Ask OraOne AI or reach our team — answers are grounded in our docs.",
    action: "support",
    accent: "from-[#EFF6FF] to-[#ECFEFF] text-[#0891B2]",
  },
  {
    key: "docs",
    icon: BookOpen,
    title: "Documentation",
    desc: "Guides, tutorials and product reference.",
    to: "/documentation",
    external: true,
    accent: "from-[#EFF6FF] to-[#E0F2FE] text-[#2563EB]",
  },
  {
    key: "getting-started",
    icon: Rocket,
    title: "Getting started",
    desc: "A guided checklist from zero to a live assistant.",
    to: "/app/getting-started",
    accent: "from-[#ECFDF5] to-[#D1FAE5] text-[#16A34A]",
  },
  {
    key: "developers",
    icon: Code2,
    title: "API & developers",
    desc: "Keys, webhooks and an interactive API reference.",
    to: "/app/developers",
    accent: "from-[#EFF6FF] to-[#ECFEFF] text-[#0891B2]",
  },
  {
    key: "status",
    icon: Activity,
    title: "Product status",
    desc: "Live health of every OraOne service.",
    to: "/app/status",
    accent: "from-[#ECFDF5] to-[#D1FAE5] text-[#16A34A]",
  },
  {
    key: "changelog",
    icon: Rocket,
    title: "What's new",
    desc: "The latest releases and improvements.",
    to: "/app/changelog",
    accent: "from-[#FFF7ED] to-[#FFEDD5] text-[#B45309]",
  },
  {
    key: "support-tickets",
    icon: Lightbulb,
    title: "Support tickets",
    desc: "Report a bug, ask for help or request a feature.",
    to: "/app/tickets",
    accent: "from-[#FFF7ED] to-[#FEF3C7] text-[#B45309]",
  },
  {
    key: "billing",
    icon: CreditCard,
    title: "Billing & plan",
    desc: "Manage your subscription and payment method.",
    to: "/app/billing",
    accent: "from-[#EFF6FF] to-[#E0F2FE] text-[#2563EB]",
  },
];

function MetricBar({ m }) {
  const pct = m.unlimited ? 0 : Math.min(100, Number(m.percent || 0));
  const tone = pct >= 90 ? "#DC2626" : pct >= 70 ? "#F59E0B" : "#2563EB";
  return (
    <div>
      <div className="flex items-center justify-between text-[12.5px]">
        <span className="font-medium text-[#475569]">{m.label}</span>
        <span className="font-semibold text-[#0F172A]">
          {m.used}
          {m.unlimited ? "" : ` / ${m.limit}`}
        </span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-[#EEF2F7]">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${m.unlimited ? 6 : pct}%`, background: m.unlimited ? "#CBD5E1" : tone }}
        />
      </div>
    </div>
  );
}

export default function Portal() {
  const { user } = useAuth();
  const [usage, setUsage] = useState(null);
  const firstName = (user?.name || user?.full_name || user?.email || "there").split(/[\s@]/)[0];

  useEffect(() => {
    let active = true;
    api
      .get("/usage")
      .then((r) => active && setUsage(r.data))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const metrics = (usage?.metrics || []).filter((m) => RESOURCE_METRICS.includes(m.metric));

  const openSupport = () => window.dispatchEvent(new CustomEvent("oraone:open-support"));

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <PageHeader
        eyebrow="Customer Portal"
        icon={LifeBuoy}
        title={`Welcome back, ${firstName}`}
        subtitle="Your self-service hub — support, docs, status and account, all in one place."
        actions={
          <PrimaryButton onClick={openSupport} data-testid="portal-get-help">
            <MessageCircle size={16} />
            Get help
          </PrimaryButton>
        }
      />

      {/* Plan & usage snapshot */}
      <Card className="p-5" data-testid="portal-plan">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-[#EFF4FF] to-[#ECFEFF] text-[#2563EB] ring-1 ring-[#DBEAFE]">
              <Gauge size={22} />
            </span>
            <div>
              <p className="text-sm font-bold text-[#0F172A]">Your plan</p>
              <p className="text-xs text-[#64748B]">Resource usage this period</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="indigo">{usage?.plan_name || "—"}</Badge>
            <Link
              to="/app/usage"
              className="inline-flex items-center gap-1 text-[13px] font-semibold text-[#2563EB] hover:text-[#1D4ED8]"
            >
              View usage <ArrowRight size={14} />
            </Link>
          </div>
        </div>
        {metrics.length > 0 && (
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {metrics.map((m) => (
              <MetricBar key={m.metric} m={m} />
            ))}
          </div>
        )}
      </Card>

      {/* Quick actions */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ACTIONS.map((a) => {
          const Icon = a.icon;
          const inner = (
            <>
              <span
                className={`grid size-11 place-items-center rounded-2xl bg-gradient-to-br ring-1 ring-black/5 ${a.accent}`}
              >
                <Icon size={20} />
              </span>
              <div className="mt-3 flex items-center gap-1.5">
                <p className="text-[15px] font-bold text-[#0F172A]">{a.title}</p>
                {a.external ? (
                  <ArrowUpRight size={15} className="text-[#94A3B8]" />
                ) : (
                  <ArrowRight size={15} className="text-[#94A3B8]" />
                )}
              </div>
              <p className="mt-1 text-[13px] leading-snug text-[#64748B]">{a.desc}</p>
            </>
          );
          const cls =
            "group flex flex-col rounded-2xl border border-[#E7EAF1] bg-white p-5 text-left transition hover:border-[#C7D2FE] hover:shadow-sm";
          if (a.action === "support") {
            return (
              <button key={a.key} onClick={openSupport} className={cls} data-testid={`portal-action-${a.key}`}>
                {inner}
              </button>
            );
          }
          if (a.external) {
            return (
              <a key={a.key} href={a.to} className={cls} data-testid={`portal-action-${a.key}`}>
                {inner}
              </a>
            );
          }
          return (
            <Link key={a.key} to={a.to} className={cls} data-testid={`portal-action-${a.key}`}>
              {inner}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
