import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { PartyPopper, CheckCircle2, Users, Rocket, ArrowRight } from "lucide-react";
import { useSEO } from "@/lib/seo";
import { AuthShell, GradientButton } from "@/components/auth/AuthShell";

const STEPS = [
  {
    icon: CheckCircle2,
    title: "Account Created",
    desc: "Your account has been successfully created and verified.",
  },
  {
    icon: Users,
    title: "Explore Features",
    desc: "Discover powerful AI agents and automation tools.",
  },
  {
    icon: Rocket,
    title: "Get Started",
    desc: "Launch your first agent and start scaling your business.",
  },
];

export default function Welcome() {
  useSEO({ title: "Welcome", description: "Your OraOne account is ready." });
  const nav = useNavigate();

  return (
    <AuthShell cardTestId="welcome-card">
      <div className="relative mx-auto grid size-20 place-items-center rounded-full bg-gradient-to-br from-[#EFF6FF] to-[#ECFEFF]">
        <PartyPopper size={34} className="text-[#2563EB]" />
      </div>

      <h1 className="mt-6 text-center text-3xl font-extrabold tracking-tight text-[#0F172A]">
        Welcome to OraOne! <span aria-hidden="true">🎉</span>
      </h1>
      <p className="mt-2 text-center text-sm leading-relaxed text-[#64748B]">
        Your account is all set up and you&apos;re ready to go.
        <br />
        Let&apos;s get you started on your automation journey.
      </p>

      <div className="mt-8 space-y-5 border-t border-[#EEF0F6] pt-6">
        {STEPS.map((s) => (
          <div key={s.title} className="flex items-start gap-3.5">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#EFF6FF] text-[#2563EB]">
              <s.icon size={19} />
            </span>
            <div>
              <p className="text-sm font-bold text-[#0F172A]">{s.title}</p>
              <p className="mt-0.5 text-xs leading-snug text-[#64748B]">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <GradientButton
          type="button"
          trailingIcon={ArrowRight}
          onClick={() => nav("/app/dashboard", { replace: true })}
          data-testid="welcome-dashboard"
        >
          Go to Dashboard
        </GradientButton>
      </div>

      <p className="mt-5 text-center text-sm text-[#64748B]">
        Need help getting started?{" "}
        <Link to="/docs" className="font-semibold text-[#2563EB] hover:underline">
          View Getting Started Guide
        </Link>
      </p>
    </AuthShell>
  );
}
