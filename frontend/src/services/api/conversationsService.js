/**
 * Conversations service — thin wrapper over the REST API (chat/v2 surface).
 */
import { api } from "@/lib/api";

export const conversationsService = {
  list: async (params = {}) => {
    const { data } = await api.get("/v2/conversations", { params });
    return Array.isArray(data) ? data : data?.items || [];
  },

  get: async (id) => {
    const { data } = await api.get(`/v2/conversations/${id}`);
    return data;
  },

  messages: async (id) => {
    const { data } = await api.get(`/v2/conversations/${id}/messages`);
    return Array.isArray(data) ? data : data?.items || [];
  },

  sendMessage: async (id, payload) => {
    const { data } = await api.post(`/v2/conversations/${id}/messages`, payload);
    return data;
  },

  update: async (id, payload) => {
    const { data } = await api.put(`/v2/conversations/${id}`, payload);
    return data;
  },

  remove: async (id) => {
    await api.delete(`/v2/conversations/${id}`);
  },
};
