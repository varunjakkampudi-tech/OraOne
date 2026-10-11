import React from "react";
import { Link } from "react-router-dom";
import { useSEO } from "@/lib/seo";
import { ServerCrash, RotateCcw } from "lucide-react";

export default function ServerError() {
  useSEO({
    title: "500 — Server Error",
    description: "Something went wrong on our side. Please try again in a moment.",
    noindex: true,
  });
  return (
    <div className="min-h-[60vh] py-20 grid place-items-center bg-[#F8FAFC]">
      <div className="text-center px-4">
        <div className="mx-auto size-16 rounded-2xl bg-[#FEF2F2] grid place-items-center">
          <ServerCrash size={28} className="text-[#DC2626]" aria-hidden="true" />
        </div>
        <p className="mt-6 text-[140px] sm:text-[200px] leading-none font-black tracking-tighter gradient-text">500</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-[#0F172A]">Server Error</h1>
        <p className="mt-3 text-[#64748B] max-w-md mx-auto">
          Something went wrong on our end. Our team has been notified. Please try again in a few moments.
        </p>
        <div className="mt-8 flex items-center justify-center gap-2.5">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold"
            data-testid="500-retry"
          >
            <RotateCcw size={16} /> Try again
          </button>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-white border border-[#E2E8F0] hover:bg-[#F1F5F9] text-sm font-semibold text-[#0F172A]"
            data-testid="500-back-home"
          >
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
