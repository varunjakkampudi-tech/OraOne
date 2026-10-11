import React from "react";
import { Phone, MessageCircle, MessageSquare, Calendar } from "lucide-react";
import { motion } from "framer-motion";
import { OraMark } from "@/components/marketing/Logo";
import SimpleIcon from "@/components/ui/SimpleIcon";

/**
 * Hero Orb — large OraOne brand mark surrounded by 6 channel icons on
 * concentric dashed rings, with an audio-waveform halo behind the mark.
 *
 * Matches the user-supplied reference: white background, soft lavender halos,
 * brand-coloured icon tiles around the orb, animated audio bars.
 */
export default function HeroOrb() {
  return (
    <div className="relative w-full aspect-square max-w-[560px] mx-auto select-none">
      {/* Concentric rings */}
      <svg className="absolute inset-0" viewBox="0 0 400 400" fill="none" aria-hidden="true">
        <defs>
          <radialGradient id="orbRingFill" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#EEF2FF" stopOpacity="0.8" />
            <stop offset="60%" stopColor="#EEF2FF" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#EEF2FF" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="200" cy="200" r="172" fill="url(#orbRingFill)" />
        <circle cx="200" cy="200" r="172" stroke="#C7D2FE" strokeWidth="1" strokeDasharray="3 5" opacity="0.55" />
        <circle cx="200" cy="200" r="130" stroke="#C7D2FE" strokeWidth="1" opacity="0.55" />
        <circle cx="200" cy="200" r="88" stroke="#C7D2FE" strokeWidth="1" strokeDasharray="2 4" opacity="0.55" />
      </svg>

      {/* Audio waveform behind the brand mark */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="flex items-center gap-[3px] w-[78%]" aria-hidden="true">
          {Array.from({ length: 56 }).map((_, i) => {
            // Symmetric envelope — taller in the middle, smaller at the edges.
            const envelope = Math.sin((i / 55) * Math.PI);
            const seed = ((i * 37) % 13) / 13; // pseudo-random per bar
            const baseHeight = 8 + envelope * 70 + seed * 18;
            return (
              <motion.span
                key={i}
                className="block flex-1 rounded-full"
                style={{
                  background: "linear-gradient(180deg, #3B82F6, #06B6D4)",
                  opacity: 0.55 + envelope * 0.35,
                }}
                animate={{ height: [`${baseHeight * 0.6}px`, `${baseHeight}px`, `${baseHeight * 0.6}px`] }}
                transition={{
                  duration: 1.1 + (i % 5) * 0.12,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: i * 0.025,
                }}
              />
            );
          })}
        </div>
      </div>

      {/* Channel icons positioned on the rings */}
      <FloatIcon top="22%" left="14%" color="#2563EB" bg="#FFFFFF" delay={0.15}>
        <Phone size={22} />
      </FloatIcon>
      <FloatIcon top="22%" left="86%" color="#7C3AED" bg="#FFFFFF" delay={0.3}>
        <MessageSquare size={22} />
      </FloatIcon>
      <FloatIcon top="78%" left="14%" color="#7C3AED" bg="#FFFFFF" delay={0.45}>
        <Calendar size={22} />
      </FloatIcon>
      <FloatIcon top="78%" left="86%" color="#4F46E5" bg="#FFFFFF" delay={0.6}>
        <Calendar size={22} />
      </FloatIcon>
      <FloatIcon top="50%" left="98%" color="#06B6D4" bg="#FFFFFF" delay={0.75}>
        <MessageCircle size={22} />
      </FloatIcon>

      {/* Centre — brand orb (logo placeholder) */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <motion.div
          animate={{ scale: [1, 1.04, 1] }}
          transition={{ duration: 3.6, repeat: Infinity, ease: "easeInOut" }}
        >
          <div
            className="relative size-44 sm:size-52 rounded-full grid place-items-center"
            style={{
              background:
                "radial-gradient(circle at 50% 40%, #DBEAFE 0%, #EEF2FF 55%, transparent 80%)",
            }}
          >
            <div
              className="relative size-36 sm:size-44 rounded-full overflow-hidden grid place-items-center"
              style={{
                boxShadow:
                  "0 22px 60px -12px rgba(37,99,235,0.35), inset 0 0 0 1px rgba(255,255,255,0.5)",
                background: "linear-gradient(135deg, #EFF6FF 0%, #FFFFFF 100%)",
              }}
            >
              <OraMark size={104} className="sm:hidden" />
              <OraMark size={128} className="hidden sm:block" />
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

function FloatIcon({ top, left, color, bg, delay, children }) {
  return (
    <motion.div
      className="absolute size-12 sm:size-14 rounded-2xl grid place-items-center shadow-premium border border-[#E2E8F0]"
      style={{ top, left, transform: "translate(-50%, -50%)", background: bg }}
      animate={{ y: [0, -8, 0] }}
      transition={{ duration: 3.6, repeat: Infinity, ease: "easeInOut", delay }}
    >
      <span style={{ color }}>{children}</span>
    </motion.div>
  );
}
