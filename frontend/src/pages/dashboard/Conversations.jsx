import React, { useEffect, useMemo, useState } from "react";
import {
  MessageSquare,
  MessageCircle,
  Search,
  SlidersHorizontal,
  Calendar,
  MoreVertical,
  Bot,
  User,
  ChevronLeft,
  ChevronRight,
  Zap,
  Clock,
  DollarSign,
  Cpu,
  ShieldCheck,
  Quote,
  Loader2,
} from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/dashboard/kit";

/* ---------- Data ---------- */

const CHANNEL = {
  chat:     { icon: MessageSquare, color: "#0891B2", bg: "#ECFEFF", label: "Website Chat" },
  whatsapp: { icon: MessageCircle, color: "#16A34A", bg: "#DCFCE7", label: "WhatsApp" },
};

const STATUS_META = {
  active:    { label: "Active",    cls: "bg-blue-50 text-blue-700 border-blue-200" },
  completed: { label: "Completed", cls: "bg-green-50 text-green-700 border-green-200" },
  qualified: { label: "Qualified", cls: "bg-cyan-50 text-cyan-700 border-cyan-200" },
  failed:    { label: "Failed",    cls: "bg-red-50 text-red-700 border-red-200" },
  lost:      { label: "Lost",      cls: "bg-orange-50 text-orange-700 border-orange-200" },
};

const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : "");
const statusCls = (raw) => STATUS_META[raw]?.cls || "bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]";
const statusLabel = (raw) => STATUS_META[raw]?.label || cap(raw);

const fmtCost = (n) => {
  const v = Number(n || 0);
  if (v === 0) return "$0.00";
  if (v < 0.01) return `$${v.toFixed(4)}`;
  return `$${v.toFixed(2)}`;
};
const fmtTokens = (n) => {
  const v = Number(n || 0);
  return v >= 1000 ? `${(v / 1000).toFixed(1)}k` : `${v}`;
};
const shortTime = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
};

// Map a raw /v2/conversations row to the shape the UI renders.
function normalizeConv(c) {
  const started = c.started_at || c.created_at;
  return {
    ...c,
    name: c.customer_name || c.title || "Anonymous visitor",
    phone: c.customer_phone || c.customer_email || "No contact info",
    statusRaw: c.status,
    statusLabel: statusLabel(c.status),
    time: shortTime(c.last_message_at || started),
    date: started ? new Date(started).toLocaleDateString() : "",
    startedAt: started,
    tokens: c.total_tokens || 0,
    cost: c.total_cost_usd || 0,
    msgCount: c.message_count || 0,
    model: c.last_model || (Array.isArray(c.models) && c.models[0]) || null,
    avgLatency: c.avg_latency_ms || null,
  };
}

const FILTERS = [
  { k: "all",      l: "All",          icon: null },
  { k: "chat",     l: "Chats",        icon: MessageSquare },
];

/* ---------- Page ---------- */

export default function Conversations() {
  const [conversations, setConversations] = useState([]);
  const [active, setActive] = useState(null);
  const [filter, setFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showStatus, setShowStatus] = useState(false);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch conversations from API
  const loadConversations = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get("/v2/conversations");
      const data = (response.data || []).map(normalizeConv);
      setConversations(data);
      if (data.length > 0) setActive(data[0]);
    } catch (err) {
      const message = formatApiError(err.response?.data?.detail) || "Failed to load conversations";
      setError(message);
      setConversations([]);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Distinct statuses present in the data, for the status filter menu.
  const statuses = useMemo(() => {
    const set = new Set();
    conversations.forEach((c) => c.status && set.add(c.status));
    return ["all", ...Array.from(set)];
  }, [conversations]);

  const filtered = useMemo(() => {
    return conversations.filter((c) => {
      if (filter !== "all" && c.channel !== filter) return false;
      if (statusFilter !== "all" && c.status !== statusFilter) return false;
      if (q && !`${c.name || ""} ${c.phone || ""}`.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    });
  }, [conversations, filter, statusFilter, q]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <PageHeader
        eyebrow="Inbox"
        icon={MessageSquare}
        title="Conversations"
        subtitle="Live transcripts and conversation history across all channels."
      />

      <div className="grid grid-cols-1 lg:grid-cols-[428px_1fr] gap-6">
        {/* ============ LEFT — list ============ */}
        <div className="rounded-2xl bg-white border border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)] flex flex-col overflow-hidden">
          {/* Channel filter chips */}
          <div className="p-3 border-b border-[#E2E8F0]">
            <div className="flex gap-2 overflow-x-auto scrollbar-thin">
              {FILTERS.map((f) => {
                const Icon = f.icon;
                const sel = filter === f.k;
                return (
                  <button
                    key={f.k}
                    onClick={() => setFilter(f.k)}
                    data-testid={`conv-filter-${f.k}`}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[12.5px] font-medium whitespace-nowrap transition-colors ${
                      sel
                        ? "bg-[#2563EB] text-white shadow-[0_4px_12px_-4px_rgba(37,99,235,0.45)]"
                        : "text-[#475569] hover:bg-[#F8FAFC]"
                    }`}
                  >
                    {Icon && <Icon size={13} />}
                    {f.l}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Search */}
          <div className="p-3 border-b border-[#E2E8F0] flex items-center gap-2">
            <div className="relative flex-1">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
              <input
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search conversations..."
                data-testid="conv-search"
                className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-[#E2E8F0] bg-white text-[13px] placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10 transition-all"
              />
            </div>
            <button
              onClick={() => setShowStatus((v) => !v)}
              className={`relative size-10 rounded-xl border grid place-items-center transition-colors ${
                statusFilter !== "all" || showStatus
                  ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]"
                  : "border-[#E2E8F0] hover:bg-[#F8FAFC] text-[#475569]"
              }`}
              aria-label="Filters"
              data-testid="conv-filters-btn"
            >
              <SlidersHorizontal size={15} />
              {statusFilter !== "all" && (
                <span className="absolute -top-1 -right-1 size-2.5 rounded-full bg-[#2563EB] border-2 border-white" />
              )}
            </button>
          </div>

          {/* Status filter menu */}
          {showStatus && (
            <div className="px-3 py-2.5 border-b border-[#E2E8F0] bg-[#F8FAFC]/60" data-testid="conv-status-filter">
              <p className="text-[10.5px] uppercase tracking-[0.1em] text-[#94A3B8] font-semibold mb-2">Filter by status</p>
              <div className="flex flex-wrap gap-1.5">
                {statuses.map((s) => (
                  <button
                    key={s}
                    onClick={() => setStatusFilter(s)}
                    data-testid={`conv-status-${s}`}
                    className={`text-[11.5px] px-2.5 py-1 rounded-full border font-medium transition-colors ${
                      statusFilter === s
                        ? "bg-[#2563EB] text-white border-[#2563EB]"
                        : `bg-white ${statusCls(s)}`
                    }`}
                  >
                    {s === "all" ? "All statuses" : statusLabel(s)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* List */}
          <ul className="flex-1 overflow-y-auto max-h-[640px] scrollbar-thin">
            {filtered.length === 0 ? (
              loading ? (
                <li className="p-10 flex flex-col items-center justify-center text-center gap-3" data-testid="conv-list-loading">
                  <Loader2 size={22} className="animate-spin text-[#2563EB]" />
                  <span className="text-[13px] text-[#94A3B8]">Loading conversations…</span>
                </li>
              ) : (
              <li className="p-5">
                <EmptyState
                  testId={error ? "conv-list-error" : "conv-list-empty"}
                  size="sm"
                  dashed={false}
                  icon={MessageSquare}
                  title={error ? "Couldn't load conversations" : "No conversations match"}
                  description={
                    error
                      ? error
                      : q
                      ? `We couldn't find anything for "${q}". Try a different name, phone or channel.`
                      : "No conversations in this channel yet. Once your AI agents talk to leads, they'll show up here."
                  }
                  actionLabel={error ? "Retry" : (q || filter !== "all" || statusFilter !== "all" ? "Clear filters" : undefined)}
                  onAction={
                    error
                      ? loadConversations
                      : q || filter !== "all" || statusFilter !== "all"
                      ? () => {
                          setQ("");
                          setFilter("all");
                          setStatusFilter("all");
                        }
                      : undefined
                  }
                />
              </li>
              )
            ) : null}
            {filtered.map((c) => {
              const meta = CHANNEL[c.channel];
              const Icon = meta.icon;
              const sel = active?.id === c.id;
              return (
                <li
                  key={c.id}
                  onClick={() => setActive(c)}
                  data-testid={`conv-${c.id}`}
                  className={`relative p-4 cursor-pointer transition-colors border-b border-[#F1F5F9] ${
                    sel ? "bg-[#EFF6FF]" : "hover:bg-[#F8FAFC]"
                  }`}
                >
                  {sel && (
                    <span className="absolute left-0 top-0 bottom-0 w-[3px] bg-[#2563EB] rounded-r-full" />
                  )}
                  <div className="flex items-start gap-3">
                    <div
                      className="size-10 rounded-xl grid place-items-center shrink-0"
                      style={{ background: meta.bg }}
                    >
                      <Icon size={16} style={{ color: meta.color }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-[13.5px] font-semibold text-[#0F172A] truncate">{c.name}</p>
                        <span className="text-[11px] text-[#94A3B8] whitespace-nowrap">{c.time}</span>
                      </div>
                      <p className="text-[11.5px] text-[#64748B] mt-0.5 truncate">
                        {c.phone} <span className="text-[#CBD5E1]">·</span> {meta.label}
                      </p>
                      <div className="mt-2 flex items-center gap-2 flex-wrap">
                        <span
                          className={`inline-block text-[10.5px] px-2 py-0.5 rounded-full border font-medium ${statusCls(
                            c.statusRaw
                          )}`}
                        >
                          {c.statusLabel}
                        </span>
                        {c.msgCount > 0 && (
                          <span className="inline-flex items-center gap-1 text-[10.5px] text-[#94A3B8]">
                            <MessageSquare size={11} /> {c.msgCount}
                          </span>
                        )}
                        {c.tokens > 0 && (
                          <span className="inline-flex items-center gap-1 text-[10.5px] text-[#94A3B8]">
                            <Zap size={11} /> {fmtTokens(c.tokens)}
                          </span>
                        )}
                        {c.cost > 0 && (
                          <span className="inline-flex items-center gap-1 text-[10.5px] text-[#94A3B8]">
                            {fmtCost(c.cost)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>

          {/* Pagination */}
          {filtered.length > 0 && (
            <div className="p-3 border-t border-[#E2E8F0] flex items-center justify-center gap-1 text-[12.5px]">
              <Pager
                page={page}
                total={12}
                onChange={setPage}
              />
            </div>
          )}
        </div>

        {/* ============ RIGHT — conversation detail ============ */}
        <ConversationPanel conv={active} />
      </div>
    </div>
  );
}

/* ---------- Pager ---------- */

function Pager({ page, total, onChange }) {
  const pages = [1, 2, 3, 4, 5];
  return (
    <>
      <button
        onClick={() => page > 1 && onChange(page - 1)}
        className="size-8 rounded-lg grid place-items-center hover:bg-[#F1F5F9] text-[#64748B] disabled:opacity-40"
        disabled={page === 1}
        aria-label="Previous page"
      >
        <ChevronLeft size={14} />
      </button>
      {pages.map((n) => (
        <button
          key={n}
          onClick={() => onChange(n)}
          className={`size-8 rounded-lg font-semibold transition-colors ${
            n === page
              ? "bg-[#2563EB] text-white"
              : "text-[#475569] hover:bg-[#F1F5F9]"
          }`}
        >
          {n}
        </button>
      ))}
      <span className="px-1 text-[#94A3B8]">...</span>
      <button
        onClick={() => onChange(total)}
        className={`size-8 rounded-lg font-semibold transition-colors ${
          total === page ? "bg-[#2563EB] text-white" : "text-[#475569] hover:bg-[#F1F5F9]"
        }`}
      >
        {total}
      </button>
      <button
        onClick={() => page < total && onChange(page + 1)}
        className="size-8 rounded-lg grid place-items-center hover:bg-[#F1F5F9] text-[#64748B] disabled:opacity-40"
        disabled={page === total}
        aria-label="Next page"
      >
        <ChevronRight size={14} />
      </button>
    </>
  );
}

/* ---------- Conversation panel ---------- */

function ConversationPanel({ conv }) {
  const [note, setNote] = useState("");
  const [messages, setMessages] = useState([]);
  const [msgLoading, setMsgLoading] = useState(false);
  const [msgError, setMsgError] = useState(null);

  useEffect(() => {
    if (!conv?.id) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setMsgLoading(true);
      setMsgError(null);
      try {
        const { data } = await api.get(`/v2/conversations/${conv.id}/messages`);
        if (!cancelled) setMessages(Array.isArray(data) ? data : []);
      } catch (err) {
        if (!cancelled) {
          setMessages([]);
          const message = formatApiError(err.response?.data?.detail) || "Failed to load messages";
          setMsgError(message);
          toast.error(message);
        }
      } finally {
        if (!cancelled) setMsgLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [conv?.id]);

  if (!conv) {
    return (
      <div className="rounded-2xl bg-white border border-[#E2E8F0] grid place-items-center min-h-[520px] p-6">
        <EmptyState
          testId="conv-panel-empty"
          dashed={false}
          showOrb={false}
          className="border-0 bg-transparent shadow-none"
          title="Pick a conversation"
          description="Select any conversation on the left to view its live transcript, AI notes and recording."
        />
      </div>
    );
  }
  const meta = CHANNEL[conv.channel];
  const Icon = meta.icon;

  return (
    <div className="rounded-2xl bg-white border border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)] flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-[#E2E8F0] flex items-center gap-3">
        <div className="size-10 rounded-xl grid place-items-center shrink-0" style={{ background: meta.bg }}>
          <Icon size={16} style={{ color: meta.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-[15px] font-semibold text-[#0F172A] truncate">{conv.name}</h3>
            <span
              className={`text-[10.5px] px-2 py-0.5 rounded-full border font-medium ${statusCls(
                conv.statusRaw
              )}`}
            >
              {conv.statusLabel}
            </span>
          </div>
          <p className="text-[12px] text-[#64748B] mt-0.5">
            {conv.phone} <span className="text-[#CBD5E1]">·</span> {meta.label}
          </p>
        </div>
        <div className="hidden sm:flex items-center gap-3 text-[12px] text-[#64748B]">
          {conv.startedAt && (
            <span className="inline-flex items-center gap-1.5">
              <Calendar size={13} /> {new Date(conv.startedAt).toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })}
            </span>
          )}
          <span className="text-[#CBD5E1]">·</span>
          <span>{conv.time}</span>
        </div>
        <button className="size-9 rounded-lg grid place-items-center hover:bg-[#F1F5F9]" aria-label="More">
          <MoreVertical size={15} className="text-[#64748B]" />
        </button>
      </div>

      {/* Observability rollup */}
      {(conv.msgCount > 0 || conv.tokens > 0 || conv.cost > 0 || conv.model) && (
        <div className="px-5 py-2.5 border-b border-[#F1F5F9] bg-[#FAFBFC] flex items-center gap-4 flex-wrap text-[11.5px]">
          <RollupStat icon={MessageSquare} label="Messages" value={conv.msgCount || messages.length} />
          <RollupStat icon={Zap} label="Tokens" value={fmtTokens(conv.tokens)} />
          <RollupStat icon={DollarSign} label="Cost" value={fmtCost(conv.cost)} />
          {conv.avgLatency != null && (
            <RollupStat icon={Clock} label="Avg latency" value={`${conv.avgLatency} ms`} />
          )}
          {conv.model && <RollupStat icon={Cpu} label="Model" value={conv.model} />}
        </div>
      )}

      {/* Transcript */}
      <div className="flex-1 overflow-y-auto px-5 py-5 max-h-[520px] scrollbar-thin">
        {/* Date divider */}
        <div className="flex justify-center mb-5">
          <span className="px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] text-[#64748B] font-medium">
            {conv.date || new Date().toLocaleDateString()}
          </span>
        </div>

        <div className="space-y-4">
          {msgLoading ? (
            <div className="flex items-center justify-center gap-2 text-[#94A3B8] text-sm py-8">
              <Loader2 size={15} className="animate-spin" /> Loading transcript…
            </div>
          ) : messages.length > 0 ? (
            messages.map((m, i) => <MessageBubble key={m.id || i} message={m} />)
          ) : msgError ? (
            <p className="text-center text-red-500 text-sm py-8">{msgError}</p>
          ) : (
            <p className="text-center text-[#94A3B8] text-sm py-8">No messages in this conversation yet.</p>
          )}
        </div>
      </div>

      {/* Add note */}
      <div className="px-5 py-3 border-t border-[#E2E8F0] flex items-center gap-3">
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Type a note..."
          data-testid="conv-note-input"
          className="flex-1 px-4 py-2.5 rounded-xl border border-[#E2E8F0] bg-white text-[13px] placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10"
        />
        <button
          className="px-4 py-2.5 rounded-xl bg-[#EFF6FF] text-[#2563EB] text-[13px] font-semibold hover:bg-[#DBEAFE]"
          data-testid="conv-note-add"
        >
          Add Note
        </button>
      </div>
    </div>
  );
}

function RollupStat({ icon: Icon, label, value }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[#64748B]">
      <Icon size={12} className="text-[#94A3B8]" />
      <span className="text-[#94A3B8]">{label}</span>
      <span className="font-semibold text-[#0F172A]">{value}</span>
    </span>
  );
}

function MessageBubble({ message }) {
  const isCustomer = (message.sender || message.who) === "customer";
  const text = message.message ?? message.text ?? "";
  const time =
    message.time ||
    (message.created_at
      ? new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "");
  const tokens = message.total_tokens ?? message.token_count ?? 0;
  const cost = message.cost_usd ?? 0;
  const latency = message.latency_ms ?? null;
  const model = message.model || null;
  const confidence = message.confidence ?? null;
  const grounded = message.grounded;
  const citations = Array.isArray(message.citations) ? message.citations : [];
  const hasObs = !isCustomer && (tokens > 0 || cost > 0 || latency != null || model);

  return (
    <div className={`flex items-start gap-3 ${isCustomer ? "flex-row-reverse" : ""}`}>
      <div
        className={`size-9 rounded-full grid place-items-center shrink-0 ${
          isCustomer ? "bg-[#DBEAFE] text-[#2563EB]" : "bg-[#EFF6FF] text-[#2563EB]"
        }`}
      >
        {isCustomer ? <User size={15} /> : <Bot size={15} />}
      </div>
      <div className={`max-w-[72%] ${isCustomer ? "items-end text-right" : "items-start text-left"} flex flex-col`}>
        <p className="text-[10.5px] text-[#94A3B8] mb-1 font-medium">
          {isCustomer ? "Customer" : "Agent"}
          {time && (
            <>
              <span className="mx-1.5 text-[#CBD5E1]">·</span>
              {time}
            </>
          )}
        </p>
        <div
          className={`px-4 py-2.5 rounded-2xl text-[13.5px] leading-relaxed ${
            isCustomer
              ? "bg-[#2563EB] text-white rounded-tr-md"
              : "bg-[#F8FAFC] text-[#0F172A] rounded-tl-md border border-[#E2E8F0]"
          }`}
        >
          {text}
        </div>

        {/* Citations */}
        {!isCustomer && citations.length > 0 && (
          <div className="mt-1.5 flex flex-col gap-1 items-start">
            {citations.slice(0, 3).map((c, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 max-w-full text-[10.5px] text-[#475569] bg-[#EFF6FF] border border-[#DBEAFE] rounded-md px-2 py-0.5"
                title={c.title || c.source || c.text || ""}
              >
                <Quote size={10} className="text-[#2563EB] shrink-0" />
                <span className="truncate">{c.title || c.source || c.text || `Source ${i + 1}`}</span>
              </span>
            ))}
          </div>
        )}

        {/* Per-message observability */}
        {hasObs && (
          <div className="mt-1.5 flex items-center gap-2 flex-wrap text-[10px] text-[#94A3B8]">
            {model && (
              <span className="inline-flex items-center gap-1 bg-[#F1F5F9] rounded px-1.5 py-0.5">
                <Cpu size={10} /> {model}
              </span>
            )}
            {tokens > 0 && (
              <span className="inline-flex items-center gap-1">
                <Zap size={10} /> {fmtTokens(tokens)} tok
              </span>
            )}
            {cost > 0 && (
              <span className="inline-flex items-center gap-1">
                <DollarSign size={10} /> {fmtCost(cost)}
              </span>
            )}
            {latency != null && (
              <span className="inline-flex items-center gap-1">
                <Clock size={10} /> {latency} ms
              </span>
            )}
            {grounded != null && (
              <span
                className={`inline-flex items-center gap-1 ${
                  grounded ? "text-[#16A34A]" : "text-[#D97706]"
                }`}
                title={grounded ? "Answer grounded in knowledge base" : "Not grounded in knowledge base"}
              >
                <ShieldCheck size={10} /> {grounded ? "Grounded" : "Ungrounded"}
              </span>
            )}
            {confidence != null && (
              <span className="inline-flex items-center gap-1">{Math.round(confidence * 100)}% conf.</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
