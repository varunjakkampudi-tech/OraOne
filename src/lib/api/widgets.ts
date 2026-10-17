import { apiRequest } from "./client";

// A website chat widget connects one assistant (agent) to a website.
// The public key identifies the widget in the embed script; it is not a secret.

export type WidgetStatus = "draft" | "published" | "paused";

export type Widget = {
  id: string;
  public_key: string;
  name: string;
  status: WidgetStatus;
  agent_id: string | null;
  domains: string[];
  embed_snippet: string | null;
  settings: Record<string, unknown>;
  theme: Record<string, unknown>;
  published_at: string | null;
  // True when this deployment refuses to load a widget without an allowed-domain list.
  allowed_domains_required: boolean;
};

export type WidgetList = { items: Widget[]; total: number };

export type WidgetAnalytics = {
  widget_id: string;
  status: string;
  sessions: number;
  by_event: Record<string, number>;
  // Newest recorded embed load. Null until a real visit reaches the widget.
  last_loaded_at: string | null;
};

export function getWidgetAnalytics(widgetId: string) {
  return apiRequest<WidgetAnalytics>(`/widgets/${widgetId}/analytics`);
}

export function listWidgets(projectId: string) {
  return apiRequest<WidgetList>("/widgets?limit=100", { projectId });
}

export function createWidget(
  projectId: string,
  input: { name: string; agent_id: string; domains: string[] },
) {
  return apiRequest<Widget>("/widgets", {
    method: "POST",
    projectId,
    body: { ...input, widget_type: "bubble", position: "bottom-right", auth_mode: "public" },
  });
}

export function updateWidgetDomains(widgetId: string, domains: string[]) {
  return apiRequest<Widget>(`/widgets/${widgetId}`, { method: "PUT", body: { domains } });
}

export function setWidgetPublished(widgetId: string, publish: boolean) {
  return apiRequest<Widget>(`/widgets/${widgetId}/publish?publish=${publish ? "true" : "false"}`, {
    method: "POST",
  });
}
