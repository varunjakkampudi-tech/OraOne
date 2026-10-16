import { apiRequest } from "./client";

// Webhook endpoints belong to a workspace (project). The signing secret is
// returned only by create and rotate; it is never readable afterwards.

export type WebhookStatus = "active" | "paused" | "disabled";

export type Webhook = {
  id: string;
  url: string;
  description: string | null;
  status: WebhookStatus | string;
  events: string[];
  failure_count: number;
  last_status: string | null;
  last_delivery_at: string | null;
  created_at: string;
};

export type WebhookEventInfo = { event: string; description: string };

export type WebhookList = {
  webhooks: Webhook[];
  events: WebhookEventInfo[];
};

export type WebhookWithSecret = { webhook: Webhook; secret: string };

export type WebhookDelivery = {
  id: string;
  event: string;
  success: boolean;
  status_code: number | null;
  attempts: number;
  error: string | null;
  created_at: string;
};

export function listWebhooks(projectId: string) {
  return apiRequest<WebhookList>("/webhooks", { projectId });
}

export function createWebhook(
  projectId: string,
  input: { url: string; events: string[]; description?: string | undefined },
) {
  return apiRequest<WebhookWithSecret>("/webhooks", { method: "POST", body: input, projectId });
}

export function updateWebhook(
  webhookId: string,
  input: { status?: "active" | "paused"; events?: string[] },
) {
  return apiRequest<Webhook>(`/webhooks/${webhookId}`, { method: "PATCH", body: input });
}

export function deleteWebhook(webhookId: string) {
  return apiRequest<unknown>(`/webhooks/${webhookId}`, { method: "DELETE" });
}

export function rotateWebhookSecret(webhookId: string) {
  return apiRequest<WebhookWithSecret>(`/webhooks/${webhookId}/rotate`, { method: "POST" });
}

export function testWebhook(webhookId: string) {
  return apiRequest<WebhookDelivery>(`/webhooks/${webhookId}/test`, { method: "POST" });
}

export function listWebhookDeliveries(webhookId: string, limit = 20) {
  return apiRequest<WebhookDelivery[]>(`/webhooks/${webhookId}/deliveries?limit=${limit}`);
}
