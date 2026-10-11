import { api } from "@/lib/api";

// Bonus AI assistants client.
export const assistantsApi = {
  list: () => api.get("/assistants").then((r) => r.data),
  run: (kind, input) => api.post(`/assistants/${kind}/run`, { input }).then((r) => r.data),
};
