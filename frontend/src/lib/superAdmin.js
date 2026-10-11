import { api } from "@/lib/api";

// Super Admin Control Center API client. All routes are platform-scoped and
// gated server-side by the PLATFORM_ADMIN_EMAILS allow-list.
const get = (path, params) => api.get(`/super-admin${path}`, { params }).then((r) => r.data);

export const superAdminApi = {
  me: () => get("/me"),
  overview: () => get("/overview"),
  activity: (limit = 40) => get("/activity", { limit }),
  customers: (params) => get("/customers", params),
  customer: (id) => get(`/customers/${id}`),
  conversations: (params) => get("/conversations", params),
  auditLogs: (params) => get("/audit-logs", params),
  billing: () => get("/billing"),
  usage: () => get("/usage"),
  security: () => get("/security"),
  infrastructure: () => get("/infrastructure"),
  releases: () => get("/releases"),
  featureFlags: () => get("/feature-flags"),
  setFeatureFlag: (key, body) => api.patch(`/super-admin/feature-flags/${key}`, body).then((r) => r.data),
  secrets: () => get("/secrets"),
  resources: (kind, params) => get(`/resources/${kind}`, params),

  // Products & entitlements (Phase 1)
  products: () => get("/products"),
  entitlementsOverview: () => get("/entitlements/overview"),
  authzMetrics: () => get("/authz-metrics"),
  setProduct: (key, body) => api.patch(`/super-admin/products/${key}`, body).then((r) => r.data),
  customerEntitlements: (orgId) => get(`/customers/${orgId}/entitlements`),
  setCustomerEntitlement: (orgId, productKey, body) =>
    api.patch(`/super-admin/customers/${orgId}/entitlements/${productKey}`, body).then((r) => r.data),

  // Platform intelligence
  costOptimization: (days) => get("/cost-optimization", days ? { days } : undefined),
  quality: () => get("/quality"),
  selfImprovement: () => get("/self-improvement"),
  benchmarking: () => get("/benchmarking"),
  healthMonitor: () => get("/health-monitor"),
  fraud: () => get("/fraud"),
  compliance: () => get("/compliance"),
  tenantIsolation: () => get("/tenant-isolation"),

  // Universal search / Ora Copilot / Report generator
  search: (q, limit = 8) => get("/search", { q, limit }),
  copilot: (question) => api.post(`/super-admin/copilot`, { question }).then((r) => r.data),
  report: (period) => get(`/reports/${period}`),
};
