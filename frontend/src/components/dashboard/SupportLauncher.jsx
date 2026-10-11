import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  MessageCircle,
  X,
  Send,
  Loader2,
  Sparkles,
  FileText,
  ShieldCheck,
  ThumbsUp,
  ThumbsDown,
  Rocket,
  LifeBuoy,
  Mail,
  Check,
} from "lucide-react";
import { api, API_BASE } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/**
 * SupportLauncher — OraOne dogfooding its own embeddable chat widget.
 *
 * This is the very same public widget runtime our customers embed on their
 * sites: it talks to the PUBLIC widget endpoints (/api/widget/config,
 * /api/widget/session, /api/widget/chat, /api/widget/feedback) using OraOne's
 * own "OraOne Support" widget public_key — no privileged API. The answers are
 * grounded in the OraOne Knowledge Base by the same RAG + reranker pipeline
 * customers get, so every OraOne customer has product support in-app. The key
 * is overridable via REACT_APP_ORAONE_SUPPORT_WIDGET_KEY.
 */

const SUPPORT_WIDGET_KEY =
  process.env.REACT_APP_ORAONE_SUPPORT_WIDGET_KEY ||
  "wgt_MpMxvc3_7QFIu0ugrlxQ1sPj";

const VISITOR_KEY = "oraone_support_visitor";

function newVisitorId() {
  const existing = localStorage.getItem(VISITOR_KEY);
  if (existing) return existing;
  const id = `v_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
  try {
    localStorage.setItem(VISITOR_KEY, id);
  } catch {
    /* ignore */
  }
  return id;
}

export default function SupportLauncher() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [config, setConfig] = useState(null); // { public_key, agent_name, settings }
  const [unavailable, setUnavailable] = useState(false);
  const [messages, setMessages] = useState([]); // { role, text, sources?, grounded?, confidence? }
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [booting, setBooting] = useState(false);
  // Fallback "contact us" form (used when there's no live AI support widget).
  const [fbMsg, setFbMsg] = useState("");
  const [fbBusy, setFbBusy] = useState(false);
  const [fbSent, setFbSent] = useState(false);
  const [fbErr, setFbErr] = useState("");
  const visitorId = useRef(newVisitorId());
  const scrollRef = useRef(null);
  const bootedRef = useRef(false);

  /* Load OraOne's own published support widget (once) via its public key. */
  const boot = useCallback(async () => {
    if (bootedRef.current) return;
    bootedRef.current = true;
    setBooting(true);
    try {
      // Pull the sanitized public config via the public surface.
      const res = await fetch(
        `${API_BASE}/widget/config?key=${encodeURIComponent(SUPPORT_WIDGET_KEY)}`
      );
      if (!res.ok) {
        setUnavailable(true);
        return;
      }
      const cfg = await res.json();
      setConfig(cfg);
      // Start a visitor session (restores prior transcript if any).
      try {
        const sres = await fetch(`${API_BASE}/widget/session`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            public_key: cfg.public_key,
            visitor_id: visitorId.current,
          }),
        });
        if (sres.ok) {
          const s = await sres.json();
          visitorId.current = s.visitor_id || visitorId.current;
          const prior = (s.messages || []).map((m) => ({
            role: m.role === "assistant" ? "agent" : "user",
            text: m.content,
          }));
          setMessages(
            prior.length
              ? prior
              : [
                  {
                    role: "agent",
                    text:
                      cfg.settings?.welcome_message ||
                      "Hi! How can I help you with OraOne?",
                  },
                ]
          );
        }
      } catch {
        setMessages([
          {
            role: "agent",
            text: cfg.settings?.welcome_message || "Hi! How can I help you with OraOne?",
          },
        ]);
      }
    } catch {
      setUnavailable(true);
    } finally {
      setBooting(false);
    }
  }, []);

  useEffect(() => {
    if (open) boot();
  }, [open, boot]);

  // Allow other parts of the app (e.g. the Customer Portal "Get help" action)
  // to open the support assistant via a window event.
  useEffect(() => {
    const openSupport = () => setOpen(true);
    window.addEventListener("oraone:open-support", openSupport);
    return () => window.removeEventListener("oraone:open-support", openSupport);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, open, sending]);

  const send = useCallback(
    async (text) => {
      const q = (text ?? input).trim();
      if (!q || sending || !config) return;
      setInput("");
      setMessages((m) => [...m, { role: "user", text: q }]);
      setSending(true);
      try {
        const res = await fetch(`${API_BASE}/widget/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            public_key: config.public_key,
            visitor_id: visitorId.current,
            message: q,
          }),
        });
        if (!res.ok) throw new Error("chat failed");
        const data = await res.json();
        setMessages((m) => [
          ...m,
          {
            role: "agent",
            text: data.answer,
            sources: data.sources || [],
            grounded: data.grounded,
            confidence: data.confidence,
            related: data.related_questions || [],
            messageId: data.message_id || null,
            feedback: null,
          },
        ]);
      } catch {
        setMessages((m) => [
          ...m,
          {
            role: "agent",
            text: "Sorry — I couldn't reach the assistant just now. Please try again.",
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [input, sending, config]
  );

  /* Was this answer helpful? — records CSAT via the public feedback endpoint. */
  const sendFeedback = useCallback(
    (index, helpful) => {
      setMessages((m) =>
        m.map((msg, i) =>
          i === index ? { ...msg, feedback: helpful ? "up" : "down" } : msg
        )
      );
      const msg = messages[index];
      if (!config) return;
      try {
        fetch(`${API_BASE}/widget/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            public_key: config.public_key,
            visitor_id: visitorId.current,
            message_id: msg?.messageId || undefined,
            rating: helpful ? 5 : 1,
          }),
        });
      } catch {
        /* best-effort */
      }
    },
    [messages, config]
  );

  const primary = config?.theme?.primary_color || "#2563EB";
  const suggestions = config?.settings?.suggested_questions || [];
  const showSuggestions = messages.length <= 1 && !sending;

  /* Fallback contact form — used when no live AI support widget is available,
     so in-app help never dead-ends. Posts to the public /contact endpoint. */
  const submitContact = useCallback(
    async (e) => {
      if (e) e.preventDefault();
      const message = fbMsg.trim();
      if (!message) { setFbErr("Please enter a message."); return; }
      setFbErr("");
      setFbBusy(true);
      try {
        await api.post("/contact", {
          name: user?.full_name || "OraOne user",
          email: user?.email || "support@oraone.in",
          message,
          type: "support",
        });
        setFbSent(true);
        setFbMsg("");
      } catch {
        setFbErr("Couldn't send — please email sales@oraone.in.");
      } finally {
        setFbBusy(false);
      }
    },
    [fbMsg, user]
  );

  return (
    <>
      {/* Launcher button */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        data-testid="support-launcher"
        aria-label="OraOne Support"
        className="fixed bottom-5 right-5 z-[60] flex h-14 w-14 items-center justify-center rounded-full text-white shadow-lg transition hover:scale-105 active:scale-95"
        style={{ backgroundColor: primary }}
      >
        <AnimatePresence mode="wait" initial={false}>
          {open ? (
            <motion.span key="x" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }}>
              <X size={22} />
            </motion.span>
          ) : (
            <motion.span key="chat" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }}>
              <MessageCircle size={24} />
            </motion.span>
          )}
        </AnimatePresence>
      </button>

      {/* Panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.97 }}
            transition={{ duration: 0.18 }}
            data-testid="support-panel"
            className="fixed bottom-24 right-5 z-[60] flex h-[560px] max-h-[calc(100vh-7rem)] w-[380px] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 text-white" style={{ backgroundColor: primary }}>
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20">
                <Sparkles size={18} />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold">{config?.agent_name || "OraOne Support"}</p>
                <p className="truncate text-[11px] text-white/80">{unavailable ? "Typically replies within 24 hours" : "Grounded in OraOne product knowledge"}</p>
              </div>
            </div>

            {/* Fallback: contact panel when there's no live AI support widget */}
            {unavailable && (
              <div className="flex-1 overflow-y-auto bg-[#F8FAFC] p-4 space-y-3" data-testid="support-fallback">
                {fbSent ? (
                  <div className="py-8 text-center">
                    <span className="mx-auto grid size-12 place-items-center rounded-full bg-[#DCFCE7] text-[#16A34A]"><Check size={24} /></span>
                    <p className="mt-3 text-sm font-semibold text-[#0F172A]">Message sent!</p>
                    <p className="mt-1 text-[12.5px] text-[#64748B]">Our team will get back to you within 24 hours.</p>
                  </div>
                ) : (
                  <>
                    <p className="text-[13px] text-[#475569]">Hi{user?.full_name ? ` ${user.full_name.split(" ")[0]}` : ""} 👋 How can we help? Send a message or explore these:</p>
                    <div className="space-y-2">
                      <Link to="/app/getting-started" onClick={() => setOpen(false)} className="flex items-center gap-2.5 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2.5 text-[13px] font-medium text-[#334155] transition hover:border-[#BFD3F5] hover:bg-[#EFF6FF]"><Rocket size={15} className="text-[#2563EB]" /> Getting started</Link>
                      <Link to="/app/guide" onClick={() => setOpen(false)} className="flex items-center gap-2.5 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2.5 text-[13px] font-medium text-[#334155] transition hover:border-[#BFD3F5] hover:bg-[#EFF6FF]"><LifeBuoy size={15} className="text-[#2563EB]" /> Help &amp; docs</Link>
                      <a href="mailto:sales@oraone.in" className="flex items-center gap-2.5 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2.5 text-[13px] font-medium text-[#334155] transition hover:border-[#BFD3F5] hover:bg-[#EFF6FF]"><Mail size={15} className="text-[#2563EB]" /> sales@oraone.in</a>
                    </div>
                    <form onSubmit={submitContact} className="space-y-2 pt-1">
                      <textarea value={fbMsg} onChange={(e) => setFbMsg(e.target.value)} rows={3} placeholder="Describe your question…" data-testid="support-fallback-input" className="w-full resize-none rounded-xl border border-[#E2E8F0] px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30" />
                      {fbErr && <p className="text-[12px] text-[#DC2626]">{fbErr}</p>}
                      <button type="submit" disabled={fbBusy} data-testid="support-fallback-send" className="w-full rounded-xl py-2.5 text-[13px] font-semibold text-white transition disabled:opacity-60" style={{ backgroundColor: primary }}>{fbBusy ? "Sending…" : "Send message"}</button>
                    </form>
                  </>
                )}
              </div>
            )}

            {/* Messages */}
            {!unavailable && (
            <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto bg-[#F8FAFC] p-4">
              {booting && (
                <div className="flex items-center justify-center py-10 text-[#94A3B8]">
                  <Loader2 className="animate-spin" size={20} />
                </div>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-[13px] leading-relaxed ${
                      m.role === "user"
                        ? "rounded-br-md bg-[#2563EB] text-white"
                        : "rounded-bl-md border border-[#E2E8F0] bg-white text-[#0F172A]"
                    }`}
                    style={m.role === "user" ? { backgroundColor: primary } : undefined}
                  >
                    <p className="whitespace-pre-wrap">{m.text}</p>
                    {m.role === "agent" && m.sources?.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {m.sources.slice(0, 4).map((s, j) => (
                          <span
                            key={j}
                            className="inline-flex items-center gap-1 rounded-full bg-[#EFF6FF] px-2 py-0.5 text-[10px] font-medium text-[#2563EB]"
                          >
                            <FileText size={10} />
                            {s.title || s.url || "Source"}
                          </span>
                        ))}
                        {typeof m.confidence === "number" && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-[#ECFDF5] px-2 py-0.5 text-[10px] font-medium text-[#047857]">
                            <ShieldCheck size={10} />
                            {Math.round(m.confidence * 100)}% match
                          </span>
                        )}
                      </div>
                    )}
                    {m.role === "agent" && i > 0 && (
                      <div
                        className="mt-2 flex items-center gap-1.5 border-t border-[#F1F5F9] pt-1.5"
                        data-testid={`support-feedback-${i}`}
                      >
                        {m.feedback ? (
                          <span className="text-[10px] font-medium text-[#16A34A]">
                            Thanks for the feedback!
                          </span>
                        ) : (
                          <>
                            <span className="text-[10px] text-[#94A3B8]">
                              Was this helpful?
                            </span>
                            <button
                              type="button"
                              onClick={() => sendFeedback(i, true)}
                              data-testid={`support-feedback-up-${i}`}
                              aria-label="Helpful"
                              className="flex h-6 w-6 items-center justify-center rounded-md text-[#94A3B8] transition hover:bg-[#ECFDF5] hover:text-[#047857]"
                            >
                              <ThumbsUp size={12} />
                            </button>
                            <button
                              type="button"
                              onClick={() => sendFeedback(i, false)}
                              data-testid={`support-feedback-down-${i}`}
                              aria-label="Not helpful"
                              className="flex h-6 w-6 items-center justify-center rounded-md text-[#94A3B8] transition hover:bg-[#FEF2F2] hover:text-[#DC2626]"
                            >
                              <ThumbsDown size={12} />
                            </button>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {sending && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-bl-md border border-[#E2E8F0] bg-white px-3.5 py-2.5">
                    <Loader2 className="animate-spin text-[#94A3B8]" size={14} />
                  </div>
                </div>
              )}

              {showSuggestions && suggestions.length > 0 && (
                <div className="space-y-1.5 pt-1" data-testid="support-suggestions">
                  {suggestions.slice(0, 3).map((s, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => send(s)}
                      className="block w-full truncate rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-left text-[12px] font-medium text-[#334155] transition hover:border-[#BFD3F5] hover:bg-[#EFF6FF]"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
            )}

            {/* Composer */}
            {!unavailable && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
              className="flex items-center gap-2 border-t border-[#E2E8F0] bg-white p-3"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={config?.settings?.input_placeholder || "Ask about OraOne…"}
                disabled={!config || sending}
                data-testid="support-input"
                className="flex-1 rounded-xl border border-[#E2E8F0] px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30 disabled:opacity-60"
              />
              <button
                type="submit"
                disabled={!input.trim() || sending || !config}
                data-testid="support-send"
                className="flex h-9 w-9 items-center justify-center rounded-xl text-white disabled:opacity-50"
                style={{ backgroundColor: primary }}
              >
                <Send size={16} />
              </button>
            </form>
            )}
            {!unavailable && config?.settings?.show_branding !== false && (
              <div className="bg-white pb-2 text-center text-[10px] text-[#94A3B8]">
                Powered by OraOne
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
