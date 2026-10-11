import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Search,
  Loader2,
  FileText,
  Globe,
  ExternalLink,
  ShieldCheck,
  Send,
  Database,
  Layers,
  BookOpen,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

const SOURCE_FILTERS = [
  { value: "all", label: "All sources" },
  { value: "document", label: "Documents" },
  { value: "website", label: "Websites" },
];

function confidenceTone(c) {
  if (c >= 0.7) return { label: "High confidence", cls: "text-green-700", bar: "#059669" };
  if (c >= 0.4) return { label: "Medium confidence", cls: "text-amber-700", bar: "#D97706" };
  return { label: "Low confidence", cls: "text-red-700", bar: "#DC2626" };
}

export default function KnowledgeSearch() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("ask"); // ask | search
  const [sourceFilter, setSourceFilter] = useState("all");
  const [kbs, setKbs] = useState([]);
  const [kbId, setKbId] = useState("");
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [hits, setHits] = useState(null);

  const loadMeta = useCallback(async () => {
    try {
      const [kbRes, srcRes] = await Promise.all([
        api.get("/knowledge-bases", { params: { limit: 100 } }),
        api.get("/rag/sources"),
      ]);
      setKbs(kbRes.data.items || []);
      setStats(srcRes.data);
    } catch {
      /* non-fatal */
    }
  }, []);

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  const run = useCallback(
    async (q) => {
      const text = (q ?? query).trim();
      if (!text) return;
      setLoading(true);
      setAnswer(null);
      setHits(null);
      const body = {
        query: text,
        top_k: mode === "ask" ? 5 : 10,
        ...(kbId ? { knowledge_base_ids: [kbId] } : {}),
        ...(sourceFilter !== "all" ? { source_types: [sourceFilter] } : {}),
      };
      try {
        if (mode === "ask") {
          const { data } = await api.post("/rag/query", body);
          setAnswer(data);
        } else {
          const { data } = await api.post("/rag/search", body);
          setHits(data.hits || []);
        }
      } catch (err) {
        toast.error(formatApiError(err.response?.data?.detail));
      } finally {
        setLoading(false);
      }
    },
    [query, mode, kbId, sourceFilter]
  );

  const kpis = useMemo(
    () => [
      { icon: BookOpen, color: "#2563EB", label: "Knowledge Bases", value: stats?.knowledge_bases ?? "—" },
      { icon: FileText, color: "#0891B2", label: "Documents", value: stats?.documents ?? "—" },
      { icon: Globe, color: "#0EA5E9", label: "Websites", value: stats?.websites ?? "—" },
      { icon: Layers, color: "#059669", label: "Chunks", value: stats?.chunks ?? "—" },
    ],
    [stats]
  );

  return (
    <div className="space-y-6" data-testid="rag-search-page">
      <div>
        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0F172A]">
          Ask Your Knowledge
        </h2>
        <p className="text-sm text-[#64748B] mt-1">
          Grounded answers and hybrid search across your documents and crawled websites.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="bg-white border border-[#E2E8F0] rounded-2xl p-4">
            <div className="flex items-center gap-3">
              <div
                className="h-10 w-10 rounded-xl flex items-center justify-center"
                style={{ background: `${k.color}14`, color: k.color }}
              >
                <k.icon size={18} />
              </div>
              <div>
                <div className="text-2xl font-bold text-[#0F172A]">{k.value}</div>
                <div className="text-xs text-[#64748B]">{k.label}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Search bar */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-4 space-y-3">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()}
              placeholder="Ask a question or search your knowledge…"
              aria-label="Search knowledge base"
              className="w-full pl-11 pr-3 py-3 rounded-xl border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/20"
            />
          </div>
          <button
            onClick={() => run()}
            disabled={loading || !query.trim()}
            className="inline-flex items-center gap-2 px-5 py-3 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-50 text-white text-sm font-semibold"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : mode === "ask" ? <Send size={16} /> : <Search size={16} />}
            {mode === "ask" ? "Ask" : "Search"}
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-lg border border-[#E2E8F0] p-0.5">
            {["ask", "search"].map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize ${
                  mode === m ? "bg-[#2563EB] text-white" : "text-[#64748B] hover:text-[#475569]"
                }`}
              >
                {m === "ask" ? "Ask AI" : "Hybrid search"}
              </button>
            ))}
          </div>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-[#E2E8F0] text-xs text-[#475569]"
          >
            {SOURCE_FILTERS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <select
            value={kbId}
            onChange={(e) => setKbId(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-[#E2E8F0] text-xs text-[#475569]"
          >
            <option value="">All knowledge bases</option>
            {kbs.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center justify-center py-16 text-[#94A3B8]"
          >
            <Loader2 className="animate-spin" />
          </motion.div>
        ) : answer ? (
          <AnswerView key="answer" answer={answer} onAsk={(q) => { setQuery(q); run(q); }} />
        ) : hits ? (
          <HitsView key="hits" hits={hits} />
        ) : (
          <EmptyState key="empty" />
        )}
      </AnimatePresence>
    </div>
  );
}

function SourceIcon({ type }) {
  return type === "website" ? <Globe size={13} /> : <FileText size={13} />;
}

function AnswerView({ answer, onAsk }) {
  const tone = confidenceTone(answer.confidence || 0);
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-4"
    >
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6">
        <div className="flex items-center justify-between mb-3">
          <div className="inline-flex items-center gap-2 text-sm font-semibold text-[#0F172A]">
            <Sparkles size={16} className="text-[#2563EB]" /> Answer
          </div>
          <div className="flex items-center gap-2">
            {!answer.grounded && (
              <span className="text-[11px] px-2 py-0.5 rounded-md bg-amber-50 text-amber-700">
                Extractive fallback
              </span>
            )}
            <span className={`inline-flex items-center gap-1 text-xs font-medium ${tone.cls}`}>
              <ShieldCheck size={13} /> {tone.label}
            </span>
          </div>
        </div>
        <div className="h-1.5 w-full bg-[#F1F5F9] rounded-full overflow-hidden mb-4">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${Math.round((answer.confidence || 0) * 100)}%`, background: tone.bar }}
          />
        </div>
        <p className="text-[15px] leading-relaxed text-[#1E293B] whitespace-pre-wrap">
          {answer.answer}
        </p>
      </div>

      {answer.sources?.length > 0 && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5">
          <div className="text-sm font-semibold text-[#0F172A] mb-3 inline-flex items-center gap-2">
            <Database size={15} /> Sources ({answer.sources.length})
          </div>
          <div className="space-y-2">
            {answer.sources.map((s, i) => (
              <SourceRow key={i} index={i + 1} source={s} />
            ))}
          </div>
        </div>
      )}

      {answer.related_questions?.length > 0 && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5">
          <div className="text-sm font-semibold text-[#0F172A] mb-3">Related questions</div>
          <div className="flex flex-wrap gap-2">
            {answer.related_questions.map((q, i) => (
              <button
                key={i}
                onClick={() => onAsk(q)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-[#E2E8F0] text-xs text-[#475569] hover:border-[#2563EB] hover:text-[#2563EB] hover:bg-[#EFF6FF]"
              >
                {q} <ArrowRight size={12} />
              </button>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

function SourceRow({ index, source }) {
  const isWeb = source.type === "website";
  const href = isWeb ? source.url : null;
  const Wrapper = href ? "a" : "div";
  return (
    <Wrapper
      {...(href ? { href, target: "_blank", rel: "noreferrer" } : {})}
      className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] group"
    >
      <span className="h-6 w-6 shrink-0 rounded-md bg-[#EFF6FF] text-[#2563EB] text-xs font-bold inline-flex items-center justify-center">
        {index}
      </span>
      <span className="text-[#64748B]">
        <SourceIcon type={source.type} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-[#0F172A] truncate">
          {source.title || source.document || source.url}
        </div>
        {(source.url || source.page != null || source.section) && (
          <div className="text-[11px] text-[#64748B] truncate">
            {isWeb ? source.url : [source.section, source.page != null ? `p.${source.page}` : null].filter(Boolean).join(" · ")}
          </div>
        )}
      </div>
      {source.score != null && (
        <span className="text-[11px] text-[#94A3B8] shrink-0">{Math.round(source.score * 100)}%</span>
      )}
      {href && <ExternalLink size={13} className="text-[#94A3B8] group-hover:text-[#2563EB] shrink-0" />}
    </Wrapper>
  );
}

function HitsView({ hits }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="space-y-3"
    >
      {hits.length === 0 ? (
        <EmptyState noData />
      ) : (
        hits.map((h, i) => (
          <div key={i} className="bg-white border border-[#E2E8F0] rounded-2xl p-5">
            <div className="flex items-center justify-between gap-3 mb-2">
              <div className="inline-flex items-center gap-2 min-w-0">
                <span className="text-[#64748B]">
                  <SourceIcon type={h.source_type} />
                </span>
                <span className="text-sm font-medium text-[#0F172A] truncate">
                  {h.title || h.url}
                </span>
                {h.url && (
                  <a href={h.url} target="_blank" rel="noreferrer" className="text-[#94A3B8] hover:text-[#2563EB]">
                    <ExternalLink size={12} />
                  </a>
                )}
              </div>
              {h.score != null && (
                <span className="text-xs font-semibold text-[#2563EB] shrink-0">
                  {Math.round(h.score * 100)}%
                </span>
              )}
            </div>
            <p className="text-sm text-[#475569] leading-relaxed line-clamp-4">{h.content}</p>
            {h.components && (
              <div className="flex flex-wrap gap-2 mt-3">
                {h.components.vector != null && (
                  <Chip label="vector" value={h.components.vector} />
                )}
                {h.components.lexical != null && (
                  <Chip label="lexical" value={h.components.lexical} />
                )}
              </div>
            )}
          </div>
        ))
      )}
    </motion.div>
  );
}

function Chip({ label, value }) {
  return (
    <span className="text-[10px] px-2 py-0.5 rounded-md bg-[#F1F5F9] text-[#64748B]">
      {label}: {Number(value).toFixed(2)}
    </span>
  );
}

function EmptyState({ noData }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="bg-white border border-dashed border-[#CBD5E1] rounded-2xl p-12 text-center"
    >
      <Sparkles size={40} className="mx-auto text-[#CBD5E1]" />
      <h3 className="mt-3 text-lg font-semibold text-[#0F172A]">
        {noData ? "No matches found" : "Ask anything about your knowledge"}
      </h3>
      <p className="text-sm text-[#64748B] mt-1">
        {noData
          ? "Try a different query or broaden your source filter."
          : "Answers are grounded in your documents and crawled websites, with citations."}
      </p>
    </motion.div>
  );
}
