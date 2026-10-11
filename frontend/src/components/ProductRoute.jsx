import React from "react";
import { useNavigate } from "react-router-dom";
import { EmptyState } from "@/components/ui/EmptyState";
import OraOneLoader from "@/components/ui/OraOneLoader";
import { useEntitlements, useRequestAccess } from "@/lib/entitlements";

// Phase 1.5 — client-side product gate.
//
// Mirrors the backend fail-closed `require_product` guard for UX: blocks a
// product surface when the org isn't entitled, shows a maintenance notice
// during platform maintenance, and a "Coming soon" notice for pre-launch
// products. When simply not entitled, it offers a "Request Access" CTA that
// records an audit-logged request for the platform team.
//
// Fail-open while loading so entitled customers never see a flash of the
// blocked screen.
export default function ProductGate({ productKey, productName = "This product", children }) {
  const navigate = useNavigate();
  const {
    isProductEnabled,
    isProductInMaintenance,
    isComingSoon,
    isLoading,
  } = useEntitlements();
  const requestAccess = useRequestAccess();

  const backToDashboard = () => navigate("/app/dashboard");

  if (isLoading) {
    return (
      <div className="min-h-[50vh] grid place-items-center">
        <OraOneLoader label={`Loading ${productName}…`} fullScreen={false} />
      </div>
    );
  }

  if (isProductInMaintenance(productKey)) {
    return (
      <div className="max-w-xl mx-auto mt-10">
        <EmptyState
          size="lg"
          title={`${productName} is under maintenance`}
          description="We're performing scheduled maintenance on this product. Please check back shortly — your data is safe."
          actionLabel="Back to Dashboard"
          onAction={backToDashboard}
        />
      </div>
    );
  }

  if (isComingSoon(productKey)) {
    return (
      <div className="max-w-xl mx-auto mt-10">
        <EmptyState
          size="lg"
          title={`${productName} is coming soon`}
          description="This product isn't available yet. We'll let your administrator know the moment it launches."
          actionLabel="Notify me"
          onAction={() =>
            requestAccess.mutate({ productKey, reason: "coming_soon_notify" })
          }
          secondaryLabel="Back to Dashboard"
          onSecondary={backToDashboard}
        />
      </div>
    );
  }

  if (!isProductEnabled(productKey)) {
    const requested = requestAccess.isSuccess;
    return (
      <div className="max-w-xl mx-auto mt-10">
        <EmptyState
          size="lg"
          title={`${productName} isn't enabled for your workspace`}
          description={
            requested
              ? "Thanks — your request has been sent to your administrator. You'll be notified once access is granted."
              : "Your organization doesn't currently have access to this product. Contact your administrator or request access below."
          }
          actionLabel={requested ? "Request sent" : requestAccess.isPending ? "Requesting…" : "Request Access"}
          onAction={
            requested || requestAccess.isPending
              ? undefined
              : () => requestAccess.mutate({ productKey })
          }
          secondaryLabel="Back to Dashboard"
          onSecondary={backToDashboard}
        />
      </div>
    );
  }

  return children;
}
