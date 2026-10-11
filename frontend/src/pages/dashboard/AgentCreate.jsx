import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessageSquare, ArrowRight, ArrowLeft, Globe } from "lucide-react";
import { motion } from "framer-motion";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

const TYPES = [
  { id: "chat", label: "Chat Agent", desc: "AI chatbot for your website.", icon: MessageSquare, color: "#10B981" },
];

export default function AgentCreate() {
  const nav = useNavigate();
  const [type, setType] = useState("chat");
  const [website, setWebsite] = useState("");
  const [busy, setBusy] = useState(false);

  const next = async () => {
    setBusy(true);
    try {
      const site = website.trim();
      const { data } = await api.post("/agents", {
        type,
        name: "New Chat Agent",
        ...(site ? { website_url: site } : {}),
      });
      toast.success(
        site
          ? "Agent created — we're crawling your website into its knowledge now."
          : "Agent created. Configure it now."
      );
      nav(`/app/agents/${data.id}`);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <button onClick={() => nav("/app/agents")} className="text-sm text-[#64748B] hover:text-[#0F172A] inline-flex items-center gap-1.5 mb-4">
        <ArrowLeft size={14} /> Back to Agents
      </button>
      <h2 className="text-2xl font-bold tracking-tight text-[#0F172A]">Create New Agent</h2>
      <p className="text-sm text-[#64748B] mt-1">Select the type of agent you want to create.</p>

      <div className="mt-8 space-y-3">
        {TYPES.map((t) => (
          <motion.button
            key={t.id}
            whileTap={{ scale: 0.99 }}
            onClick={() => setType(t.id)}
            className={`w-full text-left p-5 rounded-2xl border-2 transition-all flex items-center gap-4 ${type === t.id ? "border-[#2563EB] bg-[#EFF6FF]" : "border-[#E2E8F0] bg-white hover:border-[#CBD5E1]"}`}
            data-testid={`agent-create-type-${t.id}`}
          >
            <div className="size-12 rounded-xl grid place-items-center" style={{ background: `${t.color}15` }}>
              <t.icon size={20} style={{ color: t.color }} />
            </div>
            <div className="flex-1">
              <p className="text-base font-semibold text-[#0F172A]">{t.label}</p>
              <p className="text-sm text-[#64748B]">{t.desc}</p>
            </div>
            <div className={`size-5 rounded-full border-2 ${type === t.id ? "border-[#2563EB] bg-[#2563EB]" : "border-[#CBD5E1]"} grid place-items-center`}>
              {type === t.id && <div className="size-2 rounded-full bg-white" />}
            </div>
          </motion.button>
        ))}
      </div>

      {/* Optional: seed the agent's knowledge by crawling a website up front. */}
      <div className="mt-6">
        <label htmlFor="agent-website" className="block text-sm font-semibold text-[#0F172A]">
          Website to learn from <span className="font-normal text-[#94A3B8]">(optional)</span>
        </label>
        <p className="text-sm text-[#64748B] mt-0.5">
          We'll crawl your site like a search bot and turn its pages into knowledge your agent can answer from.
        </p>
        <div className="mt-2 relative">
          <Globe size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
          <input
            id="agent-website"
            type="url"
            inputMode="url"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            placeholder="https://yourcompany.com"
            data-testid="agent-create-website"
            className="w-full rounded-xl border-2 border-[#E2E8F0] bg-white pl-9 pr-4 py-3 text-sm text-[#0F172A] placeholder:text-[#94A3B8] focus:border-[#2563EB] focus:outline-none"
          />
        </div>
      </div>

      <div className="mt-10 flex justify-between">
        <button onClick={() => nav("/app/agents")} className="px-5 py-3 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] text-sm font-semibold text-[#0F172A]">Cancel</button>
        <button onClick={next} disabled={busy} data-tour="pick-chat-type" className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold disabled:opacity-60" data-testid="agent-create-next">
          {busy ? "Creating..." : "Next"} <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
