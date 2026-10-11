import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  ScrollText,
  Loader2,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Filter,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

const ACTION_STYLES = {
  create: { bg: "#DCFCE7", fg: "#15803D" },
  update: { bg: "#DBEAFE", fg: "#1D4ED8" },
  delete: { bg: "#FEE2E2", fg: "#B91C1C" },
  read: { bg: "#F1F5F9", fg: "#475569" },
};

function ActionBadge({ action }) {
  const s = ACTION_STYLES[action] || { bg: "#F1F5F9", fg: "#475569" };
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold capitalize"
      style={{ backgroundColor: s.bg, color: s.fg }}
    >
      {action}
    </span>
  );
}

function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function JsonBlock({ label, data }) {
  if (data == null) return null;
  return (
    <div className="min-w-0 flex-1">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[#94A3B8]">
        {label}
      </p>
      <pre className="overflow-x-auto rounded-lg bg-[#0F172A] p-3 text-xs leading-relaxed text-[#E2E8F0] scrollbar-thin">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

const PAGE_SIZE = 50;

export default function AuditLogs() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState({});
  const [filters, setFilters] = useState({ action: "", resource: "", days: "" });
  const [offset, setOffset] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: PAGE_SIZE, offset };
      if (filters.action) params.action = filters.action;
      if (filters.resource) params.resource = filters.resource;
      if (filters.days) params.days = filters.days;
      const { data } = await api.get("/audit-logs", { params });
      setData(data);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, [filters, offset]);

  useEffect(() => {
    load();
  }, [load]);

  const logs = data?.logs || [];
  const total = data?.total || 0;
  const actors = data?.actors || {};
  const hasFilters = filters.action || filters.resource || filters.days;

  const setFilter = (k) => (v) => {
    setOffset(0);
    setFilters((f) => ({ ...f, [k]: v }));
  };
  const clearFilters = () => {
    setOffset(0);
    setFilters({ action: "", resource: "", days: "" });
  };

  const actorLabel = (uid) => {
    if (!uid) return "System";
    const a = actors[uid];
    return a?.name || a?.email || `${uid.slice(0, 8)}…`;
  };

  const pageInfo = useMemo(() => {
    if (!total) return "No events";
    const from = offset + 1;
    const to = Math.min(offset + logs.length, total);
    return `${from}–${to} of ${total}`;
  }, [offset, logs.length, total]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-[#0F172A]">
            <ScrollText size={24} /> Audit Log
          </h1>
          <p className="mt-1 text-sm text-[#64748B]">
            Every change in your workspace, captured for security and compliance.
          </p>
        </div>
        <button
          onClick={load}
          data-testid="audit-refresh"
          className="inline-flex items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
        >
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[#E2E8F0] bg-white p-4">
        <span className="flex items-center gap-1.5 text-sm font-medium text-[#64748B]">
          <Filter size={15} /> Filters
        </span>
        <select
          value={filters.action}
          onChange={(e) => setFilter("action")(e.target.value)}
          data-testid="audit-filter-action"
          className="rounded-lg border border-[#E2E8F0] px-3 py-1.5 text-sm outline-none focus:border-[#2563EB]"
        >
          <option value="">All actions</option>
          {(data?.actions || []).map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <select
          value={filters.resource}
          onChange={(e) => setFilter("resource")(e.target.value)}
          data-testid="audit-filter-resource"
          className="rounded-lg border border-[#E2E8F0] px-3 py-1.5 text-sm outline-none focus:border-[#2563EB]"
        >
          <option value="">All resources</option>
          {(data?.resources || []).map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <select
          value={filters.days}
          onChange={(e) => setFilter("days")(e.target.value)}
          data-testid="audit-filter-days"
          className="rounded-lg border border-[#E2E8F0] px-3 py-1.5 text-sm outline-none focus:border-[#2563EB]"
        >
          <option value="">All time</option>
          <option value="1">Last 24 hours</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
        </select>
        {hasFilters && (
          <button
            onClick={clearFilters}
            className="inline-flex items-center gap-1 text-sm font-medium text-[#64748B] hover:text-[#0F172A]"
          >
            <X size={14} /> Clear
          </button>
        )}
        <span className="ml-auto text-xs text-[#94A3B8]">{pageInfo}</span>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white">
        {loading ? (
          <div className="grid h-64 place-items-center text-[#64748B]">
            <Loader2 className="animate-spin" />
          </div>
        ) : logs.length === 0 ? (
          <div className="grid h-64 place-items-center px-6 text-center">
            <div>
              <ScrollText size={32} className="mx-auto text-[#CBD5E1]" />
              <p className="mt-3 text-sm font-medium text-[#475569]">No audit events</p>
              <p className="mt-1 text-xs text-[#94A3B8]">
                {hasFilters
                  ? "No events match your filters."
                  : "Actions across your workspace will appear here."}
              </p>
            </div>
          </div>
        ) : (
          <div className="divide-y divide-[#F1F5F9]">
            {logs.map((l) => {
              const open = !!expanded[l.id];
              const hasDetail = l.before || l.after || l.meta;
              return (
                <div key={l.id} data-testid={`audit-row-${l.id}`}>
                  <button
                    onClick={() =>
                      hasDetail && setExpanded((e) => ({ ...e, [l.id]: !e[l.id] }))
                    }
                    className={`flex w-full items-center gap-3 px-4 py-3 text-left ${
                      hasDetail ? "hover:bg-[#F8FAFC]" : "cursor-default"
                    }`}
                  >
                    <span className="w-4 shrink-0 text-[#94A3B8]">
                      {hasDetail ? (
                        open ? <ChevronDown size={15} /> : <ChevronRight size={15} />
                      ) : null}
                    </span>
                    <span className="w-20 shrink-0">
                      <ActionBadge action={l.action} />
                    </span>
                    <span className="w-36 shrink-0 truncate text-sm font-medium text-[#0F172A]">
                      {l.resource}
                      {l.resource_id && (
                        <span className="ml-1 font-mono text-xs text-[#94A3B8]">
                          {String(l.resource_id).slice(0, 8)}
                        </span>
                      )}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm text-[#475569]">
                      {actorLabel(l.user_id)}
                    </span>
                    <span className="shrink-0 text-xs text-[#94A3B8]">
                      {fmtTime(l.created_at)}
                    </span>
                  </button>
                  {open && hasDetail && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="overflow-hidden bg-[#F8FAFC] px-11 py-4"
                    >
                      <div className="flex flex-col gap-4 sm:flex-row">
                        <JsonBlock label="Before" data={l.before} />
                        <JsonBlock label="After" data={l.after} />
                        <JsonBlock label="Meta" data={l.meta} />
                      </div>
                    </motion.div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
            disabled={offset === 0}
            data-testid="audit-prev"
            className="rounded-xl border border-[#E2E8F0] bg-white px-4 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-xs text-[#94A3B8]">{pageInfo}</span>
          <button
            onClick={() => setOffset((o) => o + PAGE_SIZE)}
            disabled={offset + PAGE_SIZE >= total}
            data-testid="audit-next"
            className="rounded-xl border border-[#E2E8F0] bg-white px-4 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
