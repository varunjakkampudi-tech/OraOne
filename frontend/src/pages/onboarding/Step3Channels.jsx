import React from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Globe, MessageCircle, ArrowLeft, CheckCircle2 } from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import { ONBOARDING } from "@/constants/testIds";

const CHANNELS = [
  { key: "website", label: "Website", desc: "Add website for chatbot", icon: Globe, testid: ONBOARDING.step3Website },
];

export default function Step3Channels() {
  const nav = useNavigate();
  const { refresh } = useAuth();

  const finish = async () => {
    const biz = JSON.parse(sessionStorage.getItem("onboard_business") || "{}");
    try {
      await api.post("/onboarding/complete", {
        company_name: biz.company_name || "My Business",
        industry: biz.industry || "Other",
        phone: biz.phone || null,
        website: biz.website || null,
        email: biz.email || null,
      });
      await refresh();
      toast.success("All set! Welcome to OraOne.");
      sessionStorage.removeItem("onboard_agent");
      sessionStorage.removeItem("onboard_business");
      nav("/app/dashboard");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Setup failed");
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <h1 className="text-4xl font-bold tracking-tighter text-[#0F172A]">Connect your channels</h1>
      <p className="mt-3 text-[#64748B]">Choose the channel you want to connect first. You can always add more later.</p>

      <div className="mt-8 space-y-3">
        {CHANNELS.map((c) => (
          <button key={c.key} data-testid={c.testid} className="w-full text-left p-5 rounded-2xl border border-[#E2E8F0] bg-white hover:border-[#2563EB]/30 hover:shadow-premium transition-all flex items-center gap-4">
            <div className="size-12 rounded-xl bg-[#EFF6FF] grid place-items-center flex-shrink-0">
              <c.icon size={20} className="text-[#2563EB]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-base font-semibold text-[#0F172A]">{c.label}</p>
              <p className="text-sm text-[#64748B]">{c.desc}</p>
            </div>
            <CheckCircle2 size={20} className="text-[#CBD5E1]" />
          </button>
        ))}
      </div>

      <div className="mt-10 flex justify-between items-center">
        <button onClick={() => nav("/onboarding/business")} className="inline-flex items-center gap-2 px-5 py-3 rounded-xl border border-[#E2E8F0] text-[#0F172A] font-semibold text-sm hover:bg-[#F8FAFC]">
          <ArrowLeft size={16} /> Back
        </button>
        <div className="flex items-center gap-3">
          <button onClick={finish} className="text-sm text-[#64748B] hover:text-[#0F172A]">I'll do this later</button>
          <button onClick={finish} data-testid={ONBOARDING.step3Finish} className="inline-flex items-center gap-2 px-7 py-3 rounded-xl bg-gradient-to-r from-[#2563EB] to-[#06B6D4] text-white font-semibold text-sm shadow-[0_10px_24px_-10px_rgba(37,99,235,0.6)] hover:shadow-[0_12px_28px_-8px_rgba(37,99,235,0.7)] transition-shadow">
            Complete Setup
          </button>
        </div>
      </div>
    </motion.div>
  );
}
