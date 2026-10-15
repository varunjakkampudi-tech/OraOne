import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export function ProtectedRoute({ children }) {
  const {
    user,
    loading,
    identity,
    identityLoading,
    identityError,
    fetchIdentity,
    authError,
    fetchMe,
  } = useAuth();

  // Initial auth probe in progress.
  if (loading) {
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8FAFC]"
        data-testid="protected-route-auth-loading"
      >
        <div className="flex items-center gap-3 text-[#5B6B82] text-sm">
          <span className="size-2 rounded-full bg-[#2563EB] animate-pulse" />
          Loading your session…
        </div>
      </div>
    );
  }

  if (authError) return <SessionRetry message={authError} onRetry={fetchMe} />;

  // Not signed in.
  if (!user) return <Navigate to="/login" replace />;

  // Signed in but workspace context isn't hydrated yet.
  if (!identity && identityLoading) {
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8FAFC]"
        data-testid="protected-route-identity-loading"
      >
        <div className="flex items-center gap-3 text-[#5B6B82] text-sm">
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
          <h1 className="text-lg font-semibold text-[#0F172A]">
            Couldn&apos;t load your workspace
          </h1>
          <p className="text-sm text-[#5B6B82] leading-relaxed">
            {identityError}
          </p>
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
  const { user, loading, authError, fetchMe } = useAuth();

  if (loading) {
    return (
      <div
        className="min-h-screen grid place-items-center bg-[#F8FAFC]"
        data-testid="guest-route-auth-loading"
      >
        <div className="flex items-center gap-3 text-[#5B6B82] text-sm">
          <span className="size-2 rounded-full bg-[#2563EB] animate-pulse" />
          Loading…
        </div>
      </div>
    );
  }

  if (authError) return <SessionRetry message={authError} onRetry={fetchMe} />;

  if (user) return <Navigate to="/app/dashboard" replace />;

  return children;
}

function SessionRetry({ message, onRetry }) {
  return (
    <div
      className="min-h-screen grid place-items-center bg-[#F8FAFC] p-6"
      data-testid="session-verification-error"
    >
      <div
        className="max-w-md rounded-2xl border border-[#E2E8F0] bg-white p-7 text-center space-y-4"
        role="alert"
      >
        <h1 className="text-lg font-semibold text-[#0F172A]">
          Couldn’t verify your session
        </h1>
        <p className="text-sm text-[#5B6B82]">{message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="rounded-xl bg-[#2563EB] px-5 py-2.5 font-semibold text-white"
          data-testid="session-verification-retry"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
