import { apiRequest } from "./client";

// Integrations are listed per workspace (project). The catalog marks which
// providers are available; `integration` is set once this workspace connects one.

export type IntegrationCatalog = {
  provider: string;
  name: string;
  category: string;
  type: string;
  auth: string;
  description: string;
  available: boolean;
};

export type Integration = {
  id: string;
  provider: string;
  category: string | null;
  type: string;
  status: string;
  connection_type: string;
  external_account: string | null;
  sync_schedule: string;
  last_synced_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type IntegrationCatalogEntry = {
  catalog: IntegrationCatalog;
  integration: Integration | null;
};

export type IntegrationCatalogResponse = {
  items: IntegrationCatalogEntry[];
  total: number;
};

export type ConnectResponse = {
  integration: Integration | null;
  authorize_url: string | null;
};

export type SyncJob = {
  id: string;
  integration_id: string;
  status: string;
  trigger: string;
  documents_synced: number;
  error_message: string | null;
  created_at: string;
};

export function listIntegrations(projectId: string) {
  return apiRequest<IntegrationCatalogResponse>("/integrations", { projectId });
}

/** Starts a real OAuth connection. Returns an authorize URL to visit, or the connected row. */
export function connectIntegration(projectId: string, provider: string) {
  return apiRequest<ConnectResponse>("/integrations/connect", {
    method: "POST",
    body: { provider },
    projectId,
  });
}

export function syncIntegration(projectId: string, integrationId: string) {
  return apiRequest<SyncJob>(`/integrations/${integrationId}/sync`, {
    method: "POST",
    projectId,
  });
}

export function disconnectIntegration(projectId: string, integrationId: string) {
  return apiRequest<unknown>(`/integrations/${integrationId}`, {
    method: "DELETE",
    projectId,
  });
}
