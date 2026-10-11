import React from "react";
import { Link } from "react-router-dom";
import { useSEO } from "@/lib/seo";
import { ArrowLeft } from "lucide-react";

export default function NotFound() {
  useSEO({ title: "404 — Page Not Found", description: "The page you are looking for doesn't exist." });
  return (
    <div className="min-h-[60vh] py-20 grid place-items-center bg-[#F8FAFC]">
      <div className="text-center px-4">
        <div className="relative inline-block">
          <p className="text-[120px] sm:text-[200px] lg:text-[260px] leading-none font-black tracking-tighter gradient-text">404</p>
        </div>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-[#0F172A]">Page Not Found</h1>
        <p className="mt-3 text-[#64748B] max-w-md mx-auto">Oops! The page you're looking for doesn't exist or has been moved.</p>
        <Link to="/" className="mt-8 inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold" data-testid="404-back-home">
          <ArrowLeft size={16} /> Go Back Home
        </Link>
      </div>
    </div>
  );
}
