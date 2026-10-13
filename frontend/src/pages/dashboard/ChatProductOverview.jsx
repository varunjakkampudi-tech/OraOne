import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  BookOpen,
  FileText,
  LayoutGrid,
  MessageSquare,
  Plus,
  RefreshCw,
  Sparkles,
  Waypoints,
} from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import {
  Badge,
  Card,
  EmptyState,
  GhostButton,
  PageHeader,
  PrimaryButton,
  SectionTitle,
  StatCard,
} from "@/components/dashboard/kit";
import { ErrorState, Skeleton } from "@/components/dashboard/states";

const STATUS_TONE = {
  active: "green",
  published: "green",
  draft: "slate",
  paused: "amber",
  processing: "blue",
  pending: "blue",
  failed: "red",
};

const labelize = (value) =>
  String(value || "unknown")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const getItems = (response) => response?.data?.items || [];
const getTotal = (response, fallback = 0) => response?.data?.total ?? fallback;

const sourceFrom = (result) =>
  result.status === "fulfilled"
    ? { status: "fulfilled", response: result.value, error: "" }
    : {
        status: "rejected",
        response: null,
        error:
          formatApiError(
            result.reason?.response?.data?.detail || result.reason?.message,
          ) || "This data source is unavailable.",
      };

function SummarySkeleton() {
  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-3"
      role="status"
      aria-busy="true"
    >
      <span className="sr-only">Loading Product 1 summary…</span>
      {Array.from({ length: 3 }).map((_, index) => (
        <Skeleton key={index} className="h-36 rounded-2xl" />
      ))}
    </div>
  );
}

function ResourceList({
  title,
  subtitle,
  icon: Icon,
  items,
  source,
  onRetry,
  emptyTitle,
  emptyHint,
  emptyAction,
}) {
  return (
    <Card className="p-5">
      <SectionTitle icon={Icon} title={title} subtitle={subtitle} />
      {source.status === "rejected" ? (
        <ErrorState
          title={`${title} unavailable`}
          message={source.error}
          onRetry={onRetry}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Icon}
          title={emptyTitle}
          hint={emptyHint}
          action={emptyAction}
        />
      ) : (
        <div className="divide-y divide-hairline">
          {items.map((item) => (
            <Link
              key={item.id}
              to={item.to}
              className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-ink">
                  {item.name}
                </p>
                <p className="mt-0.5 truncate text-xs text-sub">{item.meta}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {item.status && (
                  <Badge tone={STATUS_TONE[item.status] || "slate"}>
                    {labelize(item.status)}
                  </Badge>
                )}
                <ArrowRight
                  size={15}
                  className="text-faint"
                  aria-hidden="true"
                />
              </div>
            </Link>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function ChatProductOverview() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const results = await Promise.allSettled([
      api.get("/agents", { params: { limit: 5, sort: "-updated_at" } }),
      api.get("/knowledge-bases", {
        params: { limit: 5, sort: "-updated_at" },
      }),
      api.get("/knowledge/stats"),
      api.get("/widgets", { params: { limit: 100 } }),
    ]);
    const [agentsResult, knowledgeResult, statsResult, widgetsResult] = results;
    const failed = results.filter((result) => result.status === "rejected");
    if (failed.length === results.length) {
      setError(
        formatApiError(
          failed[0].reason?.response?.data?.detail || failed[0].reason?.message,
        ),
      );
      setData(null);
    } else {
      setData({
        agents: sourceFrom(agentsResult),
        knowledge: sourceFrom(knowledgeResult),
        stats: sourceFrom(statsResult),
        widgets: sourceFrom(widgetsResult),
        failures: failed.length,
      });
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const agents = data?.agents;
    const knowledge = data?.knowledge;
    const stats = data?.stats;
    const widgets = data?.widgets;
    const widgetItems =
      widgets?.status === "fulfilled" ? getItems(widgets.response) : [];
    return {
      agents:
        agents?.status === "fulfilled"
          ? getTotal(agents.response, getItems(agents.response).length)
          : "Unavailable",
      knowledgeBases:
        knowledge?.status === "fulfilled"
          ? getTotal(knowledge.response, getItems(knowledge.response).length)
          : "Unavailable",
      documents:
        stats?.status === "fulfilled"
          ? (stats.response?.data?.total_documents ?? "Unavailable")
          : "Unavailable",
      widgets:
        widgets?.status === "fulfilled"
          ? getTotal(widgets.response, widgetItems.length)
          : "Unavailable",
      publishedWidgets:
        widgets?.status === "fulfilled"
          ? widgetItems.filter((widget) => widget.status === "published").length
          : "Unavailable",
    };
  }, [data]);

  const agentItems = getItems(data?.agents?.response).map((agent) => ({
    id: agent.id,
    name: agent.name,
    meta:
      agent.is_ready === false
        ? "Needs setup before activation"
        : labelize(agent.type),
    status: agent.status,
    to: `/app/agents/${agent.id}`,
  }));
  const knowledgeBaseItems = getItems(data?.knowledge?.response).map(
    (knowledgeBase) => ({
      id: knowledgeBase.id,
      name: knowledgeBase.name,
      meta: `${knowledgeBase.document_count || 0} document${knowledgeBase.document_count === 1 ? "" : "s"}`,
      status: knowledgeBase.status,
      to: `/app/knowledge-base/${knowledgeBase.id}`,
    }),
  );

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Product 1 · AI chat"
        title="Chat workspace"
        subtitle="See the agents, knowledge, and widgets that power your customer conversations."
        icon={MessageSquare}
        actions={
          <>
            <GhostButton as={Link} to="/app/knowledge-base">
              <BookOpen size={16} /> Knowledge
            </GhostButton>
            <PrimaryButton as={Link} to="/app/agents/new">
              <Plus size={16} /> New agent
            </PrimaryButton>
          </>
        }
      />

      {loading ? (
        <SummarySkeleton />
      ) : error ? (
        <ErrorState
          title="Product summary unavailable"
          message={error}
          onRetry={load}
        />
      ) : (
        <>
          {data?.failures > 0 && (
            <div
              className="flex items-center justify-between gap-3 rounded-xl border border-warning/20 bg-warning-soft px-4 py-3 text-sm text-warning-ink"
              role="status"
            >
              <span>
                Some Product 1 data could not be loaded. Values below reflect
                the available services.
              </span>
              <button
                type="button"
                className="inline-flex shrink-0 items-center gap-1 font-semibold hover:underline"
                onClick={load}
              >
                <RefreshCw size={14} /> Retry
              </button>
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard
              icon={Bot}
              label="Agents"
              value={counts.agents}
              sub="Manage your chat agents"
              to="/app/agents"
            />
            <StatCard
              icon={FileText}
              label="Knowledge documents"
              value={counts.documents}
              sub={
                data?.knowledge?.status === "fulfilled"
                  ? `${counts.knowledgeBases} knowledge base${counts.knowledgeBases === 1 ? "" : "s"}`
                  : "Knowledge bases unavailable"
              }
              to="/app/products/chat/knowledge/documents"
            />
            <StatCard
              icon={LayoutGrid}
              label="Widgets"
              value={counts.widgets}
              sub={
                data?.widgets?.status === "fulfilled"
                  ? `${counts.publishedWidgets} published`
                  : "Widget data unavailable"
              }
              to="/app/widgets"
            />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
            <ResourceList
              title="Recent agents"
              subtitle="Your latest Product 1 agent records"
              icon={Bot}
              items={agentItems}
              source={data.agents}
              onRetry={load}
              emptyTitle="No agents yet"
              emptyHint="Create an agent to start configuring your chat experience."
              emptyAction={
                <PrimaryButton as={Link} to="/app/agents/new">
                  <Plus size={15} /> Create agent
                </PrimaryButton>
              }
            />
            <ResourceList
              title="Knowledge bases"
              subtitle="Sources available to your agents"
              icon={BookOpen}
              items={knowledgeBaseItems}
              source={data.knowledge}
              onRetry={load}
              emptyTitle="No knowledge bases yet"
              emptyHint="Create a knowledge base before adding documents."
              emptyAction={
                <GhostButton as={Link} to="/app/knowledge-base">
                  <Plus size={15} /> Open knowledge
                </GhostButton>
              }
            />
          </div>

          <Card className="p-5">
            <SectionTitle
              icon={Sparkles}
              title="Next steps"
              subtitle="Use the live Product 1 workflows to complete your setup"
            />
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <Link
                to="/app/agents/new"
                className="group rounded-xl border border-line bg-subtle p-4 transition hover:border-brand/30 hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
              >
                <Bot size={18} className="text-brand" />
                <p className="mt-3 text-sm font-semibold text-ink">
                  Create an agent
                </p>
                <p className="mt-1 text-xs text-sub">
                  Define how your assistant should respond.
                </p>
                <ArrowRight
                  size={15}
                  className="mt-3 text-faint transition group-hover:translate-x-0.5 group-hover:text-brand"
                />
              </Link>
              <Link
                to="/app/knowledge-base"
                className="group rounded-xl border border-line bg-subtle p-4 transition hover:border-brand/30 hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
              >
                <Waypoints size={18} className="text-brand" />
                <p className="mt-3 text-sm font-semibold text-ink">
                  Add knowledge
                </p>
                <p className="mt-1 text-xs text-sub">
                  Organize the documents your agents can use.
                </p>
                <ArrowRight
                  size={15}
                  className="mt-3 text-faint transition group-hover:translate-x-0.5 group-hover:text-brand"
                />
              </Link>
              <Link
                to="/app/widgets"
                className="group rounded-xl border border-line bg-subtle p-4 transition hover:border-brand/30 hover:bg-brand-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
              >
                <LayoutGrid size={18} className="text-brand" />
                <p className="mt-3 text-sm font-semibold text-ink">
                  Manage widgets
                </p>
                <p className="mt-1 text-xs text-sub">
                  Review the web chat surfaces you have configured.
                </p>
                <ArrowRight
                  size={15}
                  className="mt-3 text-faint transition group-hover:translate-x-0.5 group-hover:text-brand"
                />
              </Link>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
