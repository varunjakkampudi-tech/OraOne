import { api } from "@/lib/api";

// Agent prompt versioning (features #7/#8).
export const agentVersionsApi = {
  list: (agentId) => api.get(`/agents/${agentId}/versions`).then((r) => r.data),
  publish: (agentId, body) =>
    api.post(`/agents/${agentId}/versions`, body || {}).then((r) => r.data),
  diff: (agentId, fromVersion, toVersion) =>
    api
      .get(`/agents/${agentId}/versions/diff`, {
        params: { from_version: fromVersion, to_version: toVersion },
      })
      .then((r) => r.data),
  restore: (agentId, version) =>
    api.post(`/agents/${agentId}/versions/restore`, { version }).then((r) => r.data),
};
