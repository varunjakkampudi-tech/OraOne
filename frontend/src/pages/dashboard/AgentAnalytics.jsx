import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { Activity, ArrowLeft, BarChart3, RefreshCw } from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import {
  Badge,
  Card,
  EmptyState,
  GhostButton,
  PageHeader,
  SectionTitle,
  StatCard,
} from "@/components/dashboard/kit";
import { ErrorState, Skeleton } from "@/components/dashboard/states";

const toneForStatus = {
  active: "green",
  draft: "slate",
  paused: "amber",
  archived: "red",
};

export default function AgentAnalytics() {
  const [searchParams] = useSearchParams();
  const { id } = useParams();
  const agentId = id || searchParams.get("agent")?.trim() || "";
  const [data, setData] = useState(null);
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setData(null);
    setAgent(null);
    if (!agentId) {
      setError("Choose an agent to view its analytics.");
      setLoading(false);
      return;
    }

    try {
      const [{ data: analytics }, agentResponse] = await Promise.all([
        api.get("/analytics/agents", {
          params: { days: 30, agent_id: agentId },
        }),
        api.get(`/agents/${agentId}`),
      ]);
      const match = (analytics?.agents || []).find(
        (item) => String(item.agent_id) === agentId,
      );
      if (!match) {
        throw new Error(
          "This agent is not present in the analytics aggregate.",
        );
      }
      setData(analytics);
      setAgent(agentResponse.data);
    } catch (requestError) {
      setError(
        formatApiError(requestError?.response?.data?.detail) ||
          requestError.message ||
          "Could not load agent analytics.",
      );
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    load();
  }, [load]);

  const metrics = useMemo(() => {
    const item = data?.agents?.find(
      (entry) => String(entry.agent_id) === agentId,
    );
    return item || null;
  }, [agentId, data]);

  return (
    <div className="mx-auto max-w-5xl space-y-7">
      <PageHeader
        icon={BarChart3}
        eyebrow="Product 1 · Agent analytics"
        title={agent?.name || "Agent analytics"}
        subtitle="Conversation outcomes for this agent from the live analytics aggregate."
        actions={
          <GhostButton as={Link} to="/app/agents">
            <ArrowLeft size={15} /> Back to agents
          </GhostButton>
        }
      />

      {loading ? (
        <div
          className="grid grid-cols-1 gap-4 sm:grid-cols-3"
          role="status"
          aria-busy="true"
        >
          <span className="sr-only">Loading agent analytics…</span>
          <Skeleton className="h-36 rounded-2xl" />
          <Skeleton className="h-36 rounded-2xl" />
          <Skeleton className="h-36 rounded-2xl" />
        </div>
      ) : error ? (
        <ErrorState
          title="Agent analytics unavailable"
          message={error}
          onRetry={load}
        />
      ) : metrics ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard
              icon={Activity}
              label="Conversations"
              value={metrics.conversations}
              sub={`Last ${data.range_days} days`}
            />
            <StatCard
              icon={BarChart3}
              label="Qualified"
              value={metrics.qualified}
              sub="Conversations qualified"
            />
            <StatCard
              icon={Activity}
              label="Conversion rate"
              value={`${metrics.conversion_rate}%`}
              sub="Qualified ÷ conversations"
            />
          </div>
          <Card className="p-5">
            <SectionTitle
              icon={BarChart3}
              title="Agent status"
              subtitle="Identity and status from the agent record"
            />
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-subtle p-4">
              <div>
                <p className="text-sm font-semibold text-ink">
                  {agent?.name || metrics.name}
                </p>
                <p className="mt-1 text-xs text-sub">
                  Analytics range: last {data.range_days} days
                </p>
              </div>
              <Badge tone={toneForStatus[metrics.status] || "slate"}>
                {metrics.status}
              </Badge>
            </div>
          </Card>
        </>
      ) : (
        <EmptyState
          icon={BarChart3}
          title="No analytics for this agent"
          hint="The selected agent has no matching record in the current analytics aggregate."
          action={
            <GhostButton onClick={load}>
              <RefreshCw size={15} /> Refresh
            </GhostButton>
          }
        />
      )}
    </div>
  );
}
