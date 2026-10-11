import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import { Cookie, Settings as SettingsIcon, X, Shield } from "lucide-react";
import { setConsent, getConsent } from "@/lib/analytics";

const STORAGE_KEY = "oraone_cookie_choice_v1";

const DEFAULT = {
  necessary: true,   // always on
  analytics: false,
  marketing: false,
  preferences: false,
};

const CATEGORIES = [
  {
    key: "necessary",
    title: "Strictly Necessary",
    desc: "Required for the site to function — authentication, session, security and load balancing. Cannot be disabled.",
    locked: true,
  },
  {
    key: "analytics",
    title: "Analytics & Performance",
    desc: "Help us understand how the site is used (page views, traffic sources, anonymised heatmaps) so we can improve it.",
  },
  {
    key: "marketing",
    title: "Marketing & Advertising",
    desc: "Used to measure ad effectiveness and show you relevant content across other sites.",
  },
  {
    key: "preferences",
    title: "Preferences",
    desc: "Remember your settings — preferred language, theme, region, last-used integration.",
  },
];

function readChoice() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveChoice(c) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...c, ts: Date.now() })); } catch { /* storage blocked */ }
  setConsent(c);
}

export default function CookieConsent() {
  const [open, setOpen] = useState(false);
  const [managing, setManaging] = useState(false);
  const [choices, setChoices] = useState(DEFAULT);

  useEffect(() => {
    const stored = readChoice();
    if (!stored) {
      // Defer 600ms so the page renders first
      const t = setTimeout(() => setOpen(true), 600);
      return () => clearTimeout(t);
    } else {
      setConsent(stored);
    }
  }, []);

  const acceptAll = () => {
    const all = { necessary: true, analytics: true, marketing: true, preferences: true };
    saveChoice(all);
    setOpen(false);
  };

  const rejectAll = () => {
    saveChoice({ ...DEFAULT, necessary: true });
    setOpen(false);
  };

  const saveChoices = () => {
    saveChoice(choices);
    setOpen(false);
    setManaging(false);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cookie-consent-title"
          aria-describedby="cookie-consent-desc"
          initial={{ y: 60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 60, opacity: 0 }}
          transition={{ type: "spring", stiffness: 220, damping: 26 }}
          className="fixed bottom-4 left-4 right-4 sm:left-6 sm:right-6 z-[9999]"
          data-testid="cookie-consent"
        >
          <div className="max-w-5xl mx-auto rounded-2xl bg-white border border-[#E2E8F0] shadow-[0_24px_64px_-12px_rgba(15,23,42,0.25)] overflow-hidden">
            {!managing ? (
              <div className="p-5 sm:p-6 flex flex-col lg:flex-row items-start lg:items-center gap-4">
                <div className="size-11 rounded-xl bg-[#EFF6FF] grid place-items-center flex-shrink-0">
                  <Cookie size={20} className="text-[#2563EB]" />
                </div>
                <div className="flex-1 min-w-0">
                  <h2 id="cookie-consent-title" className="text-[15px] font-bold text-[#0F172A]">
                    We value your privacy.
                  </h2>
                  <p id="cookie-consent-desc" className="mt-1 text-[13px] text-[#475569] leading-relaxed">
                    OraOne uses cookies to keep the site running, remember your preferences and (with your consent) understand how it&apos;s used. Read our{" "}
                    <Link to="/cookie-policy" className="text-[#2563EB] hover:underline font-medium">Cookie Policy</Link>{" "}
                    or{" "}
                    <Link to="/privacy" className="text-[#2563EB] hover:underline font-medium">Privacy Policy</Link>.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
                  <button
                    onClick={() => setManaging(true)}
                    data-testid="cookie-manage"
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[#E2E8F0] hover:border-[#2563EB] hover:text-[#2563EB] text-[#0F172A] text-[13px] font-semibold transition-colors"
                  >
                    <SettingsIcon size={13} /> Manage
                  </button>
                  <button
                    onClick={rejectAll}
                    data-testid="cookie-reject-all"
                    className="px-3 py-2 rounded-xl border border-[#E2E8F0] hover:border-[#2563EB] hover:text-[#2563EB] text-[#0F172A] text-[13px] font-semibold transition-colors"
                  >
                    Reject All
                  </button>
                  <button
                    onClick={acceptAll}
                    data-testid="cookie-accept-all"
                    className="px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-semibold shadow-[0_8px_20px_-6px_rgba(37,99,235,0.5)] transition-colors"
                  >
                    Accept All
                  </button>
                </div>
              </div>
            ) : (
              <ManagePanel
                choices={choices}
                setChoices={setChoices}
                onCancel={() => setManaging(false)}
                onSave={saveChoices}
                onReject={rejectAll}
                onAccept={acceptAll}
              />
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/** Tiny floating "Cookie Settings" button — surfaces once a choice has been saved. */
export function CookieSettingsTrigger() {
  const [show, setShow] = useState(false);
  const [reopen, setReopen] = useState(false);

  useEffect(() => {
    setShow(!!readChoice());
  }, []);

  if (!show || reopen) return null;
  return (
    <button
      onClick={() => {
        try { localStorage.removeItem(STORAGE_KEY); } catch { /* storage blocked */ }
        setReopen(true);
        window.location.reload();
      }}
      data-testid="cookie-settings-trigger"
      className="fixed bottom-4 left-4 z-[100] size-10 rounded-full bg-white border border-[#E2E8F0] shadow-md hover:shadow-lg grid place-items-center text-[#2563EB] hover:bg-[#EFF6FF] transition-all"
      aria-label="Cookie preferences"
      title="Cookie preferences"
    >
      <Cookie size={16} />
    </button>
  );
}

function ManagePanel({ choices, setChoices, onCancel, onSave, onReject, onAccept }) {
  return (
    <div>
      <div className="px-5 py-4 sm:px-6 border-b border-[#E2E8F0] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="size-9 rounded-xl bg-[#EFF6FF] grid place-items-center">
            <Shield size={16} className="text-[#2563EB]" />
          </div>
          <div>
            <h2 className="text-[15px] font-bold text-[#0F172A]">Cookie Preferences</h2>
            <p className="text-[11.5px] text-[#64748B]">Choose which cookies you&apos;d like to allow.</p>
          </div>
        </div>
        <button
          onClick={onCancel}
          className="text-[#94A3B8] hover:text-[#0F172A]"
          aria-label="Close preferences"
          data-testid="cookie-manage-close"
        >
          <X size={18} />
        </button>
      </div>
      <div className="px-5 py-4 sm:px-6 sm:py-5 space-y-3 max-h-[60vh] overflow-y-auto">
        {CATEGORIES.map((c) => (
          <label
            key={c.key}
            htmlFor={`cookie-cat-${c.key}`}
            className="flex items-start gap-3 p-3 rounded-xl border border-[#E2E8F0] hover:border-[#2563EB]/30 cursor-pointer"
          >
            <input
              id={`cookie-cat-${c.key}`}
              type="checkbox"
              checked={c.locked ? true : !!choices[c.key]}
              disabled={c.locked}
              onChange={(e) => !c.locked && setChoices((s) => ({ ...s, [c.key]: e.target.checked }))}
              data-testid={`cookie-cat-${c.key}`}
              className="mt-1 size-4 accent-[#2563EB] disabled:opacity-60"
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-[13.5px] font-semibold text-[#0F172A]">{c.title}</p>
                {c.locked && (
                  <span className="text-[10px] font-bold tracking-wider text-[#475569] bg-[#F1F5F9] px-1.5 py-0.5 rounded-full">
                    ALWAYS ON
                  </span>
                )}
              </div>
              <p className="text-[12.5px] text-[#64748B] mt-1 leading-snug">{c.desc}</p>
            </div>
          </label>
        ))}
      </div>
      <div className="px-5 py-4 sm:px-6 bg-[#F8FAFC] border-t border-[#E2E8F0] flex flex-wrap gap-2 justify-end">
        <button
          onClick={onReject}
          data-testid="cookie-reject-all-manage"
          className="px-3 py-2 rounded-xl border border-[#E2E8F0] hover:border-[#2563EB] hover:text-[#2563EB] text-[#0F172A] text-[13px] font-semibold"
        >
          Reject All
        </button>
        <button
          onClick={onSave}
          data-testid="cookie-save-choices"
          className="px-3 py-2 rounded-xl border border-[#E2E8F0] hover:border-[#2563EB] hover:text-[#2563EB] text-[#0F172A] text-[13px] font-semibold"
        >
          Save Choices
        </button>
        <button
          onClick={onAccept}
          data-testid="cookie-accept-all-manage"
          className="px-4 py-2 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13px] font-semibold shadow-[0_8px_20px_-6px_rgba(37,99,235,0.5)]"
        >
          Accept All
        </button>
      </div>
    </div>
  );
}
