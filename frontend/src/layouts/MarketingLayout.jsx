import React from "react";
import { Outlet, useLocation } from "react-router-dom";
import Navbar from "@/components/marketing/Navbar";
import Footer from "@/components/marketing/Footer";
import SupportWidget from "@/components/marketing/SupportWidget";

export default function MarketingLayout() {
  const { pathname } = useLocation();
  React.useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [pathname]);

  return (
    <div className="min-h-screen flex flex-col bg-white overflow-x-hidden">
      {/* Skip-to-content link for keyboard / screen-reader users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-[#2563EB] focus:text-white focus:font-semibold focus:shadow-lg focus:outline-none focus:ring-4 focus:ring-[#2563EB]/30"
      >
        Skip to main content
      </a>
      <Navbar />
      <main id="main-content" className="flex-1 pt-16" tabIndex="-1">
        <Outlet />
      </main>
      <Footer />
      <SupportWidget />
    </div>
  );
}
