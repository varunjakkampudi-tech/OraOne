import React, { useEffect, useCallback, useRef, useId } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";
import { cx } from "./kit";
import { MOTION } from "@/constants/tokens";

const FOCUSABLE =
  'a[href],button:not([disabled]),textarea:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])';

/* ──────────────────────────────────────────────────────────────────────────
   Drawer — the universal right-side panel for OraOne.
   ONE implementation powers Create/Edit Agent, Conversation Details,
   Knowledge Document, Workflow, Integration, Team Member, etc.
   Every "detail / edit / create" interaction should open a Drawer instead
   of navigating to a bespoke page.
   ────────────────────────────────────────────────────────────────────────── */

const WIDTHS = {
  sm: "max-w-md",
  md: "max-w-xl",
  lg: "max-w-2xl",
  xl: "max-w-3xl",
};

export default function Drawer({
  open,
  onClose,
  title,
  description,
  icon: Icon,
  size = "md",
  footer,
  children,
  "data-testid": testId,
}) {
  const panelRef = useRef(null);
  const restoreRef = useRef(null);
  const reduceMotion = useReducedMotion();
  const titleId = useId();
  const descId = useId();

  const handleKey = useCallback(
    (e) => {
      if (e.key === "Escape") {
        onClose?.();
        return;
      }
      // Focus trap — keep Tab focus inside the drawer.
      if (e.key === "Tab" && panelRef.current) {
        const nodes = Array.from(
          panelRef.current.querySelectorAll(FOCUSABLE)
        ).filter((n) => n.offsetParent !== null);
        if (nodes.length === 0) return;
        const first = nodes[0];
        const last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (!open) return;
    // Remember what had focus so we can restore it on close.
    restoreRef.current = document.activeElement;
    document.addEventListener("keydown", handleKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    // Move focus into the panel after it mounts.
    const t = window.setTimeout(() => {
      const node = panelRef.current;
      if (!node) return;
      const target = node.querySelector(FOCUSABLE) || node;
      target.focus?.();
    }, 60);
    return () => {
      window.clearTimeout(t);
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = prev;
      // Restore focus to the trigger.
      const el = restoreRef.current;
      if (el && typeof el.focus === "function") el.focus();
    };
  }, [open, handleKey]);

  const overlayMotion = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: 0.1 } }
    : {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 },
        transition: { duration: MOTION.fast },
      };

  const panelAnim = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: 0.12 } }
    : {
        initial: { x: "100%" },
        animate: { x: 0 },
        exit: { x: "100%" },
        transition: { type: "tween", ease: MOTION.ease, duration: MOTION.slow },
      };

  return createPortal(
    <AnimatePresence>
      {open && (
        <div
          className="fixed inset-0 z-[70]"
          data-testid={testId}
          aria-modal="true"
          role="dialog"
          aria-labelledby={title ? titleId : undefined}
          aria-describedby={description ? descId : undefined}
        >
          <motion.div
            className="absolute inset-0 bg-[#0F172A]/40 backdrop-blur-[1px]"
            {...overlayMotion}
            onClick={onClose}
          />
          <motion.aside
            ref={panelRef}
            tabIndex={-1}
            className={cx(
              "absolute right-0 top-0 flex h-full w-full flex-col bg-white shadow-2xl outline-none",
              WIDTHS[size] || WIDTHS.md
            )}
            {...panelAnim}
          >
            {/* Header */}
            <div className="flex items-start gap-3 border-b border-line px-5 py-4">
              {Icon && (
                <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand">
                  <Icon size={19} />
                </span>
              )}
              <div className="min-w-0 flex-1">
                {title && (
                  <h2 id={titleId} className="truncate text-[16px] font-bold text-ink">
                    {title}
                  </h2>
                )}
                {description && (
                  <p id={descId} className="mt-0.5 text-[13px] text-sub">
                    {description}
                  </p>
                )}
              </div>
              <button
                onClick={onClose}
                aria-label="Close panel"
                className="grid size-9 shrink-0 place-items-center rounded-full text-sub transition-colors hover:bg-hairline hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
              >
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className="min-h-0 flex-1 overflow-y-auto scrollbar-thin px-5 py-5">{children}</div>

            {/* Footer */}
            {footer && (
              <div className="flex items-center justify-end gap-2 border-t border-line px-5 py-4">
                {footer}
              </div>
            )}
          </motion.aside>
        </div>
      )}
    </AnimatePresence>,
    document.body
  );
}
