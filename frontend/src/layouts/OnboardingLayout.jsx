import React from "react";
import { Outlet, useLocation, Link } from "react-router-dom";
import { Logo } from "@/components/marketing/Logo";

const steps = [
  { path: "/onboarding/agent", label: "Select Agent" },
  { path: "/onboarding/business", label: "Business Info" },
  { path: "/onboarding/channels", label: "Connect Channels" },
];

export default function OnboardingLayout() {
  const { pathname } = useLocation();
  const idx = Math.max(0, steps.findIndex((s) => pathname.startsWith(s.path)));

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col">
      <header className="h-16 border-b border-[#E2E8F0] bg-white">
        <div className="max-w-5xl mx-auto h-full flex items-center justify-between px-6">
          <Link to="/"><Logo /></Link>
          <Link to="/login" className="text-sm text-[#64748B] hover:text-[#0F172A]">Sign out</Link>
        </div>
      </header>

      <div className="border-b border-[#E2E8F0] bg-white">
        <div className="max-w-5xl mx-auto px-6 py-5 flex items-center gap-3">
          {steps.map((s, i) => (
            <React.Fragment key={s.path}>
              <div className="flex items-center gap-2.5">
                <div
                  className={`size-7 rounded-full grid place-items-center text-xs font-semibold ${
                    i <= idx ? "bg-[#2563EB] text-white" : "bg-[#E2E8F0] text-[#64748B]"
                  }`}
                >
                  {i + 1}
                </div>
                <span className={`text-sm font-medium ${i === idx ? "text-[#0F172A]" : "text-[#64748B]"}`}>{s.label}</span>
              </div>
              {i < steps.length - 1 && <div className={`flex-1 h-px ${i < idx ? "bg-[#2563EB]" : "bg-[#E2E8F0]"}`} />}
            </React.Fragment>
          ))}
        </div>
      </div>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-12 flex flex-col justify-center">
        <Outlet />
      </main>
    </div>
  );
}
