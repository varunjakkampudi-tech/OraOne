import React from "react";
import { Outlet, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Logo } from "@/components/marketing/Logo";

/**
 * AuthLayout — centered card on a soft light background (matches mockup 06–08).
 *
 *   • Soft #F8FAFC canvas with subtle blue/cyan glow accents
 *   • Centered OraOne logo at the top of a white rounded card
 *   • <Outlet /> renders the page-specific content (heading + form)
 *   • Terms / Privacy footer beneath the card
 */
export default function AuthLayout() {
  return (
    <div
      className="relative min-h-screen bg-[#F8FAFC] flex flex-col items-center justify-center px-4 py-10 overflow-hidden"
      data-testid="auth-layout-root"
    >
      {/* Background accents */}
      <div
        className="pointer-events-none absolute -top-40 -left-32 h-[420px] w-[420px] rounded-full"
        style={{ background: "radial-gradient(circle, rgba(59,130,246,0.14), transparent 65%)" }}
      />
      <div
        className="pointer-events-none absolute -bottom-44 -right-32 h-[460px] w-[460px] rounded-full"
        style={{ background: "radial-gradient(circle, rgba(6,182,212,0.12), transparent 65%)" }}
      />

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
        className="relative z-10 w-full max-w-[440px]"
      >
        <main className="rounded-2xl border border-[#E2E8F0] bg-white p-7 sm:p-8 shadow-[0_24px_60px_-30px_rgba(15,23,42,0.25)]">
          <div className="flex justify-center">
            <Link to="/" data-testid="auth-brand-link" aria-label="OraOne home">
              <Logo className="h-9" />
            </Link>
          </div>

          <Outlet />
        </main>

        <p className="mt-6 text-center text-xs leading-relaxed text-[#94A3B8]">
          By continuing you agree to our{" "}
          <Link to="/terms" className="font-medium text-[#64748B] hover:text-[#2563EB] hover:underline">
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link to="/privacy" className="font-medium text-[#64748B] hover:text-[#2563EB] hover:underline">
            Privacy Policy
          </Link>
          .
        </p>
      </motion.div>
    </div>
  );
}
