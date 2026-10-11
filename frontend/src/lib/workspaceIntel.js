import { api } from "@/lib/api";

// Workspace-intelligence client — optimization score, knowledge coverage,
// revenue attribution, customer 360, confidence heatmap, simulator.
export const workspaceIntelApi = {
  optimizationScore: () => api.get("/workspace/optimization-score").then((r) => r.data),
  knowledgeCoverage: () => api.get("/workspace/knowledge-coverage").then((r) => r.data),
  revenueAttribution: (days = 90) =>
    api.get("/workspace/revenue-attribution", { params: { days } }).then((r) => r.data),
  customer360: (q) =>
    api.get("/workspace/customer-360", { params: { q } }).then((r) => r.data),
  confidenceHeatmap: (conversationId) =>
    api.get(`/workspace/confidence-heatmap/${conversationId}`).then((r) => r.data),
  simulatorScenarios: () => api.get("/workspace/simulator/scenarios").then((r) => r.data),
  runSimulator: (agentId, scenarios) =>
    api.post("/workspace/simulator/run", { agent_id: agentId, scenarios }).then((r) => r.data),
};
