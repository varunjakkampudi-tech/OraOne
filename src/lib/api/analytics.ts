import { apiRequest } from "./client";

// Organization analytics for the workspace (project) over a window of days.

export type AnalyticsOverview = {
  range_days: number;
  generated_at: string;
  totals: {
    agents: number;
    conversations: number;
    messages: number;
    workflows: number;
    workflow_runs: number;
    knowledge_bases: number;
    documents: number;
    members: number;
    qualified_conversations: number;
    conversion_rate: number;
  };
  series: {
    conversations: { date: string; count: number }[];
    messages: { date: string; count: number }[];
    workflow_runs: { date: string; count: number }[];
  };
  breakdowns: {
    conversations_by_channel: Record<string, number>;
    conversations_by_status: Record<string, number>;
    workflow_runs_by_status: Record<string, number>;
  };
  top_agents: { agent_id: string; name: string; conversations: number }[];
};

export function getAnalyticsOverview(projectId: string, days = 30) {
  return apiRequest<AnalyticsOverview>(`/analytics/overview?days=${days}`, { projectId });
}
