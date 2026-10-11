import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Users,
  UserPlus,
  UserCheck,
  TrendingUp,
  Calendar,
  Filter as FilterIcon,
  Plus,
  Eye,
  Pencil,
  Trash2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  LayoutGrid,
  Table as TableIcon,
  Search,
  X,
  Mail,
  Phone,
  Building2,
  MessageSquare,
  Tag,
  Clock,
  Save,
  Loader2,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { EmptyState } from "@/components/ui/EmptyState";
import { EmptyStateLoader } from "@/components/ui/OraOneLoader";
import { PageHeader, GhostButton } from "@/components/dashboard/kit";

/* ---------- constants ---------- */

// Pipeline stages, in flow order. Values match the API's title-case labels.
const PIPELINE = ["New", "Contacted", "Qualified", "Won", "Lost"];
const STATUS_TO_API = { New: "new", Contacted: "contacted", Qualified: "qualified", Won: "won", Lost: "lost" };
const TEMPERATURES = ["hot", "warm", "cold"];
const TEMP_CLS = {
  hot: "bg-red-50 text-red-700 border-red-200",
  warm: "bg-amber-50 text-amber-700 border-amber-200",
  cold: "bg-sky-50 text-sky-700 border-sky-200",
};

const STATUS_CLS = {
  New:       "bg-blue-50 text-blue-700 border-blue-200",
  Contacted: "bg-orange-50 text-orange-700 border-orange-200",
  Qualified: "bg-green-50 text-green-700 border-green-200",
  Won:       "bg-cyan-50 text-cyan-700 border-cyan-200",
  Lost:      "bg-red-50 text-red-700 border-red-200",
};

const AVATAR_PALETTE = [
  "#2563EB", // blue
  "#0EA5E9", // sky
  "#16A34A", // green
  "#F59E0B", // amber
  "#06B6D4", // cyan
  "#EC4899", // pink
];

const KPI_CARDS = [
  { key: "total",      label: "Total Leads",         icon: Users,      tone: "#2563EB" },
  { key: "new",        label: "New Leads",           icon: UserPlus,   tone: "#22C55E" },
  { key: "qualified",  label: "Qualified Leads",     icon: UserCheck,  tone: "#0891B2" },
  { key: "conversion", label: "Conversion Rate",     icon: TrendingUp, tone: "#F59E0B" },
  { key: "booked",     label: "Appointments Booked", icon: Calendar,   tone: "#EC4899" },
];

const EMPTY_STATS = {
  total: 0, new: 0, qualified: 0, conversion_rate: 0, appointments: 0,
};

const kpiValue = (key, stats) => {
  switch (key) {
    case "total":      return stats.total ?? 0;
    case "new":        return stats.new ?? 0;
    case "qualified":  return stats.qualified ?? 0;
    case "conversion": return `${stats.conversion_rate ?? 0}%`;
    case "booked":     return stats.appointments ?? 0;
    default:           return 0;
  }
};

const initials = (name = "") =>
  name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

const colorFor = (key = "") => {
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return AVATAR_PALETTE[h % AVATAR_PALETTE.length];
};

// A chatting visitor may share no contact details — still show them clearly.
const displayName = (l) => l?.name || l?.email || l?.phone || "Anonymous visitor";

function toCSV(rows) {
  if (!rows.length) return "";
  const headers = ["Name", "Email", "Phone", "Source", "Intent", "Status", "Score", "Date"];
  const body = rows.map((r) =>
    [r.name, r.email, r.phone, r.source, r.intent, r.status, r.score, r.date]
      .map((v) => `"${(v ?? "").toString().replace(/"/g, '""')}"`)
      .join(",")
  );
  return [headers.join(","), ...body].join("\n");
}

/* ---------- page ---------- */

export default function Leads() {
  const nav = useNavigate();
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(EMPTY_STATS);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // View + filtering.
  const [view, setView] = useState("table"); // table | pipeline
  const [showFilter, setShowFilter] = useState(false);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState(""); // "" = all
  const [tempFilter, setTempFilter] = useState("");
  const [contactFilter, setContactFilter] = useState("all"); // all | contactable | anonymous
  const [selected, setSelected] = useState(null); // lead in detail drawer

  const formatRow = (l) => ({
    ...l,
    intent: l.intent || "—",
    tags: Array.isArray(l.tags) ? l.tags : [],
    date: l.created_at ? new Date(l.created_at).toLocaleDateString() : new Date().toLocaleDateString(),
  });

  const loadStats = useCallback(async () => {
    try {
      const { data } = await api.get("/leads/stats");
      if (data) setStats({ ...EMPTY_STATS, ...data });
    } catch {
      /* stats are best-effort */
    }
  }, []);

  const loadLeads = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { limit: 500 };
      if (q.trim()) params.q = q.trim();
      if (statusFilter) params.status = STATUS_TO_API[statusFilter] || statusFilter.toLowerCase();
      if (tempFilter) params.temperature = tempFilter;
      const { data } = await api.get("/leads", { params });
      setLeads(Array.isArray(data) ? data.map(formatRow) : []);
      setPage(1);
    } catch (err) {
      setError(formatApiError(err));
      setLeads([]);
    } finally {
      setLoading(false);
    }
  }, [q, statusFilter, tempFilter]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // Debounce list reloads so typing in search doesn't hammer the API.
  useEffect(() => {
    const t = setTimeout(loadLeads, 300);
    return () => clearTimeout(t);
  }, [loadLeads]);

  const activeFilters = (statusFilter ? 1 : 0) + (tempFilter ? 1 : 0) + (q.trim() ? 1 : 0);

  // Optimistic status move (used by both the drawer and the pipeline board).
  const changeStatus = useCallback(async (lead, nextLabel) => {
    if (!lead?.id || lead.status === nextLabel) return;
    const prev = leads;
    setLeads((rows) => rows.map((r) => (r.id === lead.id ? { ...r, status: nextLabel } : r)));
    setSelected((s) => (s && s.id === lead.id ? { ...s, status: nextLabel } : s));
    try {
      await api.patch(`/leads/${lead.id}`, { status: STATUS_TO_API[nextLabel] });
      loadStats();
      toast.success(`Moved to ${nextLabel}`);
    } catch (err) {
      setLeads(prev);
      toast.error(formatApiError(err));
    }
  }, [leads, loadStats]);

  const applyLeadUpdate = useCallback((updated) => {
    const row = formatRow(updated);
    setLeads((rows) => rows.map((r) => (r.id === row.id ? row : r)));
    setSelected((s) => (s && s.id === row.id ? row : s));
    loadStats();
  }, [loadStats]);

  // Capture-everything fills the list with anonymous browsers — let the user
  // focus on the ones they can actually reach without losing the rest.
  const isContactable = (l) => !!(l.email || l.phone);
  const visibleLeads = useMemo(() => {
    if (contactFilter === "contactable") return leads.filter(isContactable);
    if (contactFilter === "anonymous") return leads.filter((l) => !isContactable(l));
    return leads;
  }, [leads, contactFilter]);
  const contactCounts = useMemo(
    () => ({
      all: leads.length,
      contactable: leads.reduce((n, l) => n + (isContactable(l) ? 1 : 0), 0),
      anonymous: leads.reduce((n, l) => n + (isContactable(l) ? 0 : 1), 0),
    }),
    [leads]
  );

  const totalPages = Math.max(1, Math.ceil(visibleLeads.length / perPage));
  const slice = useMemo(
    () => visibleLeads.slice((page - 1) * perPage, page * perPage),
    [visibleLeads, page, perPage]
  );

  const handleImport = () => {
    const csv = toCSV(leads);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "oraone-leads.csv";
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Leads exported as CSV");
  };

  const handleDelete = async (lead) => {
    if (!lead?.id) return;
    if (!window.confirm(`Delete lead “${lead.name}”? This cannot be undone.`)) return;
    const prev = leads;
    setLeads((rows) => rows.filter((r) => r.id !== lead.id));
    setSelected((s) => (s && s.id === lead.id ? null : s));
    try {
      await api.delete(`/leads/${lead.id}`);
      setStats((s) => ({ ...s, total: Math.max(0, (s.total || 0) - 1) }));
      toast.success("Lead deleted");
    } catch (err) {
      setLeads(prev);
      toast.error(err?.response?.data?.detail || "Failed to delete lead");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        eyebrow="CRM"
        icon={Users}
        title="Leads"
        subtitle="Manage and track all your leads in one place."
        actions={
          <>
            <div className="inline-flex rounded-xl border border-[#E2E8F0] bg-white p-0.5" data-testid="leads-view-toggle">
              <button
                onClick={() => setView("table")}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[10px] text-[12.5px] font-semibold transition-colors ${
                  view === "table" ? "bg-[#EFF6FF] text-[#2563EB]" : "text-[#64748B] hover:text-[#0F172A]"
                }`}
                data-testid="leads-view-table"
              >
                <TableIcon size={14} /> Table
              </button>
              <button
                onClick={() => setView("pipeline")}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[10px] text-[12.5px] font-semibold transition-colors ${
                  view === "pipeline" ? "bg-[#EFF6FF] text-[#2563EB]" : "text-[#64748B] hover:text-[#0F172A]"
                }`}
                data-testid="leads-view-pipeline"
              >
                <LayoutGrid size={14} /> Pipeline
              </button>
            </div>
            <GhostButton
              data-testid="leads-filter"
              onClick={() => setShowFilter((v) => !v)}
              className={showFilter || activeFilters ? "ring-2 ring-[#2563EB]/20 text-[#2563EB]" : undefined}
            >
              <FilterIcon size={14} /> Filter
              {activeFilters > 0 && (
                <span className="ml-1 inline-grid place-items-center size-4 rounded-full bg-[#2563EB] text-white text-[10px] font-bold">
                  {activeFilters}
                </span>
              )}
            </GhostButton>
            <button
              onClick={handleImport}
              data-testid="leads-import"
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#2563EB] text-white text-[12.5px] font-semibold shadow-sm transition-colors hover:bg-[#1D4ED8]"
            >
              <Plus size={14} /> Export
            </button>
          </>
        }
      />

      {/* Filter bar */}
      {showFilter && (
        <div className="rounded-2xl bg-white border border-[#E7EAF1] p-4 flex flex-wrap items-center gap-3" data-testid="leads-filter-bar">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search name, email, company, phone…"
              aria-label="Search leads"
              data-testid="leads-search"
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-[#E2E8F0] text-[13px] outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15"
            />
          </div>
          <SelectFilter
            value={statusFilter}
            onChange={setStatusFilter}
            placeholder="All statuses"
            options={PIPELINE}
            testid="leads-filter-status"
          />
          <SelectFilter
            value={tempFilter}
            onChange={setTempFilter}
            placeholder="All temperatures"
            options={TEMPERATURES.map((t) => t[0].toUpperCase() + t.slice(1))}
            values={TEMPERATURES}
            testid="leads-filter-temperature"
          />
          {activeFilters > 0 && (
            <button
              onClick={() => { setQ(""); setStatusFilter(""); setTempFilter(""); }}
              className="inline-flex items-center gap-1 text-[12.5px] font-medium text-[#64748B] hover:text-[#0F172A]"
              data-testid="leads-filter-clear"
            >
              <X size={13} /> Clear
            </button>
          )}
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {KPI_CARDS.map((k) => (
          <div
            key={k.key}
            className="p-4 rounded-2xl bg-white border border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)] hover:shadow-premium hover:-translate-y-0.5 transition-all"
            data-testid={`leads-kpi-${k.key}`}
          >
            <div className="flex items-start gap-3">
              <div className="size-11 rounded-2xl grid place-items-center shrink-0" style={{ background: `${k.tone}1A` }}>
                <k.icon size={18} style={{ color: k.tone }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[12px] text-[#94A3B8] leading-tight">{k.label}</p>
                <p className="mt-1 text-[28px] font-bold tracking-tight text-[#0F172A] leading-none">
                  {(() => {
                    const v = kpiValue(k.key, stats);
                    return typeof v === "number" ? v.toLocaleString() : v;
                  })()}
                </p>
              </div>
            </div>
            <div className="mt-2.5 flex items-center gap-1.5">
              <span className="size-1.5 rounded-full bg-[#22C55E]" />
              <span className="text-[11px] text-[#94A3B8]">Live · across this project</span>
            </div>
          </div>
        ))}
      </div>

      {/* Focus filter — capture-everything fills the list with anonymous
          browsers; let the user zero in on contactable leads. */}
      {!loading && leads.length > 0 && (
        <div className="inline-flex items-center gap-1 rounded-xl border border-[#E7EAF1] bg-white p-1" data-testid="leads-contact-filter">
          {[["all", "All"], ["contactable", "Contactable"], ["anonymous", "Anonymous"]].map(([key, label]) => (
            <button
              key={key}
              onClick={() => { setContactFilter(key); setPage(1); }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12.5px] font-semibold transition-colors ${
                contactFilter === key ? "bg-[#EFF6FF] text-[#2563EB]" : "text-[#64748B] hover:text-[#0F172A]"
              }`}
              data-testid={`leads-contact-${key}`}
            >
              {label}
              <span className={`text-[10.5px] leading-none px-1.5 py-0.5 rounded-full ${
                contactFilter === key ? "bg-[#2563EB] text-white" : "bg-[#F1F5F9] text-[#94A3B8]"
              }`}>
                {contactCounts[key]}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Table / Pipeline / empty state */}
      {loading ? (
        <EmptyStateLoader label="Loading leads…" sub="Fetching your captured leads…" />
      ) : visibleLeads.length === 0 ? (
        (activeFilters || contactFilter !== "all") ? (
          <EmptyState
            testId="leads-no-match"
            size="lg"
            showOrb={false}
            title="No matching leads"
            description="No leads match your current filters. Try clearing or adjusting them."
            actionLabel="Clear filters"
            onAction={() => { setQ(""); setStatusFilter(""); setTempFilter(""); setContactFilter("all"); }}
          />
        ) : (
          <EmptyState
            testId="leads-empty-state"
            size="md"
            showOrb={false}
            title="No leads yet"
            description="Once your AI agents start capturing conversations, qualified leads will appear here automatically."
            actionLabel="Import Leads"
            onAction={handleImport}
          />
        )
      ) : view === "pipeline" ? (
        <PipelineBoard
          leads={visibleLeads}
          onMove={changeStatus}
          onOpen={setSelected}
        />
      ) : (
      <div className="rounded-2xl bg-white border border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px]">
            <thead className="bg-white">
              <tr className="text-[10.5px] uppercase tracking-[0.12em] text-[#94A3B8]">
                <th className="px-6 py-4 font-semibold">Name</th>
                <th className="px-6 py-4 font-semibold">Contact</th>
                <th className="px-6 py-4 font-semibold">Source</th>
                <th className="px-6 py-4 font-semibold">Interest</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold">Score</th>
                <th className="px-6 py-4 font-semibold">Date Added</th>
                <th className="px-6 py-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {slice.map((l) => {
                const c = colorFor(l.id || l.name);
                return (
                  <tr
                    key={l.id || l.name}
                    onClick={() => setSelected(l)}
                    className="border-t border-[#F1F5F9] hover:bg-[#F8FAFC]/60 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="size-9 rounded-full grid place-items-center text-white text-[11.5px] font-semibold shrink-0" style={{ background: c }}>
                          {initials(displayName(l)) || "?"}
                        </div>
                        <span className="font-semibold text-[#0F172A]">{displayName(l)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-[#0F172A]">{l.phone}</p>
                      <p className="text-[12px] text-[#94A3B8] mt-0.5">{l.email}</p>
                    </td>
                    <td className="px-6 py-4 text-[#475569]">{l.source}</td>
                    <td className="px-6 py-4 text-[#475569]">{l.intent}</td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-block text-[11px] px-2.5 py-1 rounded-full border font-medium ${
                          STATUS_CLS[l.status] || "bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]"
                        }`}
                      >
                        {l.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <ScorePill score={l.score} />
                    </td>
                    <td className="px-6 py-4 text-[#475569] whitespace-nowrap">{l.date}</td>
                    <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1">
                        <IconBtn ariaLabel="View" testId={`lead-view-${l.id || l.name}`} onClick={() => setSelected(l)}>
                          <Eye size={14} className="text-[#64748B]" />
                        </IconBtn>
                        <IconBtn ariaLabel="Edit" testId={`lead-edit-${l.id || l.name}`} onClick={() => setSelected(l)}>
                          <Pencil size={14} className="text-[#64748B]" />
                        </IconBtn>
                        <IconBtn ariaLabel="Delete" testId={`lead-delete-${l.id || l.name}`} danger onClick={() => handleDelete(l)}>
                          <Trash2 size={14} className="text-[#EF4444]" />
                        </IconBtn>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#F1F5F9] flex items-center justify-between flex-wrap gap-3">
          <p className="text-[12px] text-[#64748B]">
            Showing <span className="font-semibold text-[#0F172A]">{(page - 1) * perPage + 1}</span> to{" "}
            <span className="font-semibold text-[#0F172A]">{Math.min(page * perPage, visibleLeads.length)}</span> of{" "}
            <span className="font-semibold text-[#0F172A]">{visibleLeads.length.toLocaleString()}</span> entries
          </p>
          <div className="flex items-center gap-2">
            <div className="relative">
              <select
                value={perPage}
                onChange={(e) => {
                  setPerPage(Number(e.target.value));
                  setPage(1);
                }}
                className="appearance-none pl-3 pr-8 py-2 rounded-xl border border-[#E2E8F0] bg-white text-[12px] font-medium text-[#475569] hover:bg-[#F8FAFC] cursor-pointer focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10"
                data-testid="leads-per-page"
              >
                {[10, 25, 50, 100].map((n) => (
                  <option key={n} value={n}>
                    {n} per page
                  </option>
                ))}
              </select>
              <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 text-[#94A3B8] pointer-events-none" />
            </div>
            <Pager page={page} total={Math.max(totalPages, 5)} onChange={setPage} />
          </div>
        </div>
      </div>
      )}

      {/* Lead detail drawer */}
      <LeadDrawer
        lead={selected}
        onClose={() => setSelected(null)}
        onMove={changeStatus}
        onSaved={applyLeadUpdate}
        onDelete={(l) => { handleDelete(l); }}
        onOpenConversation={(cid) => nav(`/app/conversations?c=${cid}`)}
      />
    </div>
  );
}

/* ---------- helpers ---------- */

function SelectFilter({ value, onChange, placeholder, options, values, testid }) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        data-testid={testid}
        className="appearance-none pl-3 pr-8 py-2 rounded-xl border border-[#E2E8F0] bg-white text-[12.5px] font-medium text-[#475569] hover:bg-[#F8FAFC] cursor-pointer focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15"
      >
        <option value="">{placeholder}</option>
        {options.map((opt, i) => (
          <option key={opt} value={values ? values[i] : opt}>
            {opt}
          </option>
        ))}
      </select>
      <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 text-[#94A3B8] pointer-events-none" />
    </div>
  );
}

function PipelineBoard({ leads, onMove, onOpen }) {
  const [dragId, setDragId] = useState(null);
  const [overCol, setOverCol] = useState(null);

  const cols = useMemo(() => {
    const map = Object.fromEntries(PIPELINE.map((s) => [s, []]));
    for (const l of leads) (map[l.status] || (map[l.status] = [])).push(l);
    return map;
  }, [leads]);

  const drop = (stage) => {
    const lead = leads.find((l) => l.id === dragId);
    if (lead) onMove(lead, stage);
    setDragId(null);
    setOverCol(null);
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4" data-testid="leads-pipeline">
      {PIPELINE.map((stage) => (
        <div
          key={stage}
          onDragOver={(e) => { e.preventDefault(); setOverCol(stage); }}
          onDragLeave={() => setOverCol((c) => (c === stage ? null : c))}
          onDrop={() => drop(stage)}
          className={`rounded-2xl border p-3 min-h-[160px] transition-colors ${
            overCol === stage ? "border-[#2563EB] bg-[#EFF6FF]/60" : "border-[#E7EAF1] bg-[#F8FAFC]/50"
          }`}
          data-testid={`pipeline-col-${stage.toLowerCase()}`}
        >
          <div className="flex items-center justify-between mb-3 px-1">
            <span className={`inline-flex items-center gap-2 text-[12px] font-semibold ${
              STATUS_CLS[stage]?.includes("text-") ? "" : "text-[#0F172A]"
            }`}>
              <span className={`size-2 rounded-full ${STATUS_DOT[stage] || "bg-[#94A3B8]"}`} />
              {stage}
            </span>
            <span className="text-[11px] font-semibold text-[#94A3B8]">{cols[stage]?.length || 0}</span>
          </div>
          <div className="space-y-2">
            {(cols[stage] || []).map((l) => (
              <button
                key={l.id}
                draggable
                onDragStart={() => setDragId(l.id)}
                onDragEnd={() => { setDragId(null); setOverCol(null); }}
                onClick={() => onOpen(l)}
                className={`w-full text-left rounded-xl bg-white border border-[#E7EAF1] p-3 shadow-[0_1px_2px_rgba(16,24,40,0.04)] hover:shadow-premium hover:-translate-y-0.5 transition-all ${
                  dragId === l.id ? "opacity-50" : ""
                }`}
                data-testid={`pipeline-card-${l.id}`}
              >
                <div className="flex items-center gap-2">
                  <div className="size-7 rounded-full grid place-items-center text-white text-[10px] font-semibold shrink-0" style={{ background: colorFor(l.id || l.name) }}>
                    {initials(l.name)}
                  </div>
                  <span className="font-semibold text-[13px] text-[#0F172A] truncate">{l.name || "Unknown"}</span>
                </div>
                {l.intent && l.intent !== "—" && (
                  <p className="mt-2 text-[12px] text-[#64748B] line-clamp-2">{l.intent}</p>
                )}
                <div className="mt-2.5 flex items-center justify-between">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium capitalize ${TEMP_CLS[l.temperature] || "bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]"}`}>
                    {l.temperature}
                  </span>
                  <ScorePill score={l.score} />
                </div>
              </button>
            ))}
            {(cols[stage]?.length || 0) === 0 && (
              <p className="text-[11.5px] text-[#94A3B8] text-center py-4">Drop leads here</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

const STATUS_DOT = {
  New: "bg-blue-500",
  Contacted: "bg-orange-500",
  Qualified: "bg-green-500",
  Won: "bg-cyan-500",
  Lost: "bg-red-500",
};

function aiSummary(lead) {
  if (!lead) return "";
  const bits = [];
  const who = lead.name || "This contact";
  const via = lead.source && lead.source !== "manual" ? ` via ${lead.source}` : "";
  bits.push(`${who} came in${via} and is currently **${lead.status}**.`);
  if (lead.intent && lead.intent !== "—") bits.push(`They're interested in ${lead.intent.toLowerCase()}.`);
  if (lead.temperature) bits.push(`Engagement is rated **${lead.temperature}** with a lead score of ${lead.score}/100.`);
  if (lead.message) bits.push(`Last message: “${lead.message.slice(0, 160)}${lead.message.length > 160 ? "…" : ""}”`);
  return bits.join(" ");
}

function LeadDrawer({ lead, onClose, onMove, onSaved, onDelete, onOpenConversation }) {
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState("");
  const [score, setScore] = useState(0);
  const [temp, setTemp] = useState("warm");
  const [saving, setSaving] = useState(false);
  const baseline = useRef("");
  const [convo, setConvo] = useState(null);
  const [convoLoading, setConvoLoading] = useState(false);

  useEffect(() => {
    if (!lead) return;
    setNotes(lead.notes || "");
    setTags(Array.isArray(lead.tags) ? lead.tags : []);
    setScore(typeof lead.score === "number" ? lead.score : 0);
    setTemp(lead.temperature || "warm");
    baseline.current = JSON.stringify({ notes: lead.notes || "", tags: lead.tags || [], score: lead.score || 0, temp: lead.temperature || "warm" });
  }, [lead]);

  // Pull the full chat thread that produced this lead, shown inline below.
  useEffect(() => {
    if (!lead?.id) { setConvo(null); return; }
    let cancelled = false;
    setConvoLoading(true);
    api
      .get(`/leads/${lead.id}/conversation`)
      .then(({ data }) => { if (!cancelled) setConvo(data || { messages: [] }); })
      .catch(() => { if (!cancelled) setConvo({ messages: [] }); })
      .finally(() => { if (!cancelled) setConvoLoading(false); });
    return () => { cancelled = true; };
  }, [lead?.id]);

  // Lock body scroll + close on Escape while open.
  useEffect(() => {
    if (!lead) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [lead, onClose]);

  if (!lead) return null;

  const dirty = baseline.current !== JSON.stringify({ notes, tags, score, temp });

  const addTag = () => {
    const t = tagInput.trim().slice(0, 40);
    if (t && !tags.includes(t)) setTags([...tags, t]);
    setTagInput("");
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.patch(`/leads/${lead.id}`, {
        notes,
        tags,
        score: Number(score),
        temperature: temp,
      });
      onSaved(data);
      toast.success("Lead updated");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end" data-testid="lead-drawer">
      <div className="absolute inset-0 bg-[#0F172A]/40 backdrop-blur-[1px]" onClick={onClose} />
      <div className="relative w-full max-w-[440px] h-full bg-white shadow-2xl flex flex-col animate-slideIn">
        {/* Header */}
        <div className="px-6 py-5 border-b border-[#F1F5F9] flex items-start gap-3">
          <div className="size-11 rounded-full grid place-items-center text-white text-[14px] font-semibold shrink-0" style={{ background: colorFor(lead.id || lead.name) }}>
            {initials(displayName(lead)) || "?"}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-[16px] font-bold text-[#0F172A] truncate">{displayName(lead)}</h3>
            <p className="text-[12px] text-[#94A3B8] mt-0.5 capitalize">{lead.source} lead · {lead.date}</p>
          </div>
          <button onClick={onClose} className="size-8 rounded-lg grid place-items-center hover:bg-[#F1F5F9]" data-testid="lead-drawer-close">
            <X size={16} className="text-[#64748B]" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Pipeline stage */}
          <div>
            <p className="text-[11px] uppercase tracking-[0.1em] text-[#94A3B8] font-semibold mb-2">Pipeline stage</p>
            <div className="flex flex-wrap gap-1.5" data-testid="lead-drawer-stages">
              {PIPELINE.map((s) => (
                <button
                  key={s}
                  onClick={() => onMove(lead, s)}
                  className={`text-[11.5px] px-2.5 py-1 rounded-full border font-medium transition-all ${
                    lead.status === s
                      ? STATUS_CLS[s] + " ring-2 ring-offset-1 ring-current/20"
                      : "bg-white text-[#64748B] border-[#E2E8F0] hover:bg-[#F8FAFC]"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Contact */}
          <div className="space-y-2">
            <p className="text-[11px] uppercase tracking-[0.1em] text-[#94A3B8] font-semibold">Contact</p>
            <ContactRow icon={Mail} value={lead.email} href={lead.email ? `mailto:${lead.email}` : null} />
            <ContactRow icon={Phone} value={lead.phone} href={lead.phone ? `tel:${lead.phone}` : null} />
            <ContactRow icon={Building2} value={lead.company} />
            <ContactRow icon={MessageSquare} value={lead.intent !== "—" ? lead.intent : null} />
          </div>

          {/* AI summary */}
          <div className="rounded-xl border border-[#DBEAFE] bg-gradient-to-br from-[#EFF6FF] to-[#ECFEFF] p-4">
            <p className="flex items-center gap-1.5 text-[12px] font-semibold text-[#2563EB] mb-1.5">
              <Sparkles size={13} /> AI summary
            </p>
            <p className="text-[12.5px] text-[#475569] leading-relaxed" data-testid="lead-ai-summary"
               dangerouslySetInnerHTML={{ __html: aiSummary(lead).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>") }} />
          </div>

          {/* Conversation transcript — the whole thread, even for anon visitors */}
          <div>
            <p className="flex items-center gap-1.5 text-[11px] uppercase tracking-[0.1em] text-[#94A3B8] font-semibold mb-2">
              <MessageSquare size={12} /> Conversation
            </p>
            {convoLoading ? (
              <div className="flex items-center gap-2 text-[12.5px] text-[#94A3B8] py-3">
                <Loader2 size={14} className="animate-spin" /> Loading conversation…
              </div>
            ) : convo && Array.isArray(convo.messages) && convo.messages.length > 0 ? (
              <div
                className="rounded-xl border border-[#E7EAF1] bg-[#F8FAFC] p-3 space-y-2 max-h-[320px] overflow-y-auto"
                data-testid="lead-conversation"
              >
                {convo.messages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[82%] rounded-2xl px-3 py-2 text-[12.5px] leading-relaxed whitespace-pre-wrap break-words ${
                        m.role === "user"
                          ? "bg-[#2563EB] text-white rounded-br-sm"
                          : "bg-white text-[#0F172A] border border-[#E7EAF1] rounded-bl-sm"
                      }`}
                    >
                      {m.content}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[12.5px] text-[#94A3B8] py-2">
                No conversation captured for this lead yet.
              </p>
            )}
          </div>

          {/* Score + temperature */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-[11px] uppercase tracking-[0.1em] text-[#94A3B8] font-semibold">Score: {score}</label>
              <input
                type="range" min={0} max={100} value={score}
                onChange={(e) => setScore(Number(e.target.value))}
                className="w-full mt-2 accent-[#2563EB]"
                data-testid="lead-drawer-score"
              />
            </div>
            <div>
              <label className="text-[11px] uppercase tracking-[0.1em] text-[#94A3B8] font-semibold">Temperature</label>
              <div className="flex gap-1.5 mt-2">
                {TEMPERATURES.map((t) => (
                  <button
                    key={t}
                    onClick={() => setTemp(t)}
                    className={`flex-1 text-[11.5px] py-1.5 rounded-lg border font-medium capitalize transition-colors ${
                      temp === t ? TEMP_CLS[t] : "bg-white text-[#64748B] border-[#E2E8F0] hover:bg-[#F8FAFC]"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Tags */}
          <div>
            <p className="flex items-center gap-1.5 text-[11px] uppercase tracking-[0.1em] text-[#94A3B8] font-semibold mb-2">
              <Tag size={12} /> Tags
            </p>
            <div className="flex flex-wrap gap-1.5 mb-2" data-testid="lead-tags">
              {tags.map((t) => (
                <span key={t} className="inline-flex items-center gap-1 text-[11.5px] px-2 py-1 rounded-full bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE] font-medium">
                  {t}
                  <button onClick={() => setTags(tags.filter((x) => x !== t))} className="hover:text-[#1E40AF]">
                    <X size={11} />
                  </button>
                </span>
              ))}
              {tags.length === 0 && <span className="text-[12px] text-[#94A3B8]">No tags yet</span>}
            </div>
            <input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
              placeholder="Add a tag and press Enter"
              data-testid="lead-tag-input"
              className="w-full px-3 py-2 rounded-xl border border-[#E2E8F0] text-[12.5px] outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15"
            />
          </div>

          {/* Notes */}
          <div>
            <p className="text-[11px] uppercase tracking-[0.1em] text-[#94A3B8] font-semibold mb-2">Notes</p>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={4}
              placeholder="Add internal notes about this lead…"
              data-testid="lead-notes"
              className="w-full px-3 py-2 rounded-xl border border-[#E2E8F0] text-[12.5px] outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15 resize-none"
            />
          </div>

          {/* Timeline */}
          <div>
            <p className="flex items-center gap-1.5 text-[11px] uppercase tracking-[0.1em] text-[#94A3B8] font-semibold mb-3">
              <Clock size={12} /> Timeline
            </p>
            <ol className="relative border-l border-[#E2E8F0] ml-1 space-y-4" data-testid="lead-timeline">
              <TimelineItem label="Lead created" at={lead.created_at} tone="#2563EB" />
              <TimelineItem label="Last updated" at={lead.updated_at} tone="#16A34A" />
              {lead.conversation_id && (
                <li className="ml-4">
                  <span className="absolute -left-[5px] size-2.5 rounded-full bg-[#4F46E5] border-2 border-white" />
                  <button
                    onClick={() => onOpenConversation(lead.conversation_id)}
                    className="inline-flex items-center gap-1 text-[12.5px] font-medium text-[#2563EB] hover:underline"
                    data-testid="lead-open-conversation"
                  >
                    View source conversation <ExternalLink size={12} />
                  </button>
                </li>
              )}
            </ol>
          </div>
        </div>

        {/* Footer actions */}
        <div className="px-6 py-4 border-t border-[#F1F5F9] flex items-center gap-2">
          <button
            onClick={() => onDelete(lead)}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[#FECACA] text-[#EF4444] text-[12.5px] font-semibold hover:bg-red-50 transition-colors"
            data-testid="lead-drawer-delete"
          >
            <Trash2 size={14} /> Delete
          </button>
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-[#E2E8F0] text-[#475569] text-[12.5px] font-semibold hover:bg-[#F8FAFC]"
          >
            Close
          </button>
          <button
            onClick={save}
            disabled={!dirty || saving}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#2563EB] text-white text-[12.5px] font-semibold shadow-sm transition-colors hover:bg-[#1D4ED8] disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="lead-drawer-save"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save
          </button>
        </div>
      </div>
    </div>
  );
}

function ContactRow({ icon: Icon, value, href }) {
  if (!value) return null;
  const content = (
    <span className="flex items-center gap-2.5 text-[13px] text-[#475569]">
      <Icon size={14} className="text-[#94A3B8] shrink-0" /> {value}
    </span>
  );
  return href ? <a href={href} className="block hover:text-[#2563EB]">{content}</a> : content;
}

function TimelineItem({ label, at, tone }) {
  return (
    <li className="ml-4">
      <span className="absolute -left-[5px] size-2.5 rounded-full border-2 border-white" style={{ background: tone }} />
      <p className="text-[12.5px] font-medium text-[#0F172A]">{label}</p>
      <p className="text-[11.5px] text-[#94A3B8]">{at ? new Date(at).toLocaleString() : "—"}</p>
    </li>
  );
}

function IconBtn({ children, ariaLabel, testId, danger, onClick }) {
  return (
    <button
      aria-label={ariaLabel}
      data-testid={testId}
      onClick={onClick}
      className={`size-8 rounded-lg grid place-items-center hover:bg-[#F1F5F9] transition-colors ${
        danger ? "hover:bg-red-50" : ""
      }`}
    >
      {children}
    </button>
  );
}

function ScorePill({ score = 0 }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className="flex items-center gap-3">
      <div className="w-16 h-1.5 rounded-full bg-[#F1F5F9] overflow-hidden">
        <div className="h-full rounded-full bg-[#2563EB]" style={{ width: `${pct}%` }} />
      </div>
      <span className="font-semibold text-[#0F172A] tabular-nums">{score}</span>
    </div>
  );
}

function Pager({ page, total, onChange }) {
  const pages = [1, 2, 3, 4, 5];
  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => page > 1 && onChange(page - 1)}
        className="size-8 rounded-lg grid place-items-center hover:bg-[#F1F5F9] text-[#64748B] disabled:opacity-40"
        disabled={page === 1}
        aria-label="Previous"
      >
        <ChevronLeft size={14} />
      </button>
      {pages.map((n) => (
        <button
          key={n}
          onClick={() => onChange(n)}
          className={`size-8 rounded-lg font-semibold text-[12.5px] transition-colors ${
            n === page ? "bg-[#2563EB] text-white" : "text-[#475569] hover:bg-[#F1F5F9]"
          }`}
        >
          {n}
        </button>
      ))}
      <span className="px-1 text-[#94A3B8]">...</span>
      <button
        onClick={() => onChange(total)}
        className={`size-8 rounded-lg font-semibold text-[12.5px] transition-colors ${
          total === page ? "bg-[#2563EB] text-white" : "text-[#475569] hover:bg-[#F1F5F9]"
        }`}
      >
        {total}
      </button>
      <button
        onClick={() => page < total && onChange(page + 1)}
        className="size-8 rounded-lg grid place-items-center hover:bg-[#F1F5F9] text-[#64748B] disabled:opacity-40"
        disabled={page === total}
        aria-label="Next"
      >
        <ChevronRight size={14} />
      </button>
    </div>
  );
}