import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export function ProtectedRoute({ children }) {
  const { user, loading, identity, identityLoading, identityError, fetchIdentity } = useAuth();

  // Initial auth probe in progress.
  if (loading) {
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8FAFC]"
        data-testid="protected-route-auth-loading"
      >
        <div className="flex items-center gap-3 text-[#64748B] text-sm">
          <span className="size-2 rounded-full bg-[#2563EB] animate-pulse" />
          Loading your session…
        </div>
      </div>
    );
  }

  // Not signed in.
  if (!user) return <Navigate to="/login" replace />;

  // Signed in but workspace context isn't hydrated yet.
  if (!identity && identityLoading) {
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8FAFC]"
        data-testid="protected-route-identity-loading"
      >
        <div className="flex items-center gap-3 text-[#64748B] text-sm">
          <span className="size-2 rounded-full bg-[#2563EB] animate-pulse" />
          Loading your workspace…
        </div>
      </div>
    );
  }

  // Identity load failed and we have nothing cached — surface a retry UI.
  if (!identity && identityError) {
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8FAFC] p-6"
        data-testid="protected-route-identity-error"
      >
        <div className="max-w-md w-full bg-white rounded-2xl border border-[#E2E8F0] shadow-sm p-7 text-center space-y-4">
          <h1 className="text-lg font-semibold text-[#0F172A]">Couldn&apos;t load your workspace</h1>
          <p className="text-sm text-[#64748B] leading-relaxed">{identityError}</p>
          <button
            onClick={fetchIdentity}
            className="px-5 py-2.5 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold transition-colors"
            data-testid="protected-route-identity-retry"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return children;
}

/**
 * GuestRoute — the inverse of ProtectedRoute. Blocks already-authenticated
 * users from reaching guest-only pages (login, signup, password recovery) and
 * sends them straight to the dashboard.
 */
export function GuestRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8FAFC]"
        data-testid="guest-route-auth-loading"
      >
        <div className="flex items-center gap-3 text-[#64748B] text-sm">
          <span className="size-2 rounded-full bg-[#2563EB] animate-pulse" />
          Loading…
        </div>
      </div>
    );
  }

  if (user) return <Navigate to="/app/dashboard" replace />;

  return children;
}
