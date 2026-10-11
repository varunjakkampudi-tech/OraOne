import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X, ArrowRight, ArrowLeft } from "lucide-react";
import { useTour, TOUR_STEPS } from "@/lib/tour";

function useTargetRect(selector) {
  const [rect, setRect] = useState(null);
  useEffect(() => {
    if (!selector) {
      setRect(null);
      return undefined;
    }
    let raf;
    const measure = () => {
      const el = document.querySelector(`[data-tour="${selector}"]`);
      if (el && el.offsetParent !== null) {
        el.scrollIntoView({ block: "center", behavior: "smooth" });
        const r = el.getBoundingClientRect();
        setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
      } else {
        setRect(null);
      }
      raf = requestAnimationFrame(measure);
    };
    raf = requestAnimationFrame(measure);
    return () => cancelAnimationFrame(raf);
  }, [selector]);
  return rect;
}

export default function TourOverlay() {
  const { active, index, total, exit, next, back } = useTour();
  const nav = useNavigate();
  const { pathname } = useLocation();
  const step = active ? TOUR_STEPS[index] : null;
  const isLast = index === total - 1;
  const rect = useTargetRect(step?.target || null);

  // Drive the user through the app: whenever the step changes, navigate to
  // that step's page so they always see the screen it's describing.
  useEffect(() => {
    if (step?.route && pathname !== step.route) {
      nav(step.route);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, active]);

  if (!active || !step) return null;

  const showSpotlight = !!step.target && !!rect;

  const cardStyle = showSpotlight
    ? {
        position: "fixed",
        top: Math.min(rect.top + rect.height + 16, window.innerHeight - 240),
        left: Math.min(Math.max(rect.left, 16), window.innerWidth - 356),
        width: 340,
      }
    : {};

  const onCta = () => {
    exit();
    if (step.cta?.to) nav(step.cta.to);
  };

  return (
    <AnimatePresence>
      <motion.div
        key={step.id}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[70] pointer-events-none"
      >
        {/* Dimmer — a spotlight ring cuts a hole via box-shadow when a target
            exists; otherwise a plain full-screen dim for centered steps. */}
        {showSpotlight ? (
          <div
            className="fixed rounded-xl ring-4 ring-[#2563EB] pointer-events-none transition-all duration-300"
            style={{
              top: rect.top - 6,
              left: rect.left - 6,
              width: rect.width + 12,
              height: rect.height + 12,
              boxShadow: "0 0 0 9999px rgba(15,23,42,0.60)",
            }}
          />
        ) : (
          <div className="fixed inset-0 bg-[#0F172A]/60" />
        )}

        <motion.div
          key={`card-${step.id}`}
          initial={{ opacity: 0, y: 10, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          className={`pointer-events-auto rounded-2xl bg-white p-5 shadow-2xl ${
            showSpotlight ? "" : "fixed left-1/2 top-1/2 w-[92vw] max-w-md -translate-x-1/2 -translate-y-1/2"
          }`}
          style={showSpotlight ? cardStyle : undefined}
        >
          <div className="flex items-start justify-between gap-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-[#2563EB]">
              Step {index + 1} of {total}
            </p>
            <button onClick={exit} aria-label="Skip tour" className="text-[#94A3B8] hover:text-[#475569]">
              <X size={16} />
            </button>
          </div>

          <p className="mt-2 text-[16px] font-bold text-[#0F172A]">{step.title}</p>
          <p className="mt-1.5 text-[13px] leading-relaxed text-[#475569]">{step.body}</p>

          {/* Progress dots */}
          <div className="mt-4 flex items-center gap-1.5">
            {TOUR_STEPS.map((s, i) => (
              <span
                key={s.id}
                className={`h-1.5 rounded-full transition-all ${
                  i === index ? "w-5 bg-[#2563EB]" : i < index ? "w-1.5 bg-[#93C5FD]" : "w-1.5 bg-[#E2E8F0]"
                }`}
              />
            ))}
          </div>

          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={back}
              disabled={index === 0}
              className="inline-flex items-center gap-1 text-[12.5px] font-semibold text-[#64748B] hover:text-[#0F172A] disabled:opacity-0"
            >
              <ArrowLeft size={13} /> Back
            </button>

            <div className="flex items-center gap-2">
              {!isLast && (
                <button
                  onClick={exit}
                  className="rounded-full px-3 py-2 text-[12.5px] font-semibold text-[#94A3B8] hover:text-[#475569]"
                >
                  Skip
                </button>
              )}
              {isLast ? (
                <button
                  onClick={onCta}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[#2563EB] px-4 py-2 text-[12.5px] font-semibold text-white hover:bg-[#1D4ED8]"
                >
                  {step.cta?.label || "Finish"} <ArrowRight size={13} />
                </button>
              ) : (
                <button
                  onClick={next}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[#2563EB] px-4 py-2 text-[12.5px] font-semibold text-white hover:bg-[#1D4ED8]"
                  data-testid="tour-next"
                >
                  Next <ArrowRight size={13} />
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
