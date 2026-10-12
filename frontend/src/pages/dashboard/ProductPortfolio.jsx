import { ArrowRight, CheckCircle2, Clock3, Eye, Layers3 } from "lucide-react";
import { Link } from "react-router-dom";
import { useSEO } from "@/lib/seo";

const PRODUCTS = [
  {
    id: 1,
    name: "OraOne AI Chat Platform",
    shortName: "AI Chat",
    scope:
      "Website agents, grounded knowledge, conversations, leads, widgets, and analytics.",
    status: "Active product",
    tone: "active",
    icon: "✦",
  },
  {
    id: 2,
    name: "OraOne AI Voice Platform",
    shortName: "AI Voice",
    scope:
      "Voice agents and business communication with the same workspace foundations.",
    status: "Planned",
    tone: "planned",
    icon: "◌",
  },
  {
    id: 3,
    name: "OraOne WhatsApp Platform",
    shortName: "WhatsApp",
    scope:
      "WhatsApp business messaging, automation, and customer conversations.",
    status: "Planned",
    tone: "planned",
    icon: "◍",
  },
  {
    id: 4,
    name: "Omnichannel Communication Hub",
    shortName: "Omnichannel",
    scope:
      "Unified conversations and customer context across communication channels.",
    status: "Planned",
    tone: "planned",
    icon: "◎",
  },
  {
    id: 5,
    name: "Workflow Automation Platform",
    shortName: "Automation",
    scope:
      "Business triggers, actions, orchestration, and repeatable workflows.",
    status: "Planned",
    tone: "planned",
    icon: "↗",
  },
  {
    id: 6,
    name: "AI Studio & Agent Builder",
    shortName: "AI Studio",
    scope: "Tools to build, test, configure, and deploy AI agents.",
    status: "Planned",
    tone: "planned",
    icon: "⌘",
  },
  {
    id: 7,
    name: "Marketplace",
    shortName: "Marketplace",
    scope: "Agents, templates, connectors, and ecosystem extensions.",
    status: "Planned",
    tone: "planned",
    icon: "◇",
  },
  {
    id: 8,
    name: "Mobile Applications",
    shortName: "Mobile",
    scope:
      "Mobile administration and customer communication for teams on the move.",
    status: "Planned",
    tone: "planned",
    icon: "▣",
  },
  {
    id: 9,
    name: "Enterprise Edition",
    shortName: "Enterprise",
    scope:
      "Advanced security, governance, integrations, and deployment capabilities.",
    status: "Planned",
    tone: "planned",
    icon: "◆",
  },
  {
    id: 10,
    name: "OraOne OS",
    shortName: "OraOne OS",
    scope:
      "The long-term vision for a unified AI and business communication operating platform.",
    status: "Long-term vision",
    tone: "vision",
    icon: "◈",
  },
];

function StatusPill({ tone, children }) {
  const styles = {
    active: "border-emerald-200 bg-emerald-50 text-emerald-700",
    planned: "border-slate-200 bg-slate-50 text-slate-600",
    vision: "border-cyan-200 bg-cyan-50 text-cyan-700",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${styles[tone]}`}
    >
      {tone === "active" ? <CheckCircle2 size={13} /> : <Clock3 size={13} />}
      {children}
    </span>
  );
}

function ProductCard({ product }) {
  const active = product.tone === "active";
  return (
    <article
      className={`group flex min-h-[245px] flex-col rounded-2xl border p-5 transition-shadow ${
        active
          ? "border-blue-200 bg-white shadow-[0_16px_40px_-28px_rgba(37,99,235,0.7)]"
          : "border-slate-200/80 bg-white/75 hover:shadow-[0_16px_36px_-28px_rgba(15,23,42,0.35)]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <span
          className={`grid size-11 place-items-center rounded-xl text-lg font-semibold ${
            active
              ? "bg-gradient-to-br from-blue-600 to-cyan-500 text-white"
              : "bg-slate-100 text-slate-500"
          }`}
          aria-hidden="true"
        >
          {product.icon}
        </span>
        <span className="text-xs font-semibold text-slate-400">
          {String(product.id).padStart(2, "0")}
        </span>
      </div>

      <div className="mt-5 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-[17px] font-bold tracking-tight text-slate-900">
            {product.name}
          </h2>
          <StatusPill tone={product.tone}>{product.status}</StatusPill>
        </div>
        <p className="mt-2 max-w-[34rem] text-sm leading-6 text-slate-500">
          {product.scope}
        </p>
      </div>

      {active ? (
        <Link
          to="/app/dashboard"
          className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-blue-600 transition-colors hover:text-blue-800"
        >
          Open active workspace <ArrowRight size={15} />
        </Link>
      ) : (
        <span className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-slate-400">
          <Eye size={15} /> Preview only
        </span>
      )}
    </article>
  );
}

export default function ProductPortfolio() {
  useSEO({
    title: "Product portfolio",
    description:
      "Explore the OraOne product portfolio and current availability.",
  });

  return (
    <div className="pb-12" data-testid="product-portfolio-page">
      <section className="relative overflow-hidden rounded-3xl border border-slate-200 bg-[#0F172A] px-6 py-8 text-white shadow-[0_20px_60px_-36px_rgba(15,23,42,0.7)] sm:px-9 sm:py-10">
        <div className="pointer-events-none absolute -right-24 -top-28 size-72 rounded-full bg-cyan-400/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-36 left-1/3 size-72 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="relative max-w-2xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-semibold text-cyan-100">
            <Layers3 size={14} /> One unified OraOne platform
          </div>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            One workspace. A growing product ecosystem.
          </h1>
          <p className="mt-4 max-w-xl text-sm leading-6 text-slate-300 sm:text-base">
            Product 1 is the active foundation today. The rest of the portfolio
            is shown here so the roadmap stays visible without pretending future
            products are already available.
          </p>
        </div>
      </section>

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {PRODUCTS.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>

      <p className="mt-6 text-center text-xs leading-5 text-slate-400">
        Product numbers identify the OraOne portfolio; they are not a fixed
        release sequence.
      </p>
    </div>
  );
}
