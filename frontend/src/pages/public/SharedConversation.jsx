import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Bot, User, Sparkles, MessageSquare, Loader2 } from "lucide-react";
import { API_BASE } from "@/lib/api";

/* Public, unauthenticated read-only transcript view (R1).
   Renders a conversation shared via /share/:token. No auth header is
   sent — the backend endpoint is intentionally public. */
export default function SharedConversation() {
  const { token } = useParams();
  const [state, setState] = useState({ loading: true, error: null, data: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/public/conversations/${token}`);
        if (!res.ok) throw new Error(res.status === 404 ? "This shared conversation is no longer available." : "Unable to load conversation.");
        const data = await res.json();
        if (!cancelled) setState({ loading: false, error: null, data });
      } catch (e) {
        if (!cancelled) setState({ loading: false, error: e.message, data: null });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      <header className="h-14 border-b border-[#E2E8F0] bg-white">
        <div className="max-w-3xl mx-auto h-full px-4 flex items-center justify-between">
          <Link to="/" className="inline-flex items-center gap-2 font-semibold text-[#0F172A]">
            <span className="size-7 rounded-lg bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] grid place-items-center text-white">
              <Sparkles size={15} />
            </span>
            OraOne
          </Link>
          <span className="text-[11px] px-2 py-1 rounded-full bg-[#F1F5F9] text-[#64748B]">Shared transcript</span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        {state.loading ? (
          <div className="grid place-items-center py-24 text-[#64748B]">
            <Loader2 size={26} className="animate-spin" />
          </div>
        ) : state.error ? (
          <div className="grid place-items-center py-24 text-center">
            <MessageSquare size={32} className="text-[#94A3B8]" />
            <p className="mt-3 text-sm text-[#334155]">{state.error}</p>
            <Link to="/" className="mt-4 text-sm font-semibold text-[#2563EB] hover:underline">
              Go to OraOne
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-6">
              <h1 className="text-xl font-bold text-[#0F172A]">{state.data.title || "Conversation"}</h1>
              <p className="mt-1 text-sm text-[#64748B]">
                {state.data.agent_name ? `with ${state.data.agent_name}` : "AI conversation"}
                {state.data.shared_at ? ` · shared ${new Date(state.data.shared_at).toLocaleDateString()}` : ""}
              </p>
            </div>

            <div className="space-y-4">
              {(state.data.messages || []).map((m, i) => {
                const isUser = m.role === "user";
                if (m.role === "system") {
                  return (
                    <div key={i} className="flex justify-center">
                      <span className="px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] text-[#64748B]">{m.content}</span>
                    </div>
                  );
                }
                return (
                  <div key={i} className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
                    <div
                      className={`size-8 rounded-lg grid place-items-center shrink-0 ${
                        isUser ? "bg-[#2563EB] text-white" : "bg-white border border-[#E2E8F0] text-[#2563EB]"
                      }`}
                    >
                      {isUser ? <User size={15} /> : <Bot size={15} />}
                    </div>
                    <div
                      className={`max-w-[78%] px-4 py-2.5 rounded-2xl text-sm whitespace-pre-wrap break-words ${
                        isUser
                          ? "bg-[#2563EB] text-white rounded-tr-sm"
                          : "bg-white border border-[#E2E8F0] text-[#0F172A] rounded-tl-sm"
                      }`}
                    >
                      {m.content}
                    </div>
                  </div>
                );
              })}
              {(state.data.messages || []).length === 0 && (
                <p className="text-center text-sm text-[#94A3B8] py-12">This conversation has no messages yet.</p>
              )}
            </div>

            <div className="mt-10 pt-6 border-t border-[#E2E8F0] text-center">
              <p className="text-xs text-[#94A3B8]">
                Powered by{" "}
                <Link to="/" className="font-semibold text-[#2563EB] hover:underline">
                  OraOne
                </Link>{" "}
                — build your own AI agents.
              </p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
