import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquare, ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { ONBOARDING } from "@/constants/testIds";

const AGENTS = [
  { id: "chat", title: "Chat Agent", desc: "Add a chatbot to my website", icon: MessageSquare, color: "#0891B2", testid: ONBOARDING.step1Chat },
];

export default function Step1Agent() {
  const nav = useNavigate();
  const [selected, setSelected] = useState(() => sessionStorage.getItem("onboard_agent") || "chat");

  const next = () => {
    sessionStorage.setItem("onboard_agent", selected);
    nav("/onboarding/business");
  };

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: "easeOut" }}>
      <h1 className="text-[2.75rem] leading-[1.05] font-bold tracking-tighter text-[#0F172A]">Welcome to OraOne! 👋</h1>
      <p className="mt-3 text-[15px] text-[#475569]">Let's set up your account in three simple steps.</p>
      <p className="mt-9 text-sm font-semibold text-[#0F172A]">What would you like to set up first?</p>

      <div className="mt-4 space-y-3.5">
        {AGENTS.map((a) => {
          const active = selected === a.id;
          return (
            <button
              key={a.id}
              data-testid={a.testid}
              onClick={() => setSelected(a.id)}
              className={`group w-full text-left p-5 rounded-2xl border-2 transition-all flex items-center gap-4 ${
                active
                  ? "border-[#2563EB] bg-[#EFF6FF] shadow-[0_8px_24px_-12px_rgba(37,99,235,0.45)]"
                  : "border-[#E9EDF3] bg-white hover:border-[#BFD3F5] hover:shadow-[0_6px_20px_-14px_rgba(15,23,42,0.35)]"
              }`}
            >
              <div
                className="size-14 rounded-2xl grid place-items-center flex-shrink-0 transition-colors"
                style={{ background: active ? a.color : `${a.color}14` }}
              >
                <a.icon size={24} style={{ color: active ? "#FFFFFF" : a.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-[15px] font-semibold text-[#0F172A]">{a.title}</p>
                  {a.recommended && (
                    <span className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full bg-[#ECFEFF] text-[#0891B2]">
                      Recommended
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-sm text-[#64748B]">{a.desc}</p>
              </div>
              <div className={`size-5 rounded-full border-2 transition-colors ${active ? "border-[#2563EB] bg-[#2563EB]" : "border-[#CBD5E1] group-hover:border-[#94A3B8]"} grid place-items-center`}>
                {active && <div className="size-2 rounded-full bg-white" />}
              </div>
            </button>
          );
        })}
      </div>

      <div className="mt-10 flex justify-end">
        <button
          onClick={next}
          data-testid={ONBOARDING.step1Next}
          className="inline-flex items-center gap-2 px-7 py-3 rounded-xl bg-gradient-to-r from-[#2563EB] to-[#06B6D4] text-white font-semibold text-sm shadow-[0_10px_24px_-10px_rgba(37,99,235,0.6)] hover:shadow-[0_12px_28px_-8px_rgba(37,99,235,0.7)] transition-shadow"
        >
          Continue <ArrowRight size={16} />
        </button>
      </div>
    </motion.div>
  );
}
