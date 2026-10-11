/**
 * Agents service — thin wrapper over the REST API. No React, no caching
 * logic here (that's @/features/agents/hooks/useAgents.js's job via
 * TanStack Query) — this module only knows how to talk to the backend.
 */
import { api } from "@/lib/api";

export const agentsService = {
  list: async (params = {}) => {
    const { data } = await api.get("/agents", { params });
    // List endpoint returns { items, total, limit, offset }.
    return {
      items: Array.isArray(data) ? data : data?.items || [],
      total: Array.isArray(data) ? data.length : data?.total ?? 0,
    };
  },

  get: async (id) => {
    const { data } = await api.get(`/agents/${id}`);
    return data;
  },

  create: async (payload) => {
    const { data } = await api.post("/agents", payload);
    return data;
  },

  update: async (id, payload) => {
    const { data } = await api.put(`/agents/${id}`, payload);
    return data;
  },

  remove: async (id) => {
    await api.delete(`/agents/${id}`);
  },

  duplicate: async (id) => {
    const full = await agentsService.get(id);
    return agentsService.create({
      name: `${full.name} (Copy)`,
      type: full.type,
      description: full.description ?? undefined,
      model: full.model ?? undefined,
      status: "draft",
      avatar_url: full.avatar_url ?? undefined,
      system_prompt: full.system_prompt ?? undefined,
      temperature: full.temperature ?? undefined,
      voice: full.voice ?? undefined,
      language: full.language ?? undefined,
      greeting: full.greeting ?? undefined,
      max_tokens: full.max_tokens ?? undefined,
    });
  },

  bulkUpdateStatus: async (ids, status) => {
    await Promise.all(ids.map((id) => agentsService.update(id, { status })));
  },

  bulkRemove: async (ids) => {
    await Promise.all(ids.map((id) => agentsService.remove(id)));
  },
};
