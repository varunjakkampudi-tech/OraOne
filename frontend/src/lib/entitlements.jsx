import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

// Phase 1.5 — client-side product & feature entitlements.
//
// Fetches the caller's effective entitlements once (React Query dedupes and
// caches across every consumer) and exposes cheap predicates for gating UI.
//
// The BACKEND is the authoritative, fail-closed authority (unknown product /
// feature => denied at the API). This client layer is purely presentational:
// it decides what to *show*. We keep it fail-OPEN while loading / on unknown
// keys so a paying customer never sees functionality flicker away on a slow
// network — the server still enforces access if they act on it.

async function fetchEntitlements() {
  const { data } = await api.get("/entitlements/me");
  return data;
}

export function useEntitlements() {
  const { isAuthenticated } = useAuth();

  const query = useQuery({
    queryKey: ["entitlements", "me"],
    queryFn: fetchEntitlements,
    enabled: !!isAuthenticated,
    staleTime: 60_000,
  });

  const products = query.data?.products || {};
  const features = query.data?.features || {};
  const maintenance = query.data?.maintenance || {};
  const statuses = query.data?.statuses || {};
  const catalog = query.data?.catalog || [];

  const catalogByKey = catalog.reduce((acc, p) => {
    acc[p.key] = p;
    return acc;
  }, {});

  const getProduct = (key) => catalogByKey[key] || null;
  const isProductEnabled = (key) => products[key] !== false;
  const isProductInMaintenance = (key) => maintenance[key] === true;
  const getProductStatus = (key) => statuses[key] || getProduct(key)?.status || null;
  const isComingSoon = (key) => getProductStatus(key) === "coming_soon";
  const isBeta = (key) => getProductStatus(key) === "beta";
  const isPreview = (key) => getProductStatus(key) === "preview";
  const isDeprecated = (key) => getProductStatus(key) === "deprecated";
  const isFeatureEnabled = (name) => features[name] !== false;

  return {
    products,
    features,
    maintenance,
    statuses,
    catalog,
    getProduct,
    getProductStatus,
    isProductEnabled,
    isProductInMaintenance,
    isComingSoon,
    isBeta,
    isPreview,
    isDeprecated,
    isFeatureEnabled,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}

// Convenience single-feature hook (Product → Feature gating).
export function useFeature(name) {
  const { isFeatureEnabled, isLoading } = useEntitlements();
  return { enabled: isFeatureEnabled(name), isLoading };
}

// Mutation for the "Request Access" CTA on locked product surfaces. Records an
// audit-logged request server-side; never grants access itself.
export function useRequestAccess() {
  return useMutation({
    mutationFn: async ({ productKey, reason }) => {
      const { data } = await api.post("/entitlements/request-access", {
        product_key: productKey,
        reason: reason || null,
      });
      return data;
    },
  });
}
