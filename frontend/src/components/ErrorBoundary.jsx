import React from "react";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";

/**
 * App-level error boundary. Catches render-time JS errors and shows a
 * branded "Something went wrong" screen with retry + home actions.
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    if (process.env.NODE_ENV === "development") {
      console.error("[OraOne] Uncaught error:", error, info?.componentStack);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleHome = () => {
    window.location.href = "/";
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div
        role="alert"
        aria-live="assertive"
        className="min-h-screen bg-[#F8FAFC] grid place-items-center px-4"
        data-testid="error-boundary-screen"
      >
        <div className="max-w-md text-center">
          <div className="mx-auto size-16 rounded-2xl bg-[#FEF2F2] grid place-items-center">
            <AlertTriangle size={28} className="text-[#DC2626]" aria-hidden="true" />
          </div>
          <h1 className="mt-6 text-2xl sm:text-3xl font-bold tracking-tight text-[#0F172A]">
            Something went wrong
          </h1>
          <p className="mt-3 text-[#64748B] text-sm">
            An unexpected error occurred while rendering this page. You can retry, or head back home.
          </p>
          <div className="mt-7 flex items-center justify-center gap-2.5">
            <button
              type="button"
              onClick={this.handleReset}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold transition-colors"
              data-testid="error-retry-btn"
            >
              <RotateCcw size={15} /> Try again
            </button>
            <button
              type="button"
              onClick={this.handleHome}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white border border-[#E2E8F0] hover:bg-[#F8FAFC] text-sm font-semibold text-[#0F172A] transition-colors"
              data-testid="error-home-btn"
            >
              <Home size={15} /> Go home
            </button>
          </div>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
