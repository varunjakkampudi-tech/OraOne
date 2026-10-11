import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Plus,
  Sparkles,
  Send,
  Trash2,
  Pencil,
  Check,
  X,
  Bot,
  User,
  BookOpen,
  ChevronDown,
  FileText,
  Loader2,
  MessageSquarePlus,
  MessageCircle,
  Pin,
  Star,
  Archive,
  Share2,
  Download,
  MoreVertical,
  Search,
  RefreshCw,
  Lightbulb,
} from "lucide-react";
import { toast } from "sonner";
import { api, API_BASE, getToken } from "@/lib/api";
import { CHAT } from "@/constants/testIds";

/* ----------------------------- helpers ----------------------------- */

const AGENT_ICON = {
  chat: Sparkles,
  whatsapp: MessageCircle,
};

/* Minimal, dependency-free Markdown → React renderer for assistant
   messages. Supports headings, bold/italic, inline + fenced code,
   bullet/numbered lists, links, and paragraphs. Plain text is safe —
   everything is rendered as React text nodes (no dangerouslySetInnerHTML). */
function renderInline(text, keyPrefix = "i") {
  const nodes = [];
  // Order matters: code first so ** inside code isn't bolded.
  const regex = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*]+\*)|(\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m;
  let k = 0;
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("`")) {
      nodes.push(
        <code key={`${keyPrefix}-c-${k}`} className="px-1.5 py-0.5 rounded bg-[#F1F5F9] text-[#0F172A] text-[12.5px] font-mono">
          {tok.slice(1, -1)}
        </code>
      );
    } else if (tok.startsWith("**")) {
      nodes.push(<strong key={`${keyPrefix}-b-${k}`}>{tok.slice(2, -2)}</strong>);
    } else if (tok.startsWith("*")) {
      nodes.push(<em key={`${keyPrefix}-i-${k}`}>{tok.slice(1, -1)}</em>);
    } else if (tok.startsWith("[")) {
      const mm = /\[([^\]]+)\]\(([^)]+)\)/.exec(tok);
      if (mm) {
        nodes.push(
          <a key={`${keyPrefix}-a-${k}`} href={mm[2]} target="_blank" rel="noopener noreferrer" className="text-[#2563EB] underline break-all">
            {mm[1]}
          </a>
        );
      }
    }
    last = m.index + tok.length;
    k++;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function renderMarkdown(src) {
  if (!src) return null;
  const lines = String(src).replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let i = 0;
  let bi = 0;
  while (i < lines.length) {
    const line = lines[i];
    // fenced code block
    if (line.trim().startsWith("```")) {
      const code = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        code.push(lines[i]);
        i++;
      }
      i++; // skip closing fence
      blocks.push(
        <pre key={`blk-${bi++}`} className="my-1.5 p-3 rounded-lg bg-[#0F172A] text-[#E2E8F0] text-[12.5px] font-mono overflow-x-auto">
          <code>{code.join("\n")}</code>
        </pre>
      );
      continue;
    }
    // heading
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) {
      const lvl = h[1].length;
      const cls = lvl <= 1 ? "text-base font-bold" : lvl === 2 ? "text-[15px] font-bold" : "text-sm font-semibold";
      blocks.push(<div key={`blk-${bi++}`} className={`${cls} mt-1.5 mb-0.5 text-[#0F172A]`}>{renderInline(h[2], `h${bi}`)}</div>);
      i++;
      continue;
    }
    // list (bullet or numbered) — gather consecutive items
    if (/^\s*([-*+]|\d+\.)\s+/.test(line)) {
      const items = [];
      const ordered = /^\s*\d+\.\s+/.test(line);
      while (i < lines.length && /^\s*([-*+]|\d+\.)\s+/.test(lines[i])) {
        const txt = lines[i].replace(/^\s*([-*+]|\d+\.)\s+/, "");
        items.push(<li key={`li-${bi}-${items.length}`} className="ml-1">{renderInline(txt, `l${bi}-${items.length}`)}</li>);
        i++;
      }
      blocks.push(
        ordered ? (
          <ol key={`blk-${bi++}`} className="my-1 ml-4 list-decimal space-y-0.5">{items}</ol>
        ) : (
          <ul key={`blk-${bi++}`} className="my-1 ml-4 list-disc space-y-0.5">{items}</ul>
        )
      );
      continue;
    }
    // blank line
    if (line.trim() === "") {
      i++;
      continue;
    }
    // paragraph — gather until blank/structural line
    const para = [line];
    i++;
    while (i < lines.length && lines[i].trim() !== "" && !/^\s*([-*+]|\d+\.)\s+/.test(lines[i]) && !/^#{1,4}\s/.test(lines[i]) && !lines[i].trim().startsWith("```")) {
      para.push(lines[i]);
      i++;
    }
    blocks.push(<p key={`blk-${bi++}`} className="my-0.5 leading-relaxed">{renderInline(para.join(" "), `p${bi}`)}</p>);
  }
  return blocks;
}

function relativeTime(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Math.max(0, Date.now() - then);
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

let _tmpSeq = 0;
const tmpId = () => `tmp-${Date.now()}-${_tmpSeq++}`;

/* Parse a chunk of an SSE byte stream into discrete {event, data} frames.
   Returns [frames, remainingBuffer]. Frames are separated by a blank line. */
function parseSSE(buffer) {
  const frames = [];
  let rest = buffer;
  let idx;
  while ((idx = rest.indexOf("\n\n")) !== -1) {
    const raw = rest.slice(0, idx);
    rest = rest.slice(idx + 2);
    let event = "message";
    const dataLines = [];
    for (const line of raw.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (dataLines.length) {
      let data = {};
      try {
        data = JSON.parse(dataLines.join("\n"));
      } catch {
        data = { raw: dataLines.join("\n") };
      }
      frames.push({ event, data });
    }
  }
  return [frames, rest];
}

/* ------------------------------ page ------------------------------- */

export default function Chat() {
  const { conversationId } = useParams();
  const nav = useNavigate();

  const [conversations, setConversations] = useState([]);
  const [agents, setAgents] = useState([]);
  const [messages, setMessages] = useState([]);
  const [activeConv, setActiveConv] = useState(null);

  const [loadingConvs, setLoadingConvs] = useState(true);
  const [loadingThread, setLoadingThread] = useState(false);
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState("");

  const [input, setInput] = useState("");
  const [useKnowledge, setUseKnowledge] = useState(true);
  const [showPicker, setShowPicker] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState("");

  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("active"); // active | favorites | archived
  const [menuFor, setMenuFor] = useState(null); // conversation id whose menu is open
  const [suggested, setSuggested] = useState([]);
  const [regenerating, setRegenerating] = useState(false);

  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);

  /* ---------- data loaders ---------- */

  const loadConversations = useCallback(async () => {
    try {
      const params = { sort: "recent", limit: 100 };
      if (search.trim()) params.q = search.trim();
      if (filter === "favorites") params.favorite = true;
      if (filter === "archived") params.archived = true;
      else params.archived = false;
      const { data } = await api.get("/conversations", { params });
      setConversations(Array.isArray(data) ? data : []);
    } catch {
      setConversations([]);
    } finally {
      setLoadingConvs(false);
    }
  }, [search, filter]);

  const loadAgents = useCallback(async () => {
    try {
      const { data } = await api.get("/agents");
      const list = Array.isArray(data) ? data : data?.items || [];
      setAgents(list);
    } catch {
      setAgents([]);
    }
  }, []);

  const loadThread = useCallback(
    async (id) => {
      if (!id) {
        setActiveConv(null);
        setMessages([]);
        return;
      }
      setLoadingThread(true);
      try {
        const [{ data: conv }, { data: msgs }] = await Promise.all([
          api.get(`/conversations/${id}`),
          api.get(`/conversations/${id}/messages`),
        ]);
        setActiveConv(conv);
        setMessages(Array.isArray(msgs) ? msgs : []);
      } catch (err) {
        if (err.response?.status === 404) {
          toast.error("Conversation not found.");
          nav("/app/chat", { replace: true });
        } else {
          toast.error("Failed to load conversation.");
        }
        setActiveConv(null);
        setMessages([]);
      } finally {
        setLoadingThread(false);
      }
    },
    [nav]
  );

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    const t = setTimeout(() => loadConversations(), 250);
    return () => clearTimeout(t);
  }, [loadConversations]);

  useEffect(() => {
    loadThread(conversationId);
    // cancel any in-flight stream when switching threads
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
    };
  }, [conversationId, loadThread]);

  /* keep the thread pinned to the newest message */
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, streamingText]);

  /* ---------- new conversation ---------- */

  const startConversation = useCallback(
    async (agent) => {
      setShowPicker(false);
      try {
        const { data } = await api.post("/conversations", { agent_id: agent.id });
        setConversations((prev) => [data, ...prev]);
        nav(`/app/chat/${data.id}`);
      } catch {
        toast.error("Could not start a conversation.");
      }
    },
    [nav]
  );

  const onNewChat = () => {
    if (agents.length === 0) {
      toast.error("Create an agent first to start chatting.");
      nav("/app/agents/new");
      return;
    }
    if (agents.length === 1) {
      startConversation(agents[0]);
      return;
    }
    setShowPicker(true);
  };

  /* ---------- send (streaming) ---------- */

  const finalizeAssistant = useCallback(
    (text, meta) => {
      setMessages((prev) => {
        const next = prev.filter((m) => !m._streaming);
        next.push({
          id: meta?.message_id || tmpId(),
          conversation_id: conversationId,
          role: "assistant",
          content: text,
          token_count: meta?.usage?.total_tokens ?? null,
          metadata: {
            context_used: meta?.context_used ?? 0,
            sources: Array.isArray(meta?.sources) ? meta.sources : [],
          },
          created_at: new Date().toISOString(),
        });
        return next;
      });
      setStreamingText("");
    },
    [conversationId]
  );

  const sendMessage = useCallback(async (override) => {
    const content = (typeof override === "string" ? override : input).trim();
    if (!content || sending || !conversationId) return;

    setInput("");
    setSending(true);
    setStreamingText("");
    setSuggested([]);

    const optimisticUser = {
      id: tmpId(),
      conversation_id: conversationId,
      role: "user",
      content,
      created_at: new Date().toISOString(),
      _optimistic: true,
    };
    setMessages((prev) => [...prev, optimisticUser]);

    const controller = new AbortController();
    abortRef.current = controller;

    let acc = "";
    let streamedAny = false;
    let doneReceived = false;

    try {
      const res = await fetch(`${API_BASE}/conversations/${conversationId}/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken() || ""}`,
        },
        body: JSON.stringify({ content, use_knowledge: useKnowledge }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        let detail = `Request failed (${res.status}).`;
        try {
          const j = await res.json();
          detail = j?.detail?.message || j?.detail || detail;
        } catch {
          /* ignore parse failure */
        }
        throw new Error(detail);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const [frames, rest] = parseSSE(buf);
        buf = rest;
        for (const { event, data } of frames) {
          if (event === "token") {
            streamedAny = true;
            acc += data.delta || "";
            setStreamingText(acc);
          } else if (event === "done") {
            doneReceived = true;
            const finalText = data.content || acc;
            finalizeAssistant(finalText, data);
            if (data.title) {
              setActiveConv((c) => (c ? { ...c, title: data.title } : c));
            }
          } else if (event === "error") {
            throw new Error(data.message || "The assistant failed to respond.");
          }
        }
      }

      // safety: stream closed without an explicit "done" frame
      if (!doneReceived && acc) {
        finalizeAssistant(acc, {});
      }
    } catch (err) {
      if (err.name === "AbortError") {
        // thread switched mid-stream — drop the partial assistant bubble
        setMessages((prev) => prev.filter((m) => !m._streaming));
      } else {
        toast.error(err.message || "Failed to send message.");
        // drop optimistic user + any partial assistant; restore input
        setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id && !m._streaming));
        setInput(content);
      }
      setStreamingText("");
    } finally {
      abortRef.current = null;
      setSending(false);
      // refresh thread + list to reconcile persisted state / ordering / title
      if (!controller.signal.aborted) {
        loadConversations();
        if (!streamedAny) {
          // nothing streamed (e.g., error before tokens) — re-pull to be safe
          loadThread(conversationId);
        }
      }
      inputRef.current?.focus();
    }
  }, [input, sending, conversationId, useKnowledge, finalizeAssistant, loadConversations, loadThread]);

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  /* ---------- rename / delete ---------- */

  const beginRename = () => {
    setRenameValue(activeConv?.title || "");
    setRenaming(true);
  };

  const commitRename = async () => {
    const title = renameValue.trim();
    if (!title || title === activeConv?.title) {
      setRenaming(false);
      return;
    }
    try {
      const { data } = await api.put(`/conversations/${activeConv.id}`, { title });
      setActiveConv(data);
      setConversations((prev) => prev.map((c) => (c.id === data.id ? { ...c, title: data.title } : c)));
      toast.success("Renamed");
    } catch {
      toast.error("Rename failed.");
    } finally {
      setRenaming(false);
    }
  };

  const deleteConversation = async (conv, e) => {
    e?.stopPropagation();
    e?.preventDefault();
    if (!window.confirm(`Delete "${conv.title || "this conversation"}"?`)) return;
    try {
      await api.delete(`/conversations/${conv.id}`);
      setConversations((prev) => prev.filter((c) => c.id !== conv.id));
      toast.success("Conversation deleted");
      if (conv.id === conversationId) nav("/app/chat", { replace: true });
    } catch {
      toast.error("Delete failed.");
    }
  };

  /* ---------- R1: organization actions ---------- */

  const patchConversation = useCallback(
    async (id, body, { silent } = {}) => {
      try {
        const { data } = await api.patch(`/conversations/${id}`, body);
        setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, ...data } : c)));
        setActiveConv((c) => (c && c.id === id ? { ...c, ...data } : c));
        return data;
      } catch {
        if (!silent) toast.error("Update failed.");
        return null;
      }
    },
    []
  );

  const togglePin = async (conv, e) => {
    e?.stopPropagation();
    const data = await patchConversation(conv.id, { is_pinned: !conv.is_pinned });
    if (data) toast.success(data.is_pinned ? "Pinned" : "Unpinned");
  };

  const toggleFavorite = async (conv, e) => {
    e?.stopPropagation();
    const data = await patchConversation(conv.id, { is_favorite: !conv.is_favorite });
    if (data) toast.success(data.is_favorite ? "Added to favorites" : "Removed from favorites");
  };

  const toggleArchive = async (conv, e) => {
    e?.stopPropagation();
    const data = await patchConversation(conv.id, { is_archived: !conv.is_archived });
    if (data) {
      toast.success(data.is_archived ? "Archived" : "Unarchived");
      setConversations((prev) => prev.filter((c) => c.id !== conv.id));
    }
    setMenuFor(null);
  };

  const shareConversation = async (conv, e) => {
    e?.stopPropagation();
    setMenuFor(null);
    try {
      if (conv.share_token) {
        const url = `${window.location.origin}/share/${conv.share_token}`;
        await navigator.clipboard?.writeText(url).catch(() => {});
        toast.success("Share link copied");
        return;
      }
      const { data } = await api.post(`/conversations/${conv.id}/share`);
      setConversations((prev) => prev.map((c) => (c.id === conv.id ? { ...c, share_token: data.share_token } : c)));
      setActiveConv((c) => (c && c.id === conv.id ? { ...c, share_token: data.share_token } : c));
      const url = `${window.location.origin}/share/${data.share_token}`;
      await navigator.clipboard?.writeText(url).catch(() => {});
      toast.success("Public link created & copied");
    } catch {
      toast.error("Could not create share link.");
    }
  };

  const exportConversation = async (conv, format, e) => {
    e?.stopPropagation();
    setMenuFor(null);
    try {
      const res = await fetch(`${API_BASE}/conversations/${conv.id}/export?format=${format}`, {
        headers: { Authorization: `Bearer ${getToken() || ""}` },
      });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `conversation-${conv.id}.${format === "json" ? "json" : "md"}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(`Exported as ${format === "json" ? "JSON" : "Markdown"}`);
    } catch {
      toast.error("Export failed.");
    }
  };

  const regenerate = useCallback(async () => {
    if (!conversationId || regenerating || sending) return;
    setRegenerating(true);
    try {
      const { data } = await api.post(`/conversations/${conversationId}/regenerate`, null, {
        params: { use_knowledge: useKnowledge },
      });
      setMessages((prev) => {
        // drop the last assistant message, append the fresh one
        const trimmed = [...prev];
        for (let i = trimmed.length - 1; i >= 0; i--) {
          if (trimmed[i].role === "assistant") {
            trimmed.splice(i, 1);
            break;
          }
        }
        trimmed.push({
          id: data.assistant_message.id,
          conversation_id: conversationId,
          role: "assistant",
          content: data.assistant_message.content,
          metadata: data.assistant_message.metadata,
          created_at: data.assistant_message.created_at,
        });
        return trimmed;
      });
      setSuggested([]);
      toast.success("Regenerated");
    } catch (err) {
      const msg = err?.response?.data?.detail?.message || err?.response?.data?.detail;
      toast.error(typeof msg === "string" ? msg : "Regenerate failed.");
    } finally {
      setRegenerating(false);
    }
  }, [conversationId, regenerating, sending, useKnowledge]);

  const loadSuggested = useCallback(async () => {
    if (!conversationId) return;
    try {
      const { data } = await api.get(`/conversations/${conversationId}/suggested-questions`);
      setSuggested(Array.isArray(data?.questions) ? data.questions : []);
    } catch {
      setSuggested([]);
    }
  }, [conversationId]);

  /* refresh suggestions when the thread settles (last msg is assistant) */
  useEffect(() => {
    if (sending || regenerating) return;
    const last = messages[messages.length - 1];
    if (last && last.role === "assistant") {
      loadSuggested();
    } else {
      setSuggested([]);
    }
  }, [messages, sending, regenerating, loadSuggested]);

  const agentName = useMemo(() => {
    if (!activeConv) return "";
    const a = agents.find((x) => x.id === activeConv.agent_id);
    return a?.name || "Agent";
  }, [activeConv, agents]);

  /* ------------------------------ render ------------------------------ */

  return (
    <div className="h-[calc(100vh-7rem)] min-h-[520px]" data-testid={CHAT.page}>
      <div className="h-full grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-5">
        {/* ============ LEFT — conversation list ============ */}
        <div className="hidden lg:flex rounded-2xl bg-white border border-[#E2E8F0] flex-col overflow-hidden">
          <div className="p-3 border-b border-[#E2E8F0] space-y-2.5">
            <button
              onClick={onNewChat}
              data-testid={CHAT.newChatBtn}
              className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_8px_24px_-8px_rgba(37,99,235,0.5)] transition-colors"
            >
              <Plus size={16} /> New Chat
            </button>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search conversations…"
                data-testid="chat-search"
                className="w-full pl-8 pr-7 py-2 rounded-lg border border-[#E2E8F0] text-[13px] placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10"
              />
              {search && (
                <button
                  onClick={() => setSearch("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-[#94A3B8] hover:text-[#0F172A]"
                  aria-label="Clear search"
                >
                  <X size={13} />
                </button>
              )}
            </div>
            <div className="flex items-center gap-1 text-[12px]">
              {[
                { k: "active", label: "All" },
                { k: "favorites", label: "Favorites" },
                { k: "archived", label: "Archived" },
              ].map((t) => (
                <button
                  key={t.k}
                  onClick={() => setFilter(t.k)}
                  data-testid={`chat-filter-${t.k}`}
                  className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                    filter === t.k ? "bg-[#EFF6FF] text-[#2563EB]" : "text-[#64748B] hover:bg-[#F8FAFC]"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-1">
            {loadingConvs ? (
              [1, 2, 3, 4].map((i) => <div key={i} className="h-14 rounded-xl skeleton" />)
            ) : conversations.length === 0 ? (
              <div className="px-3 py-10 text-center">
                <MessageSquarePlus size={28} className="mx-auto text-[#94A3B8]" />
                <p className="mt-2 text-sm text-[#64748B]">
                  {search ? "No matches found." : filter === "archived" ? "No archived chats." : filter === "favorites" ? "No favorites yet." : "No conversations yet."}
                </p>
                {!search && filter === "active" && <p className="text-xs text-[#94A3B8]">Start a new chat to begin.</p>}
              </div>
            ) : (
              (() => {
                const pinned = conversations.filter((c) => c.is_pinned);
                const others = conversations.filter((c) => !c.is_pinned);
                const rowProps = {
                  conversationId,
                  nav,
                  menuFor,
                  setMenuFor,
                  togglePin,
                  toggleFavorite,
                  toggleArchive,
                  shareConversation,
                  exportConversation,
                  deleteConversation,
                };
                return (
                  <>
                    {pinned.length > 0 && (
                      <>
                        <div className="px-2 pt-1 pb-0.5 text-[10.5px] font-semibold uppercase tracking-wide text-[#94A3B8] flex items-center gap-1">
                          <Pin size={10} /> Pinned
                        </div>
                        {pinned.map((c) => (
                          <ConversationRow key={c.id} c={c} {...rowProps} />
                        ))}
                        {others.length > 0 && (
                          <div className="px-2 pt-2 pb-0.5 text-[10.5px] font-semibold uppercase tracking-wide text-[#94A3B8]">
                            Recent
                          </div>
                        )}
                      </>
                    )}
                    {others.map((c) => (
                      <ConversationRow key={c.id} c={c} {...rowProps} />
                    ))}
                  </>
                );
              })()
            )}
          </div>
        </div>

        {/* ============ RIGHT — chat area ============ */}
        <div className="rounded-2xl bg-white border border-[#E2E8F0] flex flex-col overflow-hidden">
          {!conversationId ? (
            <EmptyChat onNewChat={onNewChat} />
          ) : (
            <>
              {/* header */}
              <div className="h-16 px-4 sm:px-5 border-b border-[#E2E8F0] flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="size-10 rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] grid place-items-center text-white shrink-0">
                    <Bot size={18} />
                  </div>
                  <div className="min-w-0">
                    {renaming ? (
                      <div className="flex items-center gap-1.5">
                        <input
                          autoFocus
                          value={renameValue}
                          onChange={(e) => setRenameValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") commitRename();
                            if (e.key === "Escape") setRenaming(false);
                          }}
                          data-testid={CHAT.renameConversation}
                          className="px-2 py-1 rounded-lg border border-[#E2E8F0] text-sm focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10"
                        />
                        <button
                          onClick={commitRename}
                          className="p-1.5 rounded-lg text-[#16A34A] hover:bg-green-50"
                          aria-label="Save title"
                        >
                          <Check size={15} />
                        </button>
                        <button
                          onClick={() => setRenaming(false)}
                          className="p-1.5 rounded-lg text-[#64748B] hover:bg-[#F1F5F9]"
                          aria-label="Cancel rename"
                        >
                          <X size={15} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 min-w-0">
                        <h2 className="text-base font-semibold text-[#0F172A] truncate">
                          {activeConv?.title || "New Conversation"}
                        </h2>
                        <button
                          onClick={beginRename}
                          className="p-1 rounded-md text-[#94A3B8] hover:text-[#2563EB] hover:bg-[#EFF6FF]"
                          aria-label="Rename conversation"
                        >
                          <Pencil size={13} />
                        </button>
                      </div>
                    )}
                    <p className="text-xs text-[#64748B] truncate">{agentName}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  {activeConv?.share_token && (
                    <span className="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded-full bg-[#ECFDF5] text-[11px] font-medium text-[#059669] mr-1">
                      <Share2 size={11} /> Shared
                    </span>
                  )}
                  <button
                    onClick={(e) => activeConv && togglePin(activeConv, e)}
                    className={`p-2 rounded-lg transition-colors ${
                      activeConv?.is_pinned ? "text-[#2563EB] bg-[#EFF6FF]" : "text-[#94A3B8] hover:text-[#2563EB] hover:bg-[#EFF6FF]"
                    }`}
                    aria-label="Pin conversation"
                    title={activeConv?.is_pinned ? "Unpin" : "Pin"}
                  >
                    <Pin size={16} />
                  </button>
                  <button
                    onClick={(e) => activeConv && toggleFavorite(activeConv, e)}
                    className={`p-2 rounded-lg transition-colors ${
                      activeConv?.is_favorite ? "text-amber-500 bg-amber-50" : "text-[#94A3B8] hover:text-amber-500 hover:bg-amber-50"
                    }`}
                    aria-label="Favorite conversation"
                    title={activeConv?.is_favorite ? "Unfavorite" : "Favorite"}
                  >
                    <Star size={16} className={activeConv?.is_favorite ? "fill-amber-400" : ""} />
                  </button>
                  <button
                    onClick={(e) => activeConv && shareConversation(activeConv, e)}
                    className="p-2 rounded-lg text-[#94A3B8] hover:text-[#2563EB] hover:bg-[#EFF6FF] transition-colors"
                    aria-label="Share conversation"
                    title="Share"
                  >
                    <Share2 size={16} />
                  </button>
                  <button
                    onClick={(e) => activeConv && exportConversation(activeConv, "markdown", e)}
                    className="p-2 rounded-lg text-[#94A3B8] hover:text-[#2563EB] hover:bg-[#EFF6FF] transition-colors"
                    aria-label="Export conversation"
                    title="Export as Markdown"
                  >
                    <Download size={16} />
                  </button>
                  <button
                    onClick={(e) => activeConv && deleteConversation(activeConv, e)}
                    className="p-2 rounded-lg text-[#94A3B8] hover:text-red-500 hover:bg-red-50"
                    aria-label="Delete conversation"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {/* messages */}
              <div
                ref={scrollRef}
                data-testid={CHAT.messageList}
                className="flex-1 overflow-y-auto scrollbar-thin p-4 sm:p-6 space-y-4 bg-[#F8FAFC]"
              >
                {loadingThread ? (
                  <div className="space-y-4">
                    <div className="h-16 w-2/3 rounded-2xl skeleton" />
                    <div className="h-16 w-1/2 ml-auto rounded-2xl skeleton" />
                    <div className="h-16 w-3/5 rounded-2xl skeleton" />
                  </div>
                ) : messages.length === 0 && !streamingText ? (
                  <div className="h-full grid place-items-center text-center">
                    <div>
                      <Sparkles size={28} className="mx-auto text-[#2563EB]" />
                      <p className="mt-2 text-sm font-medium text-[#0F172A]">
                        Say hello to start the conversation
                      </p>
                      <p className="text-xs text-[#94A3B8]">
                        Your agent will answer using its instructions and knowledge base.
                      </p>
                    </div>
                  </div>
                ) : (
                  <>
                    {messages
                      .filter((m) => !m._streaming)
                      .map((m) => (
                        <Bubble key={m.id} role={m.role} content={m.content} meta={m.metadata} />
                      ))}
                    {(streamingText || sending) && (
                      <Bubble role="assistant" content={streamingText} streaming />
                    )}
                  </>
                )}
              </div>

              {/* composer */}
              <div className="border-t border-[#E2E8F0] p-3 sm:p-4">
                {/* suggested follow-ups + regenerate */}
                {!sending && !streamingText && messages.length > 0 && (
                  <div className="mb-2.5 flex flex-wrap items-center gap-1.5">
                    {suggested.slice(0, 3).map((qq, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(qq)}
                        data-testid="chat-suggested"
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#F8FAFC] border border-[#E2E8F0] text-[12px] text-[#334155] hover:border-[#2563EB] hover:text-[#2563EB] transition-colors"
                      >
                        <Lightbulb size={12} className="text-amber-500" />
                        <span className="truncate max-w-[220px]">{qq}</span>
                      </button>
                    ))}
                    <button
                      onClick={regenerate}
                      disabled={regenerating}
                      data-testid="chat-regenerate"
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white border border-[#E2E8F0] text-[12px] text-[#64748B] hover:text-[#2563EB] hover:border-[#2563EB] transition-colors disabled:opacity-50"
                      title="Regenerate the last response"
                    >
                      <RefreshCw size={12} className={regenerating ? "animate-spin" : ""} /> Regenerate
                    </button>
                  </div>
                )}
                <div className="flex items-center justify-between mb-2 px-1">
                  <button
                    onClick={() => setUseKnowledge((v) => !v)}
                    data-testid={CHAT.knowledgeToggle}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-medium transition-colors ${
                      useKnowledge
                        ? "bg-[#EFF6FF] text-[#2563EB]"
                        : "bg-[#F1F5F9] text-[#64748B] hover:bg-[#E2E8F0]"
                    }`}
                    aria-pressed={useKnowledge}
                  >
                    <BookOpen size={13} />
                    Knowledge {useKnowledge ? "on" : "off"}
                  </button>
                  {sending && (
                    <span
                      data-testid={CHAT.typingIndicator}
                      className="inline-flex items-center gap-1.5 text-[12px] text-[#64748B]"
                    >
                      <Loader2 size={13} className="animate-spin" /> Agent is typing…
                    </span>
                  )}
                </div>
                <div className="flex items-end gap-2">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={onKeyDown}
                    rows={1}
                    placeholder="Type your message…  (Enter to send, Shift+Enter for newline)"
                    data-testid={CHAT.input}
                    className="flex-1 resize-none max-h-40 px-4 py-3 rounded-xl border border-[#E2E8F0] bg-white text-sm placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10 transition-all"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={!input.trim() || sending}
                    data-testid={CHAT.sendBtn}
                    className="size-12 shrink-0 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-40 disabled:cursor-not-allowed text-white grid place-items-center shadow-[0_8px_24px_-8px_rgba(37,99,235,0.5)] transition-colors"
                    aria-label="Send message"
                  >
                    {sending ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* agent picker modal */}
      {showPicker && (
        <AgentPicker agents={agents} onPick={startConversation} onClose={() => setShowPicker(false)} />
      )}
    </div>
  );
}

/* ----------------------------- subcomponents ----------------------------- */

function ConversationRow({
  c,
  conversationId,
  nav,
  menuFor,
  setMenuFor,
  togglePin,
  toggleFavorite,
  toggleArchive,
  shareConversation,
  exportConversation,
  deleteConversation,
}) {
  const sel = c.id === conversationId;
  const open = menuFor === c.id;
  return (
    <div
      onClick={() => nav(`/app/chat/${c.id}`)}
      data-testid={CHAT.conversationItem}
      className={`group relative w-full text-left px-3 py-2.5 rounded-xl transition-colors cursor-pointer ${
        sel ? "bg-[#EFF6FF]" : "hover:bg-[#F8FAFC]"
      }`}
      role="button"
      tabIndex={0}
    >
      <div className="flex items-center gap-2">
        <div
          className={`size-8 rounded-lg grid place-items-center shrink-0 ${
            sel ? "bg-[#2563EB] text-white" : "bg-[#F1F5F9] text-[#64748B]"
          }`}
        >
          <Sparkles size={15} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1">
            {c.is_pinned && <Pin size={11} className="text-[#2563EB] shrink-0" />}
            {c.is_favorite && <Star size={11} className="text-amber-500 fill-amber-400 shrink-0" />}
            <p className={`text-sm font-medium truncate ${sel ? "text-[#2563EB]" : "text-[#0F172A]"}`}>
              {c.title || "New Conversation"}
            </p>
          </div>
          <p className="text-[11px] text-[#94A3B8]">{relativeTime(c.last_message_at || c.created_at)}</p>
          {Array.isArray(c.tags) && c.tags.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {c.tags.slice(0, 3).map((t) => (
                <span key={t} className="px-1.5 py-0.5 rounded bg-[#F1F5F9] text-[9.5px] text-[#64748B]">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center">
          <button
            onClick={(e) => togglePin(c, e)}
            className={`opacity-0 group-hover:opacity-100 p-1.5 rounded-lg transition-all ${
              c.is_pinned ? "text-[#2563EB] opacity-100" : "text-[#94A3B8] hover:text-[#2563EB] hover:bg-[#EFF6FF]"
            }`}
            aria-label={c.is_pinned ? "Unpin" : "Pin"}
          >
            <Pin size={14} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setMenuFor(open ? null : c.id);
            }}
            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-[#94A3B8] hover:text-[#0F172A] hover:bg-[#F1F5F9] transition-all"
            aria-label="More actions"
            aria-haspopup="menu"
            aria-expanded={open}
          >
            <MoreVertical size={14} />
          </button>
        </div>
      </div>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={(e) => { e.stopPropagation(); setMenuFor(null); }} />
          <div
            className="absolute right-2 top-11 z-20 w-44 rounded-xl bg-white border border-[#E2E8F0] shadow-xl py-1 text-[13px]"
            role="menu"
            onClick={(e) => e.stopPropagation()}
          >
            <MenuItem icon={Star} label={c.is_favorite ? "Unfavorite" : "Favorite"} onClick={(e) => { toggleFavorite(c, e); setMenuFor(null); }} />
            <MenuItem icon={Archive} label={c.is_archived ? "Unarchive" : "Archive"} onClick={(e) => toggleArchive(c, e)} />
            <MenuItem icon={Share2} label={c.share_token ? "Copy share link" : "Share"} onClick={(e) => shareConversation(c, e)} />
            <MenuItem icon={Download} label="Export Markdown" onClick={(e) => exportConversation(c, "markdown", e)} />
            <MenuItem icon={FileText} label="Export JSON" onClick={(e) => exportConversation(c, "json", e)} />
            <div className="my-1 border-t border-[#F1F5F9]" />
            <MenuItem icon={Trash2} label="Delete" danger onClick={(e) => { deleteConversation(c, e); setMenuFor(null); }} />
          </div>
        </>
      )}
    </div>
  );
}

function MenuItem({ icon: Icon, label, onClick, danger }) {
  return (
    <button
      onClick={onClick}
      role="menuitem"
      className={`w-full flex items-center gap-2 px-3 py-1.5 text-left transition-colors ${
        danger ? "text-red-600 hover:bg-red-50" : "text-[#334155] hover:bg-[#F8FAFC]"
      }`}
    >
      <Icon size={14} className="shrink-0" /> {label}
    </button>
  );
}

function Bubble({ role, content, streaming = false, meta }) {
  const isUser = role === "user";
  const isSystem = role === "system";
  if (isSystem) {
    return (
      <div className="flex justify-center">
        <span className="px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] text-[#64748B]">{content}</span>
      </div>
    );
  }
  const sources = Array.isArray(meta?.sources) ? meta.sources : [];
  const usedCount = meta?.context_used ?? meta?.context_chunks ?? sources.length ?? 0;
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`} data-testid={CHAT.message} data-role={role}>
      <div
        className={`size-8 rounded-lg grid place-items-center shrink-0 ${
          isUser ? "bg-[#2563EB] text-white" : "bg-white border border-[#E2E8F0] text-[#2563EB]"
        }`}
      >
        {isUser ? <User size={15} /> : <Bot size={15} />}
      </div>
      <div className={`max-w-[78%] ${isUser ? "items-end" : "items-start"} flex flex-col`}>
        <div
          className={`px-4 py-2.5 rounded-2xl text-sm break-words ${
            isUser
              ? "bg-[#2563EB] text-white rounded-tr-sm whitespace-pre-wrap"
              : "bg-white border border-[#E2E8F0] text-[#0F172A] rounded-tl-sm"
          }`}
        >
          {isUser ? (
            content || ""
          ) : (
            <div className="space-y-0.5">{renderMarkdown(content)}</div>
          )}
          {streaming && <span className="inline-block w-1.5 h-4 ml-0.5 align-middle bg-[#2563EB] animate-pulse" />}
        </div>
        {!isUser && sources.length > 0 ? (
          <SourcesPanel sources={sources} />
        ) : (
          !isUser &&
          usedCount > 0 && (
            <span className="mt-1 inline-flex items-center gap-1 text-[10.5px] text-[#94A3B8]">
              <BookOpen size={11} /> {usedCount} knowledge source{usedCount > 1 ? "s" : ""} used
            </span>
          )
        )}
      </div>
    </div>
  );
}

function SourcesPanel({ sources }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1.5 w-full" data-testid="chat-sources">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1 text-[10.5px] font-medium text-[#64748B] hover:text-[#2563EB] transition-colors"
        aria-expanded={open}
      >
        <BookOpen size={11} />
        {sources.length} source{sources.length > 1 ? "s" : ""}
        <ChevronDown size={11} className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ul className="mt-1.5 space-y-1">
          {sources.map((s, i) => (
            <li
              key={`${s.document_id || s.document || i}-${s.page ?? i}`}
              className="flex items-start gap-2 px-2.5 py-1.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]"
            >
              <span className="mt-0.5 size-4 rounded grid place-items-center bg-[#EFF6FF] text-[10px] font-semibold text-[#2563EB] shrink-0">
                {i + 1}
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 text-[11.5px] font-medium text-[#0F172A] truncate">
                  <FileText size={11} className="text-[#94A3B8] shrink-0" />
                  <span className="truncate">{s.document || s.document_name || "Document"}</span>
                </div>
                <div className="text-[10px] text-[#94A3B8]">
                  {s.page != null ? `Page ${s.page}` : "—"}
                  {s.section ? ` · ${s.section}` : ""}
                  {typeof s.score === "number" ? ` · ${Math.round(s.score * 100)}% match` : ""}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function EmptyChat({ onNewChat }) {
  return (
    <div className="h-full grid place-items-center p-8 text-center">
      <div className="max-w-sm">
        <div className="size-14 mx-auto rounded-2xl bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] grid place-items-center text-white">
          <Sparkles size={24} />
        </div>
        <h2 className="mt-4 text-xl font-bold text-[#0F172A]">Chat with your AI agents</h2>
        <p className="mt-1.5 text-sm text-[#64748B]">
          Start a conversation to test your agent live. Responses use the agent's instructions and your knowledge base.
        </p>
        <button
          onClick={onNewChat}
          className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_8px_24px_-8px_rgba(37,99,235,0.5)]"
        >
          <Plus size={16} /> New Chat
        </button>
      </div>
    </div>
  );
}

function AgentPicker({ agents, onPick, onClose }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <div className="absolute inset-0 bg-[#0F172A]/50 backdrop-blur-sm" onClick={onClose} />
      <div
        className="relative w-full max-w-md rounded-2xl bg-white border border-[#E2E8F0] shadow-2xl overflow-hidden"
        data-testid={CHAT.agentPicker}
        role="dialog"
        aria-modal="true"
      >
        <div className="h-14 px-5 flex items-center justify-between border-b border-[#E2E8F0]">
          <h3 className="text-base font-semibold text-[#0F172A]">Choose an agent</h3>
          <button onClick={onClose} className="p-2 rounded-lg text-[#64748B] hover:bg-[#F1F5F9]" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="max-h-[60vh] overflow-y-auto scrollbar-thin p-2">
          {agents.map((a) => {
            const Icon = AGENT_ICON[a.type] || Sparkles;
            return (
              <button
                key={a.id}
                onClick={() => onPick(a)}
                data-testid={CHAT.agentOption}
                className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-[#F8FAFC] text-left transition-colors"
              >
                <div className="size-10 rounded-xl bg-[#EFF6FF] grid place-items-center text-[#2563EB] shrink-0">
                  <Icon size={18} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-[#0F172A] truncate">{a.name}</p>
                  <p className="text-xs text-[#64748B] capitalize">{a.type || "chat"} agent</p>
                </div>
                {a.status === "active" ? (
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-green-50 text-green-700">
                    Active
                  </span>
                ) : (
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-[#F1F5F9] text-[#64748B]">
                    Paused
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
