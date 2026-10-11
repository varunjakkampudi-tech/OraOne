import { api } from "@/lib/api";

// Phase Z — AI Marketplace client. Thin wrapper over the curated catalogue
// + per-tenant installations API.
export const marketplaceApi = {
  categories: () => api.get("/marketplace/categories").then((r) => r.data),
  listings: ({ category, q } = {}) =>
    api
      .get("/marketplace/listings", { params: { category: category || undefined, q: q || undefined } })
      .then((r) => r.data),
  listing: (slug) => api.get(`/marketplace/listings/${slug}`).then((r) => r.data),
  installations: () => api.get("/marketplace/installations").then((r) => r.data),
  install: (slug) => api.post(`/marketplace/listings/${slug}/install`).then((r) => r.data),
  uninstall: (id) => api.delete(`/marketplace/installations/${id}`).then((r) => r.data),
  reviews: (slug) => api.get(`/marketplace/listings/${slug}/reviews`).then((r) => r.data),
  submitReview: (slug, body) =>
    api.put(`/marketplace/listings/${slug}/reviews`, body).then((r) => r.data),
  deleteReview: (slug) =>
    api.delete(`/marketplace/listings/${slug}/reviews`).then((r) => r.data),
};
