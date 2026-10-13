import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Building2,
  Clock3,
  Layers3,
  MessageCircle,
  MessageSquare,
  MessagesSquare,
  Network,
  Phone,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Store,
  Workflow,
} from "lucide-react";
import { Link, Navigate, useLocation, useParams } from "react-router-dom";
import { useSEO } from "@/lib/seo";
import { PRODUCT_CATALOG } from "@/constants/productCatalog";
import { PageHeader } from "@/components/dashboard/kit";

const PRODUCTS = PRODUCT_CATALOG;

const ICONS = {
  chat: MessageSquare,
  voice: Phone,
  whatsapp: MessageCircle,
  omnichannel: MessagesSquare,
  automation: Workflow,
  "ai-studio": Sparkles,
  marketplace: Store,
  mobile: Smartphone,
  enterprise: Building2,
  "oraone-os": Network,
};

const SCREENS = {
  voice: [
    ["Overview", "", "Voice product overview and availability."],
    ["Voice agents", "agents", "Planned voice-agent directory."],
    ["Create an agent", "agents/new", "Planned voice-agent setup."],
    ["Calls", "calls", "Planned call history and review."],
    ["Campaigns", "campaigns", "Planned voice campaign workspace."],
    ["Phone numbers", "numbers", "Planned number management."],
    ["Analytics", "analytics", "Planned voice reporting."],
    ["Playground", "playground", "Planned voice testing workspace."],
    ["Settings", "settings", "Planned voice product settings."],
  ],
  whatsapp: [
    ["Overview", "", "WhatsApp product overview and availability."],
    ["Business accounts", "accounts", "Planned account connections."],
    ["Agents", "agents", "Planned WhatsApp-agent directory."],
    ["Create an agent", "agents/new", "Planned WhatsApp-agent setup."],
    ["Conversations", "conversations", "Planned messaging inbox."],
    ["Contacts", "contacts", "Planned contact workspace."],
    ["Campaigns", "campaigns", "Planned message campaigns."],
    ["Automation", "automation", "Planned message automation."],
    ["Templates", "templates", "Planned message templates."],
    ["Create a template", "templates/new", "Planned template creation."],
    ["Analytics", "analytics", "Planned WhatsApp reporting."],
    ["Connect a channel", "connect", "Planned channel connection flow."],
    ["Settings", "settings", "Planned WhatsApp product settings."],
  ],
  omnichannel: [
    ["Overview", "", "Omnichannel product overview and availability."],
    ["Conversations", "conversations", "Planned unified inbox."],
    ["Team inbox", "team-inbox", "Planned team assignment workspace."],
    ["Channels", "channels", "Planned connected-channel directory."],
    ["Connect a channel", "channels/connect", "Planned channel setup."],
    ["Assignments", "assignments", "Planned conversation assignments."],
    ["Customers", "customers", "Planned cross-channel customer view."],
    ["Segments", "segments", "Planned customer segments."],
    ["Routing", "routing", "Planned routing rules."],
    ["Service levels", "sla", "Planned response-time policies."],
    ["Analytics", "analytics", "Planned omnichannel reporting."],
    ["Settings", "settings", "Planned omnichannel product settings."],
  ],
  automation: [
    ["Overview", "", "Automation product overview and availability."],
    ["Workflows", "workflows", "Planned workflow directory."],
    ["Create a workflow", "workflows/new", "Planned workflow setup."],
    ["Triggers", "triggers", "Planned workflow triggers."],
    ["Actions", "actions", "Planned workflow actions."],
    ["Templates", "templates", "Planned workflow templates."],
    ["Executions", "executions", "Planned execution history."],
    ["Analytics", "analytics", "Planned workflow reporting."],
    ["Errors", "errors", "Planned workflow error review."],
    ["Settings", "settings", "Planned automation settings."],
  ],
  "ai-studio": [
    ["Overview", "", "AI Studio overview and availability."],
    ["Agents", "agents", "Planned agent workspace."],
    ["Create an agent", "agents/new", "Planned agent setup."],
    ["Builder", "agents/demo/builder", "Planned visual agent builder."],
    ["Models", "models", "Planned model configuration."],
    ["Prompts", "prompts", "Planned prompt library."],
    ["Tools", "tools", "Planned tool configuration."],
    ["Knowledge", "knowledge", "Planned knowledge connections."],
    ["Playground", "playground", "Planned agent testing."],
    ["Evaluations", "evaluations", "Planned evaluation workspace."],
    ["Analytics", "analytics", "Planned agent reporting."],
    ["Traces", "traces", "Planned trace inspection."],
    ["Versions", "versions", "Planned version history."],
    ["Publishing", "publishing", "Planned release controls."],
    ["Settings", "settings", "Planned AI Studio settings."],
  ],
  marketplace: [
    ["Overview", "", "Marketplace overview and availability."],
    ["Explore", "explore", "Planned marketplace discovery."],
    ["Categories", "categories", "Planned marketplace categories."],
    ["Templates", "templates", "Planned template catalog."],
    ["Integrations", "integrations", "Planned integration catalog."],
    ["Installed", "installed", "Planned installed items."],
    ["Publishers", "publishers", "Planned publisher directory."],
    ["Developer tools", "developer", "Planned publisher workspace."],
    ["Submissions", "submissions", "Planned review queue."],
    ["Settings", "settings", "Planned marketplace settings."],
  ],
  mobile: [
    ["Overview", "", "Mobile product overview and availability."],
    ["Features", "features", "Planned mobile feature overview."],
    ["Availability", "availability", "Planned app availability information."],
  ],
  enterprise: [
    ["Overview", "", "Enterprise product overview and availability."],
    ["Access", "access", "Planned enterprise access controls."],
    ["Teams", "teams", "Planned enterprise team management."],
    ["Provisioning", "provisioning", "Planned identity provisioning."],
    ["Single sign-on", "sso", "Planned SSO configuration."],
    ["Security", "security", "Planned enterprise security workspace."],
    ["Governance", "governance", "Planned governance controls."],
    ["Compliance", "compliance", "Planned compliance workspace."],
    ["Audit", "audit", "Planned enterprise audit views."],
    ["Reports", "reports", "Planned enterprise reporting."],
    ["Usage", "usage", "Planned enterprise usage views."],
    ["Support", "support", "Planned enterprise support workspace."],
    ["Settings", "settings", "Planned enterprise settings."],
  ],
  "oraone-os": [
    ["Overview", "", "OraOne OS long-term vision overview."],
    ["Business graph", "business-graph", "Long-term business graph concept."],
    ["Command center", "command-center", "Long-term command-center concept."],
    [
      "Customer lifecycle",
      "customer-lifecycle",
      "Long-term lifecycle concept.",
    ],
    ["Intelligence", "intelligence", "Long-term intelligence concept."],
    ["Orchestration", "orchestration", "Long-term orchestration concept."],
    ["Workflows", "workflows", "Long-term workflow concept."],
    ["Operations", "operations", "Long-term operations concept."],
    ["Governance", "governance", "Long-term governance concept."],
    ["Reports", "reports", "Long-term reporting concept."],
    ["Settings", "settings", "Long-term settings concept."],
  ],
};

const DYNAMIC_SCREENS = {
  voice: [["agents/:id", "Agent details"]],
  whatsapp: [["agents/:id", "Agent details"]],
  omnichannel: [],
  automation: [
    ["executions/:id", "Execution details"],
    ["workflows/:id", "Workflow details"],
    ["workflows/:id/builder", "Workflow builder"],
  ],
  "ai-studio": [["agents/:id", "Agent details"]],
  marketplace: [
    ["integrations/:id", "Integration details"],
    ["items/:id", "Item details"],
    ["publishers/:id", "Publisher details"],
    ["templates/:id", "Template details"],
  ],
  mobile: [],
  enterprise: [],
  "oraone-os": [],
};

function matchesRoute(pattern, actual) {
  const expected = pattern.split("/");
  const received = actual.split("/");
  return (
    expected.length === received.length &&
    expected.every(
      (segment, index) =>
        segment.startsWith(":") || segment === received[index],
    )
  );
}

function screenFor(product, relativePath) {
  const screens = SCREENS[product.slug] || [];
  const exact = screens.find(([label, path]) => path === relativePath);
  if (exact) return { label: exact[0], description: exact[2] };

  const dynamic = (DYNAMIC_SCREENS[product.slug] || []).find(([pattern]) =>
    matchesRoute(pattern, relativePath),
  );
  if (dynamic) {
    return {
      label: dynamic[1],
      description: `A planned ${product.shortName} screen. No live service or record is connected.`,
    };
  }

  return {
    label: relativePath
      ? relativePath
          .split("/")
          .filter(Boolean)
          .slice(-1)[0]
          .replace(/[-_]/g, " ")
          .replace(/^./, (letter) => letter.toUpperCase())
      : "Overview",
    description: `A planned ${product.shortName} screen. No live service or record is connected.`,
  };
}

export function PlannedProductRoute({ defaultProductSlug }) {
  const { productSlug = "" } = useParams();
  const resolvedSlug = productSlug || defaultProductSlug || "";
  const location = useLocation();
  const product = PRODUCTS.find((entry) => entry.slug === resolvedSlug);
  const basePath = defaultProductSlug
    ? "/studio"
    : `/app/products/${product?.slug || resolvedSlug}`;
  const relativePath = location.pathname
    .slice(basePath.length)
    .replace(/^\/+|\/+$/g, "");
  const currentScreen = product
    ? screenFor(product, relativePath)
    : { label: "Product portfolio", description: "Explore OraOne products." };
  const pageScreens = product ? SCREENS[product.slug] || [] : [];
  const isVision = product?.tone === "vision";

  useSEO({
    title: product
      ? `${currentScreen.label} · ${product.name}`
      : "Product portfolio",
    description: product
      ? `${currentScreen.description} ${product.status}.`
      : "Explore the OraOne product portfolio.",
  });

  if (!product || product.slug === "chat") {
    const destination =
      resolvedSlug === "chat" ? "/app/dashboard" : "/app/products";
    return <Navigate to={destination} replace />;
  }

  return (
    <main className="space-y-6" data-testid="planned-product-page">
      <PageHeader
        eyebrow={product.shortName + " · " + product.status}
        title={
          currentScreen.label === "Overview"
            ? product.name
            : currentScreen.label
        }
        subtitle={product.scope}
        actions={
          <Link
            to="/app/products"
            className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            All products <ArrowRight size={16} />
          </Link>
        }
      />

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0 space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-5 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-amber-50 text-amber-700">
                <ShieldCheck size={19} aria-hidden="true" />
              </span>
              <div>
                <h2 className="font-semibold text-slate-900">
                  Design preview — not an active service
                </h2>
                <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
                  These screens document the intended {product.shortName}{" "}
                  experience. Product functionality, live data, and connected
                  actions are not available yet. This preview does not change
                  workspace access or entitlements.
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-5">
              <div>
                <p className="text-sm font-medium text-blue-700">
                  Product {product.id} design
                </p>
                <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
                  Design scope
                </h2>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  {currentScreen.description}
                </p>
              </div>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-600">
                {isVision ? "Long-term design" : "Planned design"}
              </span>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-[minmax(0,1.2fr)_minmax(220px,0.8fr)]">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 sm:p-5">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <Layers3
                    size={16}
                    className="text-blue-700"
                    aria-hidden="true"
                  />
                  Planned scope
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-600">
                  {product.scope}
                </p>
                <p className="mt-4 border-t border-slate-200 pt-3 text-xs leading-5 text-slate-500">
                  This is product direction, not a claim that these capabilities
                  are implemented.
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 p-4 sm:p-5">
                <p className="text-sm font-semibold text-slate-900">
                  Availability
                </p>
                <p className="mt-3 flex items-center gap-2 text-sm text-amber-800">
                  <Clock3 size={15} aria-hidden="true" /> {product.status}
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  There is no connected service, live workspace data, or release
                  date to display.
                </p>
                <Link
                  to="/app/dashboard"
                  className="mt-4 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-blue-700 hover:text-blue-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
                >
                  Open Product 1 workspace{" "}
                  <ArrowUpRight size={15} aria-hidden="true" />
                </Link>
              </div>
            </div>
          </div>
        </div>

        <aside className="min-w-0 rounded-lg border border-slate-200 bg-white p-4 sm:p-5">
          <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
            <BookOpen size={16} className="text-blue-700" aria-hidden="true" />
            <h2 className="text-sm font-semibold text-slate-900">
              Designed screens
            </h2>
          </div>
          <nav
            aria-label={`${product.shortName} designed screens`}
            className="mt-3 grid gap-1"
          >
            {pageScreens.map(([label, path]) => {
              const to = path ? `${basePath}/${path}` : basePath;
              const selected = relativePath === path;
              return (
                <Link
                  key={path || "overview"}
                  to={to}
                  aria-current={selected ? "page" : undefined}
                  className={`flex min-h-11 items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${
                    selected
                      ? "bg-blue-50 font-semibold text-blue-800"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <span className="min-w-0 truncate">{label}</span>
                  <ArrowRight
                    size={14}
                    className="shrink-0 opacity-60"
                    aria-hidden="true"
                  />
                </Link>
              );
            })}
          </nav>
          <p className="mt-4 border-t border-slate-100 pt-3 text-xs leading-5 text-slate-500">
            Product numbers identify the portfolio; they do not define a release
            order.
          </p>
        </aside>
      </section>
    </main>
  );
}

function LinkNavigate({ to }) {
  return <Navigate to={to} replace />;
}

export function MarketingProductRoute() {
  const { productSlug = "" } = useParams();
  const aliases = { "ai-chat": "chat", "ai-voice": "voice" };
  const slug = aliases[productSlug] || productSlug;
  const product = PRODUCTS.find((entry) => entry.slug === slug);
  const ProductIcon = ICONS[slug] || Layers3;

  useSEO({
    title: product ? product.name : "OraOne products",
    description: product?.scope || "Explore the OraOne product portfolio.",
  });

  if (!product) return <LinkNavigate to="/products" />;

  const active = product.tone === "active";
  return (
    <div
      className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8"
      data-testid="marketing-product-page"
    >
      <section className="grid gap-8 overflow-hidden rounded-lg border border-slate-200 bg-white lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="p-6 sm:p-9 lg:p-12">
          <Link
            to="/products"
            className="text-sm font-semibold text-blue-700 hover:text-blue-900"
          >
            OraOne products
          </Link>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <span className="grid size-12 place-items-center rounded-lg bg-blue-50 text-blue-700">
              <ProductIcon size={22} aria-hidden="true" />
            </span>
            <span
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${active ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-slate-200 bg-slate-50 text-slate-700"}`}
            >
              {product.status}
            </span>
          </div>
          <h1 className="mt-6 max-w-3xl text-3xl font-bold tracking-tight text-slate-950 sm:text-5xl">
            {product.name}
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
            {product.scope}
          </p>
          {active ? (
            <Link
              to="/signup"
              className="mt-8 inline-flex min-h-11 items-center gap-2 rounded-xl bg-blue-700 px-5 py-3 text-sm font-semibold text-white hover:bg-blue-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
            >
              Create an account <ArrowRight size={16} aria-hidden="true" />
            </Link>
          ) : (
            <p className="mt-8 max-w-xl rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950">
              This product is not available yet. The page describes its planned
              scope; no release date or signup service has been announced.
            </p>
          )}
        </div>
        <aside className="flex flex-col justify-between border-t border-slate-200 bg-slate-50 p-6 sm:p-8 lg:border-l lg:border-t-0">
          <div>
            <p className="text-xs font-semibold text-slate-500">
              ORAONE PORTFOLIO
            </p>
            <p className="mt-2 text-3xl font-bold tabular-nums text-slate-900">
              {String(product.id).padStart(2, "0")}
            </p>
            <p className="mt-4 text-sm leading-6 text-slate-600">
              Product numbers identify the portfolio and are not a fixed release
              sequence.
            </p>
          </div>
          <Link
            to="/products"
            className="mt-8 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-blue-700 hover:text-blue-900"
          >
            Explore the portfolio <ArrowRight size={15} aria-hidden="true" />
          </Link>
        </aside>
      </section>
    </div>
  );
}
