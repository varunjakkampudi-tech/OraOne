import type { MarketplaceListing } from "@/lib/api/marketplace";

// Badge mapping for marketplace listings. Derived only from the server's `installable`
// flag and its blocking requirements, so the UI never claims more than the API reports.

export type ListingStatus = "installable" | "requires_integration" | "not_supported";

export const LISTING_STATUS_LABEL: Record<ListingStatus, string> = {
  installable: "Installable",
  requires_integration: "Requires an integration",
  not_supported: "Not supported yet",
};

export function listingStatus(
  listing: Pick<MarketplaceListing, "installable" | "requirements">,
): ListingStatus {
  if (listing.installable) return "installable";
  const blocking = listing.requirements.filter((r) => r.blocking);
  if (blocking.some((r) => r.status === "unsupported" || r.status === "unavailable")) {
    return "not_supported";
  }
  if (blocking.some((r) => r.status === "requires_integration")) return "requires_integration";
  return "not_supported";
}
