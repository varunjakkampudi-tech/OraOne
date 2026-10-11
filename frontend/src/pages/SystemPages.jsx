// Standardised error pages: NetworkError + Maintenance.
// NotFound (404) and ServerError (500) already exist in /pages.

import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { WifiOff, RefreshCw, Wrench, Mail, Home } from "lucide-react";
import { useSEO } from "@/lib/seo";

function Shell({ icon: Icon, title, desc, children, badge }) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#F8FAFC] via-white to-white grid place-items-center px-4 py-12">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md text-center"
      >
        <div className="mx-auto size-20 rounded-3xl bg-white border border-[#E2E8F0] grid place-items-center shadow-premium">
          <Icon size={32} className="text-[#2563EB]" />
        </div>
        {badge && (
          <span className="mt-5 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#FEF3C7] text-[11px] font-bold tracking-[0.2em] text-[#92400E]">
            {badge}
          </span>
        )}
        <h1 className="mt-5 text-3xl sm:text-4xl font-black tracking-tight text-[#0F172A]">{title}</h1>
        <p className="mt-3 text-[#64748B] leading-relaxed">{desc}</p>
        {children}
      </motion.div>
    </div>
  );
}

export function NetworkError() {
  useSEO({ title: "You're offline", description: "Looks like you've lost your internet connection.", noindex: true });
  return (
    <Shell
      icon={WifiOff}
      title="You're offline."
      desc="We can't reach our servers right now. Check your connection and try again."
      badge="NETWORK ERROR"
    >
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        <button
          onClick={() => window.location.reload()}
          data-testid="network-error-retry"
          className="inline-flex items-center gap-1.5 px-5 py-3 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_8px_20px_-6px_rgba(37,99,235,0.5)]"
        >
          <RefreshCw size={14} /> Retry
        </button>
        <Link
          to="/"
          data-testid="network-error-home"
          className="inline-flex items-center gap-1.5 px-5 py-3 rounded-xl border border-[#E2E8F0] hover:border-[#2563EB] hover:text-[#2563EB] text-[#0F172A] text-sm font-semibold"
        >
          <Home size={14} /> Home
        </Link>
      </div>
    </Shell>
  );
}

export function Maintenance() {
  useSEO({ title: "Scheduled maintenance", description: "OraOne is undergoing scheduled maintenance.", noindex: true });
  return (
    <Shell
      icon={Wrench}
      title="We'll be right back."
      desc="OraOne is undergoing scheduled maintenance. Expected back online in under 30 minutes."
      badge="MAINTENANCE"
    >
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        <a
          href="https://status.oraone.in"
          target="_blank"
          rel="noopener noreferrer"
          data-testid="maintenance-status"
          className="inline-flex items-center gap-1.5 px-5 py-3 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_8px_20px_-6px_rgba(37,99,235,0.5)]"
        >
          View Status Page
        </a>
        <a
          href="mailto:support@oraone.in"
          data-testid="maintenance-contact"
          className="inline-flex items-center gap-1.5 px-5 py-3 rounded-xl border border-[#E2E8F0] hover:border-[#2563EB] hover:text-[#2563EB] text-[#0F172A] text-sm font-semibold"
        >
          <Mail size={14} /> Contact Support
        </a>
      </div>
    </Shell>
  );
}

export default NetworkError;
