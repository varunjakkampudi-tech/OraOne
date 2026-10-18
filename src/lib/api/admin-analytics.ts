// Platform analytics for super-admins and admins. The server returns aggregate counts only:
// no message text, names, emails or phone numbers.

import { apiRequest } from "./client";

export type DailyPoint = { date: string; count: number };

export type PlatformAnalytics = {
  window_days: number;
  generated_at: string;
  totals: {
    organizations: number;
    active_users_30d: number;
    conversations_30d: number;
    messages_30d: number;
    leads_30d: number;
    calls_placed_30d: number;
    workflows_run_30d: number;
  };
  channel_mix: Record<string, number>;
  errors: {
    requests_30d: number;
    server_errors_30d: number;
    error_rate_pct: number;
    source: string;
  };
  daily: {
    conversations: DailyPoint[];
    messages: DailyPoint[];
    server_errors: DailyPoint[];
  };
};

export function getAdminAnalyticsOverview(): Promise<PlatformAnalytics> {
  return apiRequest<PlatformAnalytics>("/admin/analytics/overview");
}
