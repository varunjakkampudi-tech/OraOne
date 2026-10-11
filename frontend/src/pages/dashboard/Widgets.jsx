import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Code2,
  Plus,
  Search,
  Trash2,
  X,
  Copy,
  Check,
  Loader2,
  MessageSquare,
  Eye,
  EyeOff,
  BarChart3,
  RefreshCw,
  Bot,
  BookOpen,
  Users,
  AlertTriangle,
  ArrowUpRight,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

const STATUS = {
  draft: { label: "Draft", cls: "bg-[#F1F5F9] text-[#64748B]" },
  published: { label: "Published", cls: "bg-green-50 text-green-700" },
  paused: { label: "Paused", cls: "bg-amber-50 text-amber-700" },
};

const TYPES = [
  { value: "bubble", label: "Chat bubble", hint: "Floating launcher in the corner" },
  { value: "popup", label: "Auto popup", hint: "Opens automatically after a delay" },
  { value: "button", label: "Inline button", hint: "Triggered by a page button" },
  { value: "inline", label: "Inline embed", hint: "Rendered within the page" },
  { value: "fullpage", label: "Full page", hint: "Dedicated chat page" },
];

const POSITIONS = [
  { value: "bottom-right", label: "Bottom right" },
  { value: "bottom-left", label: "Bottom left" },
  { value: "inline", label: "Inline" },
];

const PRESET_COLORS = ["#2563EB", "#7C3AED", "#0EA5E9", "#059669", "#DB2777", "#EA580C", "#0F172A"];

function StatusBadge({ status }) {
  const s = STATUS[status] || STATUS.draft;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${s.cls}`}>
      {s.label}
    </span>
  );
}

function CopyButton({ text, label = "Copy", className = "" }) {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setDone(false), 1500);
    } catch {
      toast.error("Could not copy");
    }
  };
  return (
    <button
      onClick={copy}
      className={`inline-flex items-center gap-1.5 text-xs font-medium ${className}`}
      type="button"
    >
      {done ? <Check size={13} /> : <Copy size={13} />}
      {done ? "Copied" : label}
    </button>
  );
}

export default function Widgets() {
  const [items, setItems] = useState([]);
  const [agents, setAgents] = useState([]);
  const [kbs, setKbs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(null); // widget object or "new"
  const [analytics, setAnalytics] = useState(null); // widget object

  const load = useCallback(async () => {
    try {
      const params = search ? { q: search } : undefined;
      const [{ data: list }, { data: agentList }, { data: kbList }] = await Promise.all([
        api.get("/widgets", { params }),
        api.get("/agents", { params: { limit: 100 } }),
        api.get("/knowledge-bases", { params: { limit: 100 } }),
      ]);
      setItems(list.items || []);
      setAgents(agentList.items || []);
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

  const togglePublish = async (w) => {
    const publish = w.status !== "published";
    try {
      await api.post(`/widgets/${w.id}/publish`, null, { params: { publish } });
      toast.success(publish ? "Widget published" : "Widget unpublished");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const regenerate = async (w) => {
    if (!window.confirm(`Regenerate the embed key for "${w.name}"? The old snippet will stop working.`)) return;
    try {
      await api.post(`/widgets/${w.id}/regenerate-key`);
      toast.success("Embed key regenerated");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const remove = async (w) => {
    if (!window.confirm(`Delete "${w.name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/widgets/${w.id}`);
      toast.success("Widget deleted");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const kpis = useMemo(() => {
    const total = items.length;
    const live = items.filter((w) => w.status === "published").length;
    const sessions = items.reduce((a, w) => a + (w.sessions_count || 0), 0);
    return [
      { icon: Code2, color: "#2563EB", label: "Widgets", value: total },
      { icon: Eye, color: "#059669", label: "Published", value: live },
      { icon: MessageSquare, color: "#7C3AED", label: "Sessions", value: sessions },
    ];
  }, [items]);

  return (
    <div className="space-y-6" data-testid="widgets-page">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0F172A]">Website Widgets</h2>
          <p className="text-sm text-[#64748B] mt-1">
            Embed your AI assistant on any website with a single line of code.
          </p>
        </div>
        <button
          onClick={() => setEditing("new")}
          data-testid="widget-create-btn"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_8px_24px_-8px_rgba(37,99,235,0.5)]"
        >
          <Plus size={16} /> New Widget
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
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
          placeholder="Search widgets…"
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
          <Code2 size={40} className="mx-auto text-[#CBD5E1]" />
          <h3 className="mt-3 text-lg font-semibold text-[#0F172A]">No widgets yet</h3>
          <p className="text-sm text-[#64748B] mt-1">
            Create a widget, connect an agent and knowledge base, then drop the snippet on your site.
          </p>
          <button
            onClick={() => setEditing("new")}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#2563EB] text-white text-sm font-semibold"
          >
            <Plus size={15} /> New Widget
          </button>
        </div>
      ) : (
        <div className="grid gap-4">
          {items.map((w) => (
            <WidgetCard
              key={w.id}
              widget={w}
              agents={agents}
              kbs={kbs}
              onEdit={() => setEditing(w)}
              onAnalytics={() => setAnalytics(w)}
              onTogglePublish={() => togglePublish(w)}
              onRegenerate={() => regenerate(w)}
              onRemove={() => remove(w)}
            />
          ))}
        </div>
      )}

      <AnimatePresence>
        {editing && (
          <WidgetModal
            widget={editing === "new" ? null : editing}
            agents={agents}
            kbs={kbs}
            onClose={() => setEditing(null)}
            onSaved={() => {
              setEditing(null);
              load();
            }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {analytics && (
          <AnalyticsDrawer widget={analytics} onClose={() => setAnalytics(null)} />
        )}
      </AnimatePresence>
    </div>
  );
}

function WidgetCard({ widget: w, agents, kbs, onEdit, onAnalytics, onTogglePublish, onRegenerate, onRemove }) {
  const agent = agents.find((a) => a.id === w.agent_id);
  const kb = kbs.find((k) => k.id === w.knowledge_base_id);
  const color = w.theme?.primary_color || "#2563EB";
  const published = w.status === "published";
  return (
    <div className="bg-white border border-[#E2E8F0] rounded-2xl p-5 hover:shadow-[0_8px_30px_-12px_rgba(15,23,42,0.15)] transition-shadow">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="h-7 w-7 rounded-lg flex items-center justify-center" style={{ background: `${color}1A`, color }}>
              <Sparkles size={14} />
            </span>
            <h3 className="text-base font-semibold text-[#0F172A] truncate">{w.name}</h3>
            <StatusBadge status={w.status} />
            <span className="text-[11px] px-2 py-0.5 rounded-md bg-[#F1F5F9] text-[#64748B] capitalize">
              {(w.widget_type || "bubble").replace("-", " ")}
            </span>
          </div>
          <div className="flex items-center gap-4 mt-3 text-xs text-[#64748B] flex-wrap">
            <span className="inline-flex items-center gap-1">
              <Bot size={13} /> {agent ? agent.name : "No agent"}
            </span>
            <span className="inline-flex items-center gap-1">
              <BookOpen size={13} /> {kb ? kb.name : "No knowledge base"}
            </span>
            <span className="inline-flex items-center gap-1">
              <MessageSquare size={13} /> {w.sessions_count || 0} sessions
            </span>
            {w.domains?.length > 0 && (
              <span className="inline-flex items-center gap-1">
                <Users size={13} /> {w.domains.length} domain{w.domains.length > 1 ? "s" : ""}
              </span>
            )}
          </div>

          {/* Embed snippet */}
          <div className="mt-4 bg-[#0F172A] rounded-xl p-3 flex items-start gap-3">
            <code className="text-[11px] leading-relaxed text-[#E2E8F0] break-all flex-1 font-mono">
              {w.embed_snippet}
            </code>
            <CopyButton text={w.embed_snippet || ""} className="text-[#93C5FD] hover:text-white shrink-0" label="" />
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          <button
            onClick={onTogglePublish}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold ${
              published ? "bg-amber-50 text-amber-700 hover:bg-amber-100" : "bg-green-50 text-green-700 hover:bg-green-100"
            }`}
          >
            {published ? <EyeOff size={14} /> : <Eye size={14} />}
            {published ? "Unpublish" : "Publish"}
          </button>
          <div className="flex items-center gap-1.5">
            <IconBtn title="Analytics" onClick={onAnalytics}>
              <BarChart3 size={15} />
            </IconBtn>
            <IconBtn title="Edit" onClick={onEdit}>
              <Code2 size={15} />
            </IconBtn>
            <IconBtn title="Regenerate key" onClick={onRegenerate}>
              <RefreshCw size={15} />
            </IconBtn>
            <IconBtn title="Delete" danger onClick={onRemove}>
              <Trash2 size={15} />
            </IconBtn>
          </div>
        </div>
      </div>
    </div>
  );
}

function IconBtn({ children, onClick, title, danger }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`h-9 w-9 rounded-lg flex items-center justify-center border transition-colors ${
        danger
          ? "border-[#FEE2E2] text-[#DC2626] hover:bg-[#FEF2F2]"
          : "border-[#E2E8F0] text-[#475569] hover:bg-[#F8FAFC]"
      }`}
    >
      {children}
    </button>
  );
}

function Field({ label, children, hint }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-[#334155]">{label}</span>
      {hint && <span className="text-[11px] text-[#94A3B8] ml-2">{hint}</span>}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

const inputCls =
  "w-full px-3 py-2.5 rounded-xl border border-[#E2E8F0] text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/20";

function WidgetPreview({ form }) {
  const color = form.primary_color || "#2563EB";
  const onLeft = form.position === "bottom-left";
  const suggestions = (form.suggested || "")
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 3);
  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[#94A3B8]">
        <Eye size={14} /> Live preview
      </div>
      <div className="relative flex-1 overflow-hidden rounded-2xl border border-[#E2E8F0] bg-[linear-gradient(135deg,#F8FAFC,#EEF2F7)] p-4">
        {/* Mock chat window */}
        <div
          className={`absolute bottom-16 ${onLeft ? "left-4" : "right-4"} w-[260px] overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-black/5`}
        >
          <div className="px-4 py-3 text-white" style={{ background: color }}>
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-white/20">
                <Bot size={15} />
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{form.agent_name || "Ora AI"}</p>
                {form.company_name ? (
                  <p className="truncate text-[11px] opacity-80">{form.company_name}</p>
                ) : (
                  <p className="text-[11px] opacity-80">Online</p>
                )}
              </div>
            </div>
          </div>
          <div className="space-y-2 p-3">
            <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-[#F1F5F9] px-3 py-2 text-[12px] text-[#0F172A]">
              {form.welcome_message || "Hi! 👋 How can I help you today?"}
            </div>
            {suggestions.map((s, i) => (
              <div
                key={i}
                className="w-fit rounded-full border px-2.5 py-1 text-[11px]"
                style={{ borderColor: `${color}55`, color }}
              >
                {s}
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2 border-t border-[#EEF2F7] px-3 py-2">
            <div className="flex-1 rounded-full bg-[#F1F5F9] px-3 py-1.5 text-[11px] text-[#94A3B8]">
              Type your message…
            </div>
            <span className="grid h-6 w-6 place-items-center rounded-full text-white" style={{ background: color }}>
              <ArrowUpRight size={12} />
            </span>
          </div>
          {form.show_branding && (
            <div className="border-t border-[#EEF2F7] py-1.5 text-center text-[10px] text-[#94A3B8]">
              Powered by OraOne
            </div>
          )}
        </div>
        {/* Launcher bubble */}
        <div
          className={`absolute bottom-4 ${onLeft ? "left-4" : "right-4"} grid h-12 w-12 place-items-center rounded-full text-white shadow-lg`}
          style={{ background: color }}
        >
          <MessageSquare size={20} />
        </div>
      </div>
      <p className="mt-2 text-center text-[11px] text-[#94A3B8]">
        Preview updates as you edit · {TYPES.find((t) => t.value === form.widget_type)?.label}
      </p>
    </div>
  );
}

function WidgetModal({ widget, agents, kbs, onClose, onSaved }) {
  const isEdit = !!widget;
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(() => ({
    name: widget?.name || "",
    agent_id: widget?.agent_id || "",
    knowledge_base_id: widget?.knowledge_base_id || "",
    widget_type: widget?.widget_type || "bubble",
    position: widget?.position || "bottom-right",
    primary_color: widget?.theme?.primary_color || "#2563EB",
    agent_name: widget?.settings?.agent_name || "Ora AI",
    company_name: widget?.settings?.company_name || "",
    welcome_message: widget?.settings?.welcome_message || "Hi! 👋 How can I help you today?",
    suggested: (widget?.settings?.suggested_questions || []).join("\n"),
    domains: (widget?.domains || []).join("\n"),
    show_branding: widget?.settings?.show_branding ?? true,
    collect_leads: widget?.settings?.collect_leads ?? true,
    enable_escalation: widget?.settings?.enable_escalation ?? true,
  }));

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("Give your widget a name");
      return;
    }
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      agent_id: form.agent_id || null,
      knowledge_base_id: form.knowledge_base_id || null,
      widget_type: form.widget_type,
      position: form.position,
      theme: { ...(widget?.theme || {}), primary_color: form.primary_color, bubble_color: form.primary_color },
      settings: {
        ...(widget?.settings || {}),
        agent_name: form.agent_name,
        company_name: form.company_name || null,
        welcome_message: form.welcome_message,
        suggested_questions: form.suggested.split("\n").map((s) => s.trim()).filter(Boolean),
        show_branding: form.show_branding,
        collect_leads: form.collect_leads,
        enable_escalation: form.enable_escalation,
      },
      domains: form.domains.split("\n").map((s) => s.trim()).filter(Boolean),
    };
    try {
      if (isEdit) {
        await api.put(`/widgets/${widget.id}`, payload);
        toast.success("Widget updated");
      } else {
        await api.post("/widgets", payload);
        toast.success("Widget created");
      }
      onSaved();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.96, y: 12 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.96, y: 12 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl w-full max-w-4xl max-h-[88vh] overflow-y-auto shadow-2xl"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#EEF2F7] sticky top-0 bg-white z-10">
          <h3 className="text-lg font-bold text-[#0F172A]">{isEdit ? "Edit widget" : "New widget"}</h3>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-[#0F172A]">
            <X size={20} />
          </button>
        </div>

        <div className="grid md:grid-cols-[1fr_320px]">
        <div className="p-6 space-y-5">
          <Field label="Name">
            <input className={inputCls} value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Support assistant" />
          </Field>

          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Agent" hint="answers visitors">
              <select className={inputCls} value={form.agent_id} onChange={(e) => set("agent_id", e.target.value)}>
                <option value="">Auto (first active agent)</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Knowledge base" hint="grounds answers">
              <select
                className={inputCls}
                value={form.knowledge_base_id}
                onChange={(e) => set("knowledge_base_id", e.target.value)}
              >
                <option value="">All organization knowledge</option>
                {kbs.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.name}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Type">
              <select className={inputCls} value={form.widget_type} onChange={(e) => set("widget_type", e.target.value)}>
                {TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Position">
              <select className={inputCls} value={form.position} onChange={(e) => set("position", e.target.value)}>
                {POSITIONS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field label="Brand color">
            <div className="flex items-center gap-2 flex-wrap">
              {PRESET_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => set("primary_color", c)}
                  className={`h-8 w-8 rounded-lg border-2 ${form.primary_color === c ? "border-[#0F172A]" : "border-transparent"}`}
                  style={{ background: c }}
                />
              ))}
              <input
                type="color"
                value={form.primary_color}
                onChange={(e) => set("primary_color", e.target.value)}
                className="h-8 w-10 rounded-lg border border-[#E2E8F0] bg-white p-0.5"
              />
            </div>
          </Field>

          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Assistant name">
              <input className={inputCls} value={form.agent_name} onChange={(e) => set("agent_name", e.target.value)} />
            </Field>
            <Field label="Company name" hint="optional">
              <input className={inputCls} value={form.company_name} onChange={(e) => set("company_name", e.target.value)} />
            </Field>
          </div>

          <Field label="Welcome message">
            <textarea
              rows={2}
              className={inputCls}
              value={form.welcome_message}
              onChange={(e) => set("welcome_message", e.target.value)}
            />
          </Field>

          <Field label="Suggested questions" hint="one per line">
            <textarea
              rows={3}
              className={inputCls}
              value={form.suggested}
              onChange={(e) => set("suggested", e.target.value)}
              placeholder={"How do I get started?\nWhat are your pricing plans?"}
            />
          </Field>

          <Field label="Allowed domains" hint="one per line, empty = any domain">
            <textarea
              rows={2}
              className={inputCls}
              value={form.domains}
              onChange={(e) => set("domains", e.target.value)}
              placeholder={"example.com\napp.example.com"}
            />
          </Field>

          <div className="flex flex-wrap gap-4">
            <Toggle label="Collect leads" checked={form.collect_leads} onChange={(v) => set("collect_leads", v)} />
            <Toggle label="Allow escalation" checked={form.enable_escalation} onChange={(v) => set("enable_escalation", v)} />
            <Toggle label="Show branding" checked={form.show_branding} onChange={(v) => set("show_branding", v)} />
          </div>
        </div>
        <div className="hidden md:block border-l border-[#EEF2F7] bg-[#FBFCFE] p-4">
          <div className="sticky top-20">
            <WidgetPreview form={form} />
          </div>
        </div>
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#EEF2F7] sticky bottom-0 bg-white">
          <button onClick={onClose} className="px-4 py-2.5 rounded-xl text-sm font-semibold text-[#475569] hover:bg-[#F1F5F9]">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-50 text-white text-sm font-semibold"
          >
            {saving && <Loader2 size={15} className="animate-spin" />}
            {isEdit ? "Save changes" : "Create widget"}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

function Toggle({ label, checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="inline-flex items-center gap-2 text-sm text-[#334155]"
    >
      <span
        className={`relative inline-flex h-5 w-9 rounded-full transition-colors ${checked ? "bg-[#2563EB]" : "bg-[#CBD5E1]"}`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${checked ? "translate-x-4" : "translate-x-0.5"}`}
        />
      </span>
      {label}
    </button>
  );
}

function AnalyticsDrawer({ widget, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const { data } = await api.get(`/widgets/${widget.id}/analytics`);
        if (active) setData(data);
      } catch (err) {
        toast.error(formatApiError(err.response?.data?.detail));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [widget.id]);

  const stats = data
    ? [
        { label: "Sessions", value: data.sessions, icon: MessageSquare, color: "#2563EB" },
        { label: "Conversations", value: data.conversations, icon: Bot, color: "#7C3AED" },
        { label: "Messages", value: data.messages, icon: ArrowUpRight, color: "#0EA5E9" },
        { label: "Opens", value: data.opens, icon: Eye, color: "#059669" },
        { label: "Leads", value: data.leads, icon: Users, color: "#DB2777" },
        { label: "Escalations", value: data.escalations, icon: AlertTriangle, color: "#EA580C" },
      ]
    : [];

  return (
    <motion.div
      className="fixed inset-0 z-50 flex justify-end bg-black/40"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        initial={{ x: 40 }}
        animate={{ x: 0 }}
        exit={{ x: 40 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white w-full max-w-md h-full overflow-y-auto shadow-2xl"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#EEF2F7] sticky top-0 bg-white">
          <div>
            <h3 className="text-lg font-bold text-[#0F172A]">Analytics</h3>
            <p className="text-xs text-[#64748B]">{widget.name}</p>
          </div>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-[#0F172A]">
            <X size={20} />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20 text-[#94A3B8]">
            <Loader2 className="animate-spin" />
          </div>
        ) : (
          <div className="p-6 space-y-6">
            <div className="grid grid-cols-2 gap-3">
              {stats.map((s) => (
                <div key={s.label} className="border border-[#E2E8F0] rounded-xl p-4">
                  <div className="h-9 w-9 rounded-lg flex items-center justify-center mb-2" style={{ background: `${s.color}14`, color: s.color }}>
                    <s.icon size={16} />
                  </div>
                  <div className="text-2xl font-bold text-[#0F172A]">{s.value ?? 0}</div>
                  <div className="text-xs text-[#64748B]">{s.label}</div>
                </div>
              ))}
            </div>

            {data?.avg_csat != null && (
              <div className="border border-[#E2E8F0] rounded-xl p-4">
                <div className="text-xs text-[#64748B]">Average satisfaction</div>
                <div className="text-2xl font-bold text-[#0F172A] mt-1">{data.avg_csat.toFixed(1)} / 5</div>
              </div>
            )}

            {data?.top_questions?.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-[#0F172A] mb-2">Top questions</h4>
                <div className="space-y-2">
                  {data.top_questions.slice(0, 8).map((q, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-[#334155]">
                      <span className="text-[#94A3B8]">{i + 1}.</span>
                      <span className="flex-1">{q.question || q.text}</span>
                      {q.count != null && <span className="text-xs text-[#94A3B8]">{q.count}×</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
