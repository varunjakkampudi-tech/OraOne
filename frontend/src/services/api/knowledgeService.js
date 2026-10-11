/**
 * Knowledge base service — thin wrapper over the REST API.
 */
import { api } from "@/lib/api";

export const knowledgeService = {
  listBases: async (params = {}) => {
    const { data } = await api.get("/knowledge-bases", { params });
    return Array.isArray(data) ? data : data?.items || [];
  },

  getBase: async (id) => {
    const { data } = await api.get(`/knowledge-bases/${id}`);
    return data;
  },

  createBase: async (payload) => {
    const { data } = await api.post("/knowledge-bases", payload);
    return data;
  },

  removeBase: async (id) => {
    await api.delete(`/knowledge-bases/${id}`);
  },

  listDocuments: async (baseId, params = {}) => {
    const { data } = await api.get(`/knowledge-bases/${baseId}/documents`, { params });
    return Array.isArray(data) ? data : data?.items || [];
  },

  uploadDocument: async (baseId, file, extra = {}) => {
    const form = new FormData();
    form.append("file", file);
    Object.entries(extra).forEach(([k, v]) => v !== undefined && form.append(k, v));
    const { data } = await api.post(`/knowledge-bases/${baseId}/documents`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  removeDocument: async (baseId, docId) => {
    await api.delete(`/knowledge-bases/${baseId}/documents/${docId}`);
  },
};
