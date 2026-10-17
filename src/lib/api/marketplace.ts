import { apiRequest } from "./client";

// Marketplace catalogue and installs, matching backend/app/api/marketplace/routes.py.
// Installs go into the workspace (project) named by X-Project-Id.

export type MarketplaceCategory = "agent_template" | "integration" | "workflow";

// Requirement statuses set by the server (backend/app/services/marketplace.py).
export type RequirementStatus =
  "satisfied" | "requires_integration" | "unavailable" | "unsupported";

export type MarketplaceRequirement = {
  kind: string;
  key: string;
  label: string;
  status: RequirementStatus;
  message: string;
  blocking: boolean;
};

export type MarketplaceListing = {
  slug: string;
  name: string;
  category: MarketplaceCategory;
  summary: string;
  icon: string;
  tags: string[];
  author: string;
  featured: boolean;
  installed: boolean;
  installable: boolean;
  requirements: MarketplaceRequirement[];
  rating: number;
  review_count: number;
};

export type MarketplaceInstallation = {
  id: string;
  listing_slug: string;
  listing_name: string;
  category: string;
  status: string;
  agent_id: string | null;
  created_at: string;
};

export type MarketplaceInstallResponse = {
  installation: MarketplaceInstallation;
  agent_id: string | null;
  workflow_id: string | null;
  requirements: MarketplaceRequirement[];
};

export function listMarketplaceListings(
  workspaceId: string,
  filters: { category?: MarketplaceCategory; q?: string } = {},
): Promise<MarketplaceListing[]> {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.q) params.set("q", filters.q);
  const query = params.toString();
  return apiRequest<MarketplaceListing[]>(`/marketplace/listings${query ? `?${query}` : ""}`, {
    projectId: workspaceId,
  });
}

export function installMarketplaceListing(
  workspaceId: string,
  slug: string,
): Promise<MarketplaceInstallResponse> {
  return apiRequest<MarketplaceInstallResponse>(
    `/marketplace/listings/${encodeURIComponent(slug)}/install`,
    { method: "POST", projectId: workspaceId },
  );
}
