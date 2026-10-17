import { apiRequest } from "./client";

// Channel and deploy state for one assistant, matching backend/app/api/channels/routes.py
// and backend/app/schemas/channels.py. The setup pages read these rows and save the
// user-settable fields through updateAgentChannel. Secrets are never read back: they come
// once, in a one-time response, and afterwards only as masked hints.

export type ChannelRead = {
  channel: string;
  label: string;
  description: string;
  icon: string;
  enabled: boolean;
  /** Server value: "active", "paused" or "disabled" (backend ChannelStatus). */
  status: string;
  embeddable: boolean;
  phone_number: string | null;
  provider: string | null;
  /** Non-secret settings only, for example { phone_number_id: "..." }. */
  configuration: Record<string, string>;
  /** Display-only forms of stored secrets, for example { sdk_secret: "••••a1b2" }. */
  masked_secrets: Record<string, string>;
  /** Present only in the response that generated the secret. Shown once, never stored. */
  one_time_secret?: OneTimeSecret | null;
};

export type OneTimeSecret = {
  name: string;
  value: string;
  shown_once: boolean;
};

export type SecretRotation = {
  channel: string;
  secret_name: string;
  secret: string;
  masked: string;
  shown_once: boolean;
};

export type ChannelSettingsBody = {
  phone_number_id?: string | null;
  instagram_account_id?: string | null;
  phone_number?: string | null;
  inbound_address?: string | null;
};

export type ChannelUpdateBody = {
  enabled?: boolean;
  settings?: ChannelSettingsBody;
};

export type ChannelsResponse = {
  agent_id: string;
  agent_name: string;
  items: ChannelRead[];
};

export type DeployInfo = {
  agent_id: string;
  agent_name: string;
  widget_status: string;
  deploy_status: string;
  domains: string[];
  verification: {
    installed: boolean;
    events_count: number;
    loads_count: number;
    last_seen: string | null;
  };
};

export function listAgentChannels(agentId: string) {
  return apiRequest<ChannelsResponse>(`/agents/${encodeURIComponent(agentId)}/channels`);
}

export function getAgentDeploy(agentId: string) {
  return apiRequest<DeployInfo>(`/agents/${encodeURIComponent(agentId)}/deploy`);
}

export function updateAgentChannel(agentId: string, channel: string, body: ChannelUpdateBody) {
  return apiRequest<ChannelRead>(
    `/agents/${encodeURIComponent(agentId)}/channels/${encodeURIComponent(channel)}`,
    { method: "PATCH", body },
  );
}

export function rotateAgentChannelSecret(agentId: string, channel: string) {
  return apiRequest<SecretRotation>(
    `/agents/${encodeURIComponent(agentId)}/channels/${encodeURIComponent(channel)}/rotate-secret`,
    { method: "POST", body: {} },
  );
}
