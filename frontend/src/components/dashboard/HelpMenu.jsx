import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  HelpCircle,
  Compass,
  Rocket,
  LifeBuoy,
  Ticket,
  Megaphone,
  Activity,
} from "lucide-react";
import { useTour } from "@/lib/tour";

// Resource links surfaced from the top bar so help is always one click away —
// and so the profile menu can stay focused on account/workspace actions.
const LINKS = [
  { icon: Rocket, label: "Getting started", to: "/app/getting-started" },
  { icon: LifeBuoy, label: "Help & docs", to: "/app/guide" },
  { icon: Ticket, label: "Support tickets", to: "/app/tickets" },
  { icon: Megaphone, label: "What's new", to: "/app/changelog" },
  { icon: Activity, label: "Product status", to: "/app/status" },
];

export default function HelpMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const nav = useNavigate();
  const { start } = useTour();

  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const go = (to) => {
    setOpen(false);
    nav(to);
  };

  const takeTour = () => {
    setOpen(false);
    start();
  };

  return (
    <div className="relative" ref={ref} data-testid="help-menu">
      <button
        onClick={() => setOpen((v) => !v)}
        className="grid size-9 place-items-center rounded-full text-[#64748B] hover:bg-[#F1F5F9] transition-colors"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Help and product tour"
        data-testid="help-menu-trigger"
      >
        <HelpCircle size={18} />
      </button>

      {open && (
        <div
          className="absolute right-0 top-[calc(100%+0.5rem)] z-50 w-64 overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white shadow-xl"
          role="menu"
          data-testid="help-menu-panel"
        >
          <div className="p-2">
            <button
              onClick={takeTour}
              className="flex w-full items-center gap-2.5 rounded-xl bg-[#F0F6FF] px-3 py-2.5 text-left text-[#2563EB] transition-colors hover:bg-[#E0EDFF]"
              role="menuitem"
              data-testid="help-take-tour"
            >
              <Compass size={17} />
              <div className="min-w-0">
                <p className="text-[13px] font-semibold">Take a tour</p>
                <p className="text-[11px] text-[#64748B]">A quick guided walkthrough</p>
              </div>
            </button>
          </div>
          <div className="border-t border-[#F1F5F9] p-2">
            {LINKS.map((l) => (
              <button
                key={l.to}
                onClick={() => go(l.to)}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-[13px] font-medium text-[#475569] transition-colors hover:bg-[#F8FAFC] hover:text-[#0F172A]"
                role="menuitem"
              >
                <l.icon size={15} className="text-[#94A3B8]" />
                {l.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
