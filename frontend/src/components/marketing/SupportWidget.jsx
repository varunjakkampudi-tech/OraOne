import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { MessageSquare, X, Send, BookOpen, Calendar, Mail, Check, Loader2 } from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { OraMark } from "@/components/marketing/Logo";

const SUPPORT_EMAIL = "sales@oraone.in";

/**
 * SupportWidget — the marketing site's own always-on help launcher.
 *
 * A self-contained bottom-right bubble that opens a support panel with quick
 * links and a message form. It posts to the public `/api/contact` endpoint, so
 * it works without any provisioned agent/widget and never leaves a dead 404 in
 * the console. (The customer-facing product embed lives in `public/widget.js`.)
 */
export default function SupportWidget() {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", email: "", message: "" });
  const panelRef = useRef(null);
  const firstFieldRef = useRef(null);

  // Escape-to-close + focus the first field when the panel opens.
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    const t = setTimeout(() => firstFieldRef.current?.focus(), 60);
    return () => {
      window.removeEventListener("keydown", onKey);
      clearTimeout(t);
    };
  }, [open]);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.message.trim()) {
      setError("Please fill in your name, email and message.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      await api.post("/contact", {
        name: form.name,
        email: form.email,
        message: form.message,
        type: "support",
      });
      setSent(true);
      setForm({ name: "", email: "", message: "" });
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || "Couldn't send — please email us instead.");
    } finally {
      setBusy(false);
    }
  };

  const QUICK = [
    { icon: Calendar, label: "Book a demo", to: "/contact" },
    { icon: BookOpen, label: "Read the docs", to: "/documentation" },
  ];

  return (
    <>
      <AnimatePresence>
        {open && (
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-label="OraOne support"
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className="fixed bottom-24 right-4 sm:right-5 z-[60] w-[calc(100vw-2rem)] max-w-[380px] overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white shadow-[0_24px_60px_-15px_rgba(15,23,42,0.35)]"
          >
            {/* Header */}
            <div className="relative bg-gradient-to-br from-[#2563EB] to-[#06B6D4] px-5 pt-5 pb-6 text-white">
              <button
                onClick={() => setOpen(false)}
                aria-label="Close support"
                className="absolute right-3 top-3 grid size-8 place-items-center rounded-lg text-white/80 hover:bg-white/15 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
              >
                <X size={18} />
              </button>
              <div className="flex items-center gap-2.5">
                <span className="grid size-9 place-items-center rounded-xl bg-white/15">
                  <OraMark size={22} light />
                </span>
                <div>
                  <p className="text-[15px] font-bold leading-tight">OraOne Support</p>
                  <p className="text-[12px] text-white/80">Typically replies within 24 hours</p>
                </div>
              </div>
            </div>

            {/* Body */}
            <div className="p-4">
              {sent ? (
                <div className="py-6 text-center" data-testid="support-sent">
                  <span className="mx-auto grid size-12 place-items-center rounded-full bg-[#DCFCE7] text-[#16A34A]">
                    <Check size={24} />
                  </span>
                  <p className="mt-3 text-[15px] font-semibold text-[#0F172A]">Message sent!</p>
                  <p className="mt-1 text-[13px] text-[#64748B]">
                    Thanks for reaching out — our team will get back to you within 24 hours.
                  </p>
                  <button
                    onClick={() => setSent(false)}
                    className="mt-4 text-[13px] font-semibold text-[#2563EB] hover:underline"
                  >
                    Send another message
                  </button>
                </div>
              ) : (
                <>
                  {/* Greeting bubble */}
                  <div className="mb-3 rounded-2xl rounded-tl-sm bg-[#F1F5F9] px-3.5 py-2.5 text-[13px] leading-relaxed text-[#334155]">
                    Hi there! 👋 How can we help? Send us a message and we'll reply by email, or use a
                    quick link below.
                  </div>

                  {/* Quick links */}
                  <div className="mb-3 grid grid-cols-2 gap-2">
                    {QUICK.map((q) => (
                      <Link
                        key={q.label}
                        to={q.to}
                        onClick={() => setOpen(false)}
                        className="flex items-center gap-2 rounded-xl border border-[#E2E8F0] px-3 py-2 text-[12.5px] font-semibold text-[#334155] transition-colors hover:border-[#2563EB]/40 hover:bg-[#F8FAFC] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563EB]/30"
                      >
                        <q.icon size={15} className="text-[#2563EB]" /> {q.label}
                      </Link>
                    ))}
                  </div>

                  {/* Message form */}
                  <form onSubmit={submit} className="space-y-2" data-testid="support-form">
                    <input
                      ref={firstFieldRef}
                      value={form.name}
                      onChange={(e) => update("name", e.target.value)}
                      placeholder="Your name"
                      aria-label="Your name"
                      className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-[13px] outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15"
                    />
                    <input
                      type="email"
                      value={form.email}
                      onChange={(e) => update("email", e.target.value)}
                      placeholder="Your email"
                      aria-label="Your email"
                      className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-[13px] outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15"
                    />
                    <textarea
                      value={form.message}
                      onChange={(e) => update("message", e.target.value)}
                      placeholder="How can we help?"
                      aria-label="Your message"
                      rows={3}
                      className="w-full resize-none rounded-xl border border-[#E2E8F0] px-3 py-2 text-[13px] outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15"
                    />
                    {error && <p className="text-[12px] text-[#DC2626]">{error}</p>}
                    <button
                      type="submit"
                      disabled={busy}
                      data-testid="support-send"
                      className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#2563EB] py-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-[#1D4ED8] disabled:opacity-60"
                    >
                      {busy ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                      {busy ? "Sending…" : "Send message"}
                    </button>
                  </form>

                  <a
                    href={`mailto:${SUPPORT_EMAIL}`}
                    className="mt-3 flex items-center justify-center gap-1.5 text-[12px] text-[#64748B] hover:text-[#2563EB]"
                  >
                    <Mail size={13} /> {SUPPORT_EMAIL}
                  </a>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Launcher bubble */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Close support chat" : "Open support chat"}
        aria-expanded={open}
        data-testid="support-launcher"
        className="fixed bottom-5 right-4 sm:right-5 z-[60] grid size-14 place-items-center rounded-full bg-gradient-to-br from-[#2563EB] to-[#06B6D4] text-white shadow-[0_12px_30px_-8px_rgba(37,99,235,0.6)] transition-transform hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#2563EB]/30"
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={open ? "x" : "chat"}
            initial={{ opacity: 0, rotate: -30, scale: 0.6 }}
            animate={{ opacity: 1, rotate: 0, scale: 1 }}
            exit={{ opacity: 0, rotate: 30, scale: 0.6 }}
            transition={{ duration: 0.15 }}
          >
            {open ? <X size={24} /> : <MessageSquare size={24} />}
          </motion.span>
        </AnimatePresence>
      </button>
    </>
  );
}
