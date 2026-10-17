import { apiRequest } from "./client";

// Marketing campaigns send one message to a chosen list of leads, scoped to a workspace (project).
// Pass the workspace id as projectId. A send only reports "sent" for a recipient the server
// actually delivered; anything else shows as skipped or failed with the reason the server gives.
// Field names mirror backend/app/schemas/marketing.py.

export const MARKETING_CHANNELS = ["email", "sms", "whatsapp"] as const;
export type MarketingChannel = (typeof MARKETING_CHANNELS)[number];

export const MARKETING_CAMPAIGN_STATUSES = [
  "draft",
  "scheduled",
  "sending",
  "completed",
  "cancelled",
] as const;
export type MarketingCampaignStatus = (typeof MARKETING_CAMPAIGN_STATUSES)[number];

export const MARKETING_RECIPIENT_STATUSES = ["queued", "sent", "skipped", "failed"] as const;
export type MarketingRecipientStatus = (typeof MARKETING_RECIPIENT_STATUSES)[number];

/** The largest number of leads one campaign can reach. Matches the server limit. */
export const MAX_MARKETING_RECIPIENTS = 500;

export type MarketingCampaign = {
  id: string;
  project_id: string;
  name: string;
  channel: MarketingChannel;
  subject: string | null;
  body: string;
  status: MarketingCampaignStatus;
  created_by: string | null;
  created_at: string;
  sent_count: number;
  skipped_count: number;
  failed_count: number;
};

export type MarketingRecipient = {
  id: string;
  lead_id: string;
  lead_label: string;
  status: MarketingRecipientStatus;
  /** Plain-language reason a recipient was not planned to receive the message. */
  skip_reason: string | null;
  /** Plain-language reason a send was refused by the provider or the server. */
  failure_reason: string | null;
  sent_at: string | null;
};

export type MarketingCampaignDetail = MarketingCampaign & {
  queued_count: number;
  recipients: MarketingRecipient[];
};

export type CreateMarketingCampaignInput = {
  name: string;
  channel: MarketingChannel;
  subject: string | null;
  body: string;
  lead_ids: string[];
};

export function listMarketingCampaigns(projectId: string) {
  return apiRequest<MarketingCampaign[]>("/marketing/campaigns", { projectId });
}

export function getMarketingCampaign(projectId: string, campaignId: string) {
  return apiRequest<MarketingCampaignDetail>(
    `/marketing/campaigns/${encodeURIComponent(campaignId)}`,
    { projectId },
  );
}

export function createMarketingCampaign(projectId: string, input: CreateMarketingCampaignInput) {
  return apiRequest<MarketingCampaignDetail>("/marketing/campaigns", {
    method: "POST",
    body: input,
    projectId,
  });
}

export function sendMarketingCampaign(projectId: string, campaignId: string) {
  return apiRequest<MarketingCampaignDetail>(
    `/marketing/campaigns/${encodeURIComponent(campaignId)}/send`,
    { method: "POST", projectId },
  );
}

export function cancelMarketingCampaign(projectId: string, campaignId: string) {
  return apiRequest<MarketingCampaignDetail>(
    `/marketing/campaigns/${encodeURIComponent(campaignId)}/cancel`,
    { method: "POST", projectId },
  );
}
