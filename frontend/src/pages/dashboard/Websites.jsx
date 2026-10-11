import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Globe,
  Plus,
  Search,
  Trash2,
  X,
  RefreshCw,
  Pause,
  Play,
  Ban,
  Loader2,
  FileText,
  Layers,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  ListTree,
  ScrollText,
  BarChart3,
  ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

const STATUS = {
  pending: { label: "Pending", cls: "bg-[#F1F5F9] text-[#64748B]", icon: Clock },
  crawling: { label: "Crawling", cls: "bg-blue-50 text-blue-700", icon: Loader2, spin: true },
  ready: { label: "Ready", cls: "bg-green-50 text-green-700", icon: CheckCircle2 },
  failed: { label: "Failed", cls: "bg-red-50 text-red-700", icon: AlertTriangle },
  paused: { label: "Paused", cls: "bg-amber-50 text-amber-700", icon: Pause },
};

const CRAWL_MODES = [
  { value: "entire", label: "Entire site", hint: "Follow links across the whole domain" },
  { value: "single", label: "Single page", hint: "Only the URL you provide" },
  { value: "folder", label: "Folder / path", hint: "Only pages under the URL's path" },
  { value: "sitemap", label: "Sitemap", hint: "Use the site's sitemap.xml" },
];

const FREQUENCIES = ["manual", "hourly", "daily", "weekly", "monthly"];

function StatusBadge({ status }) {
  const s = STATUS[status] || STATUS.pending;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${s.cls}`}>
      <Icon size={12} className={s.spin ? "animate-spin" : ""} />
      {s.label}
    </span>
  );
}

export default function Websites() {
  const [items, setItems] = useState([]);
  const [kbs, setKbs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState(null);
  const pollRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const params = search ? { q: search } : undefined;
      const [{ data: list }, { data: kbList }] = await Promise.all([
        api.get("/websites", { params }),
        api.get("/knowledge-bases", { params: { limit: 100 } }),
      ]);
      setItems(list.items || []);
      setKbs(kbList.items || []);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    load();
  }, [load]);

  // Live-poll while any site is crawling.
  useEffect(() => {
    const anyCrawling = items.some((w) => w.status === "crawling");
    if (anyCrawling && !pollRef.current) {
      pollRef.current = setInterval(load, 3000);
    } else if (!anyCrawling && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current && !anyCrawling) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [items, load]);

  useEffect(() => () => pollRef.current && clearInterval(pollRef.current), []);

  const act = async (w, action) => {
    try {
      await api.post(`/websites/${w.id}/${action}`);
      toast.success(`${action[0].toUpperCase()}${action.slice(1)} triggered`);
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const remove = async (w) => {
    if (!window.confirm(`Delete "${w.name}" and remove its pages from search?`)) return;
    try {
      await api.delete(`/websites/${w.id}`);
      toast.success("Website removed");
      if (selected?.id === w.id) setSelected(null);
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const kpis = useMemo(() => {
    const total = items.length;
    const ready = items.filter((w) => w.status === "ready").length;
    const crawling = items.filter((w) => w.status === "crawling").length;
    const pages = items.reduce((a, w) => a + (w.pages_count || 0), 0);
    return [
      { icon: Globe, color: "#2563EB", label: "Websites", value: total },
      { icon: CheckCircle2, color: "#059669", label: "Ready", value: ready },
      { icon: Loader2, color: "#0EA5E9", label: "Crawling", value: crawling },
      { icon: FileText, color: "#0891B2", label: "Pages Indexed", value: pages },
    ];
  }, [items]);

  return (
    <div className="space-y-6" data-testid="websites-page">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0F172A]">
            Website Crawling
          </h2>
          <p className="text-sm text-[#64748B] mt-1">
            Turn any website into searchable knowledge for your agents.
          </p>
        </div>
        <button
          onClick={() => setCreating(true)}
          data-testid="website-create-btn"
          disabled={kbs.length === 0}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-50 text-white text-sm font-semibold shadow-[0_8px_24px_-8px_rgba(37,99,235,0.5)]"
          title={kbs.length === 0 ? "Create a knowledge base first" : "Add a website"}
        >
          <Plus size={16} /> Add Website
        </button>
      </div>

      {/* KPIs */}
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

      {/* Search */}
      <div className="relative max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search websites…"
          aria-label="Search websites"
          className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/20"
        />
      </div>

      {/* List */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-[#94A3B8]">
          <Loader2 className="animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white border border-dashed border-[#CBD5E1] rounded-2xl p-12 text-center">
          <Globe size={40} className="mx-auto text-[#CBD5E1]" />
          <h3 className="mt-3 text-lg font-semibold text-[#0F172A]">No websites yet</h3>
          <p className="text-sm text-[#64748B] mt-1">
            {kbs.length === 0
              ? "Create a knowledge base first, then add a website to crawl."
              : "Add a website and we'll crawl, extract and embed its pages."}
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {items.map((w) => (
            <WebsiteCard
              key={w.id}
              website={w}
              onOpen={() => setSelected(w)}
              onAct={act}
              onRemove={remove}
            />
          ))}
        </div>
      )}

      <AnimatePresence>
        {creating && (
          <CreateModal
            kbs={kbs}
            onClose={() => setCreating(false)}
            onCreated={() => {
              setCreating(false);
              load();
            }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {selected && (
          <DetailDrawer
            website={selected}
            onClose={() => setSelected(null)}
            onChanged={load}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function WebsiteCard({ website: w, onOpen, onAct, onRemove }) {
  const job = w.status === "crawling";
  return (
    <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 hover:shadow-[0_8px_30px_-12px_rgba(15,23,42,0.15)] transition-shadow">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-base font-semibold text-[#0F172A] truncate">{w.name}</h3>
            <StatusBadge status={w.status} />
            <span className="text-[11px] px-2 py-0.5 rounded-md bg-[#F1F5F9] text-[#64748B] capitalize">
              {w.crawl_mode}
            </span>
          </div>
          <a
            href={w.base_url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 text-xs text-[#2563EB] hover:underline mt-1"
          >
            {w.base_url} <ExternalLink size={11} />
          </a>
          <div className="flex items-center gap-4 mt-3 text-xs text-[#64748B]">
            <span className="inline-flex items-center gap-1">
              <FileText size={13} /> {w.pages_count || 0} pages
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock size={13} />{" "}
              {w.last_crawled_at
                ? new Date(w.last_crawled_at).toLocaleString()
                : "never crawled"}
            </span>
          </div>
          {w.error && (
            <div className="mt-2 text-xs text-red-600 bg-red-50 rounded-lg px-2.5 py-1.5">
              {w.error}
            </div>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {!job && (
            <IconBtn title="Crawl now" onClick={() => onAct(w, "crawl")}>
              <RefreshCw size={15} />
            </IconBtn>
          )}
          {job && (
            <IconBtn title="Cancel crawl" danger onClick={() => onAct(w, "cancel")}>
              <Ban size={15} />
            </IconBtn>
          )}
          {w.status === "paused" ? (
            <IconBtn title="Resume" onClick={() => onAct(w, "resume")}>
              <Play size={15} />
            </IconBtn>
          ) : (
            <IconBtn title="Pause" onClick={() => onAct(w, "pause")}>
              <Pause size={15} />
            </IconBtn>
          )}
          <IconBtn title="Details" onClick={onOpen}>
            <ChevronRight size={16} />
          </IconBtn>
          <IconBtn title="Delete" danger onClick={() => onRemove(w)}>
            <Trash2 size={15} />
          </IconBtn>
        </div>
      </div>
      {job && (
        <div className="mt-4 h-1.5 w-full bg-[#EFF6FF] rounded-full overflow-hidden">
          <div className="h-full w-1/3 bg-[#2563EB] rounded-full animate-[pulse_1.4s_ease-in-out_infinite]" />
        </div>
      )}
    </div>
  );
}

function IconBtn({ children, onClick, title, danger }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`h-9 w-9 inline-flex items-center justify-center rounded-lg border border-[#E2E8F0] hover:bg-[#F8FAFC] ${
        danger ? "text-red-600 hover:bg-red-50 hover:border-red-200" : "text-[#475569]"
      }`}
    >
      {children}
    </button>
  );
}

function CreateModal({ kbs, onClose, onCreated }) {
  const [form, setForm] = useState({
    base_url: "",
    name: "",
    knowledge_base_id: kbs[0]?.id || "",
    crawl_mode: "entire",
    max_depth: 3,
    max_pages: 200,
    crawl_frequency: "manual",
    respect_robots: true,
    render_js: false,
    crawl_delay_ms: 0,
    max_concurrency: 0,
  });
  const [submitting, setSubmitting] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.base_url.trim()) return toast.error("Enter a website URL");
    if (!form.knowledge_base_id) return toast.error("Select a knowledge base");
    setSubmitting(true);
    try {
      await api.post("/websites?start=true", {
        ...form,
        max_depth: Number(form.max_depth),
        max_pages: Number(form.max_pages),
        crawl_delay_ms: Number(form.crawl_delay_ms),
        max_concurrency: Number(form.max_concurrency),
      });
      toast.success("Website added — crawl started");
      onCreated();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.form
        initial={{ scale: 0.96, y: 8 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.96, y: 8 }}
        onClick={(e) => e.stopPropagation()}
        onSubmit={submit}
        className="bg-white rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8F0]">
          <h3 className="text-lg font-semibold text-[#0F172A]">Add Website</h3>
          <button type="button" onClick={onClose} className="text-[#94A3B8] hover:text-[#475569]">
            <X size={18} />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <Field label="Website URL">
            <input
              autoFocus
              value={form.base_url}
              onChange={(e) => set("base_url", e.target.value)}
              placeholder="https://docs.example.com"
              className="input"
            />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Name (optional)">
              <input
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="auto from domain"
                className="input"
              />
            </Field>
            <Field label="Knowledge Base">
              <select
                value={form.knowledge_base_id}
                onChange={(e) => set("knowledge_base_id", e.target.value)}
                className="input"
              >
                {kbs.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Crawl scope">
            <div className="grid grid-cols-2 gap-2">
              {CRAWL_MODES.map((m) => (
                <button
                  type="button"
                  key={m.value}
                  onClick={() => set("crawl_mode", m.value)}
                  className={`text-left px-3 py-2 rounded-xl border text-sm ${
                    form.crawl_mode === m.value
                      ? "border-[#2563EB] bg-[#EFF6FF]"
                      : "border-[#E2E8F0] hover:bg-[#F8FAFC]"
                  }`}
                >
                  <div className="font-medium text-[#0F172A]">{m.label}</div>
                  <div className="text-[11px] text-[#64748B]">{m.hint}</div>
                </button>
              ))}
            </div>
          </Field>
          <div className="grid grid-cols-3 gap-4">
            <Field label="Max depth">
              <input
                type="number"
                min={0}
                max={10}
                value={form.max_depth}
                onChange={(e) => set("max_depth", e.target.value)}
                className="input"
              />
            </Field>
            <Field label="Max pages">
              <input
                type="number"
                min={1}
                max={100000}
                value={form.max_pages}
                onChange={(e) => set("max_pages", e.target.value)}
                className="input"
              />
            </Field>
            <Field label="Frequency">
              <select
                value={form.crawl_frequency}
                onChange={(e) => set("crawl_frequency", e.target.value)}
                className="input capitalize"
              >
                {FREQUENCIES.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <label className="flex items-center gap-2 text-sm text-[#475569]">
            <input
              type="checkbox"
              checked={form.respect_robots}
              onChange={(e) => set("respect_robots", e.target.checked)}
            />
            Respect robots.txt
          </label>

          {/* Distributed engine tuning */}
          <div className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-3 space-y-3">
            <div className="text-xs font-semibold text-[#475569] uppercase tracking-wide">
              Crawler performance
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Politeness delay (ms)">
                <input
                  type="number"
                  min={0}
                  max={60000}
                  value={form.crawl_delay_ms}
                  onChange={(e) => set("crawl_delay_ms", e.target.value)}
                  className="input"
                  data-testid="website-crawl-delay"
                />
              </Field>
              <Field label="Workers (0 = auto)">
                <input
                  type="number"
                  min={0}
                  max={16}
                  value={form.max_concurrency}
                  onChange={(e) => set("max_concurrency", e.target.value)}
                  className="input"
                  data-testid="website-max-concurrency"
                />
              </Field>
            </div>
            <label className="flex items-center gap-2 text-sm text-[#475569]">
              <input
                type="checkbox"
                checked={form.render_js}
                onChange={(e) => set("render_js", e.target.checked)}
                data-testid="website-render-js"
              />
              Render JavaScript (headless browser when available)
            </label>
          </div>
        </div>
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-[#E2E8F0]">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-[#E2E8F0] text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-50 text-white text-sm font-semibold"
          >
            {submitting && <Loader2 size={15} className="animate-spin" />} Start Crawl
          </button>
        </div>
      </motion.form>
    </motion.div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-[#475569] mb-1.5">{label}</span>
      {children}
    </label>
  );
}

function DetailDrawer({ website, onClose, onChanged }) {
  const [tab, setTab] = useState("pages");
  const [analytics, setAnalytics] = useState(null);
  const [pages, setPages] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const [a, p, j] = await Promise.all([
        api.get(`/websites/${website.id}/analytics`),
        api.get(`/websites/${website.id}/pages`, { params: { limit: 100 } }),
        api.get(`/websites/${website.id}/jobs`, { params: { limit: 10 } }),
      ]);
      setAnalytics(a.data);
      setPages(p.data.items || []);
      setJobs(j.data.items || []);
      const lastJob = j.data.items?.[0];
      if (lastJob) {
        const l = await api.get(`/websites/${website.id}/jobs/${lastJob.id}/logs`, {
          params: { limit: 300 },
        });
        setLogs(l.data.items || []);
      }
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, [website.id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const lastJob = jobs[0];
    const running = lastJob && !["completed", "failed", "cancelled"].includes(lastJob.status);
    if (running && !pollRef.current) {
      pollRef.current = setInterval(() => {
        load();
        onChanged?.();
      }, 3000);
    } else if (!running && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current && !running) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [jobs, load, onChanged]);

  useEffect(() => () => pollRef.current && clearInterval(pollRef.current), []);

  const lastJob = jobs[0];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/40 flex justify-end"
      onClick={onClose}
    >
      <motion.div
        initial={{ x: 40, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 40, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-[#F8FAFC] w-full max-w-2xl h-full overflow-y-auto shadow-2xl"
      >
        <div className="sticky top-0 bg-white border-b border-[#E2E8F0] px-6 py-4 flex items-center justify-between z-10">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold text-[#0F172A] truncate">{website.name}</h3>
              <StatusBadge status={website.status} />
            </div>
            <a
              href={website.base_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-[#2563EB] hover:underline inline-flex items-center gap-1"
            >
              {website.base_url} <ExternalLink size={11} />
            </a>
          </div>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-[#475569]">
            <X size={18} />
          </button>
        </div>

        {/* analytics strip */}
        {analytics && (
          <div className="grid grid-cols-4 gap-px bg-[#E2E8F0] border-b border-[#E2E8F0]">
            {[
              { label: "Indexed", value: analytics.pages_indexed },
              { label: "Skipped", value: analytics.pages_skipped },
              { label: "Failed", value: analytics.pages_failed },
              { label: "Chunks", value: analytics.chunks_total },
            ].map((s) => (
              <div key={s.label} className="bg-white px-4 py-3 text-center">
                <div className="text-xl font-bold text-[#0F172A]">{s.value}</div>
                <div className="text-[11px] text-[#64748B]">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* tabs */}
        <div className="flex gap-1 px-4 pt-3 border-b border-[#E2E8F0] bg-white">
          {[
            { id: "pages", label: "Pages", icon: ListTree },
            { id: "logs", label: "Logs", icon: ScrollText },
            { id: "analytics", label: "Analytics", icon: BarChart3 },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 -mb-px ${
                tab === t.id
                  ? "border-[#2563EB] text-[#2563EB]"
                  : "border-transparent text-[#64748B] hover:text-[#475569]"
              }`}
            >
              <t.icon size={14} /> {t.label}
            </button>
          ))}
        </div>

        <div className="p-4">
          {loading ? (
            <div className="flex justify-center py-16 text-[#94A3B8]">
              <Loader2 className="animate-spin" />
            </div>
          ) : tab === "pages" ? (
            <div className="space-y-2">
              {pages.length === 0 && (
                <p className="text-sm text-[#64748B] text-center py-8">No pages indexed yet.</p>
              )}
              {pages.map((p) => (
                <div
                  key={p.id}
                  className="bg-white border border-[#E2E8F0] rounded-xl px-4 py-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-[#0F172A] truncate">
                        {p.title || p.url}
                      </div>
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-[#2563EB] hover:underline truncate block"
                      >
                        {p.url}
                      </a>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {p.classification && (
                        <span className="text-[10px] px-2 py-0.5 rounded-md bg-[#F1F5F9] text-[#64748B] capitalize">
                          {p.classification}
                        </span>
                      )}
                      <span className="text-xs text-[#64748B] inline-flex items-center gap-1">
                        <Layers size={12} /> {p.chunk_count || 0}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : tab === "logs" ? (
            <div className="bg-[#0F172A] rounded-xl p-3 font-mono text-xs max-h-[60vh] overflow-y-auto">
              {logs.length === 0 && <div className="text-[#64748B]">No logs.</div>}
              {logs.map((l) => (
                <div key={l.id} className="flex gap-2 py-0.5">
                  <span
                    className={
                      l.level === "error"
                        ? "text-red-400"
                        : l.level === "warn"
                        ? "text-amber-400"
                        : "text-[#64748B]"
                    }
                  >
                    [{l.status || l.level}]
                  </span>
                  <span className="text-[#CBD5E1] break-all">{l.message}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-white border border-[#E2E8F0] rounded-xl p-4">
                <h4 className="text-sm font-semibold text-[#0F172A] mb-3">Pages by type</h4>
                {analytics && Object.keys(analytics.by_classification || {}).length === 0 ? (
                  <p className="text-sm text-[#64748B]">No classified pages yet.</p>
                ) : (
                  <div className="space-y-2">
                    {Object.entries(analytics?.by_classification || {}).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-2">
                        <span className="text-xs text-[#475569] capitalize w-28">{k}</span>
                        <div className="flex-1 h-2 bg-[#F1F5F9] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#2563EB] rounded-full"
                            style={{
                              width: `${Math.min(
                                100,
                                (v / Math.max(1, analytics.pages_indexed)) * 100
                              )}%`,
                            }}
                          />
                        </div>
                        <span className="text-xs text-[#64748B] w-8 text-right">{v}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {lastJob && (
                <div className="bg-white border border-[#E2E8F0] rounded-xl p-4 text-sm" data-testid="crawl-job-panel">
                  <h4 className="text-sm font-semibold text-[#0F172A] mb-2">Last crawl job</h4>
                  {(() => {
                    const running = !["completed", "failed", "cancelled"].includes(lastJob.status);
                    const done = (lastJob.pages_completed || 0) + (lastJob.pages_failed || 0) + (lastJob.pages_skipped || 0);
                    const total = Math.max(lastJob.pages_total || 0, done);
                    const pct = total ? Math.min(100, Math.round((done / total) * 100)) : 0;
                    return (
                      <>
                        {running && (
                          <div className="mb-3">
                            <div className="flex items-center justify-between text-[11px] text-[#64748B] mb-1">
                              <span>{done} / {total || "?"} pages</span>
                              <span>{pct}%</span>
                            </div>
                            <div className="h-1.5 w-full bg-[#EFF6FF] rounded-full overflow-hidden">
                              <div className="h-full bg-[#2563EB] rounded-full transition-[width] duration-500" style={{ width: `${pct}%` }} />
                            </div>
                          </div>
                        )}
                        <div className="grid grid-cols-2 gap-y-1 text-[#64748B]">
                          <span>Status</span>
                          <span className="text-[#0F172A] capitalize text-right">{lastJob.status}</span>
                          <span>Workers</span>
                          <span className="text-[#0F172A] text-right">{lastJob.worker_count ?? 1}</span>
                          <span>Live concurrency</span>
                          <span className="text-[#0F172A] text-right">{lastJob.concurrency ?? 0}</span>
                          <span>Frontier remaining</span>
                          <span className="text-[#0F172A] text-right" data-testid="crawl-frontier-size">{lastJob.frontier_size ?? 0}</span>
                          <span>Completed</span>
                          <span className="text-[#0F172A] text-right">{lastJob.pages_completed}</span>
                          <span>Failed</span>
                          <span className="text-[#0F172A] text-right">{lastJob.pages_failed}</span>
                          <span>Chunks created</span>
                          <span className="text-[#0F172A] text-right">{lastJob.chunks_created}</span>
                        </div>
                      </>
                    );
                  })()}
                </div>
              )}
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
