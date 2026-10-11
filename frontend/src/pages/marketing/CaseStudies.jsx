import React from "react";
import { motion } from "framer-motion";
import { useSEO } from "@/lib/seo";

const cases = [
  { name: "Multi-location Dental Group", industry: "Healthcare", result: "80% fewer missed appointments", quote: "The AI books and reminds patients around the clock — our front desk finally has room to breathe." },
  { name: "Real Estate Brokerage", industry: "Real Estate", result: "3× more qualified leads in 60 days", quote: "Our agents now spend their time only on leads that are ready to talk." },
  { name: "Auto Service Center", industry: "Automotive", result: "Support workload cut with AI", quote: "Customers get instant replies, day or night — and they love it." },
  { name: "Growing Dental Practice", industry: "Healthcare", result: "24/7 appointment booking", quote: "It's the best-performing addition to our front office this year." },
];

export default function CaseStudiesPage() {
  useSEO({ title: "Case Studies", description: "How businesses use OraOne to scale customer conversations across industries." });
  return (
    <div>
      <section className="bg-[#F8FAFC] py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tighter text-[#0F172A]">Case Studies</h1>
          <p className="mt-4 text-[#64748B] max-w-2xl mx-auto">Representative outcomes for teams putting OraOne to work across industries.</p>
        </div>
      </section>
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid md:grid-cols-2 gap-6">
          {cases.map((c, i) => (
            <motion.div key={c.name} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.06 }} className="p-8 rounded-3xl bg-white border border-[#E2E8F0] hover:shadow-premium transition-all">
              <div className="flex items-center gap-3 mb-4">
                <div className="size-10 rounded-xl gradient-bg grid place-items-center text-white font-bold">{c.name.slice(0, 1)}</div>
                <div>
                  <p className="text-lg font-semibold text-[#0F172A]">{c.name}</p>
                  <p className="text-xs text-[#64748B]">{c.industry}</p>
                </div>
              </div>
              <p className="text-2xl font-bold text-[#2563EB] tracking-tight">{c.result}</p>
              <p className="mt-4 text-[#64748B] italic">"{c.quote}"</p>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
