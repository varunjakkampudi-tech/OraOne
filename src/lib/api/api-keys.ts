import { apiRequest } from "./client";

// API keys are scoped to a workspace (project). The secret is returned once, on
// creation, and cannot be shown again.

export type ApiKey = {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
};

export type ScopeOption = { scope: string; label: string };

export type ApiKeyList = { keys: ApiKey[]; scopes: ScopeOption[] };

export function listApiKeys(projectId: string) {
  return apiRequest<ApiKeyList>("/api-keys", { projectId });
}

export function createApiKey(projectId: string, input: { name: string; scopes: string[] }) {
  return apiRequest<{ key: string; api_key: ApiKey }>("/api-keys", {
    method: "POST",
    body: input,
    projectId,
  });
}

export function deleteApiKey(keyId: string) {
  return apiRequest<void>(`/api-keys/${keyId}`, { method: "DELETE" });
}
