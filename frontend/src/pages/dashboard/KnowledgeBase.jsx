import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  BookOpen,
  FileText,
  Layers,
  Plus,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { PageHeader } from "@/components/dashboard/kit";

const STATUS_BADGE = {
  draft: "bg-[#F1F5F9] text-[#64748B]",
  active: "bg-green-50 text-green-700",
  archived: "bg-amber-50 text-amber-700",
};

export default function KnowledgeBase() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState({
    total_knowledge_bases: 0,
    total_documents: 0,
    total_chunks: 0,
    total_embeddings: 0,
  });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // Open the create modal when the Top Bar CTA navigates here with { create: true }.
  useEffect(() => {
    if (location.state?.create) {
      setCreating(true);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, location.pathname, navigate]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = search ? { q: search } : undefined;
      // Load list + stats independently so an empty/unseeded workspace (which
      // can 404 on either endpoint) still renders a clean empty state rather
      // than surfacing an error toast.
      const [listRes, statsRes] = await Promise.allSettled([
        api.get("/knowledge-bases", { params }),
        api.get("/knowledge/stats"),
      ]);
      setItems(listRes.status === "fulfilled" ? listRes.value.data.items || [] : []);
      if (statsRes.status === "fulfilled") setStats(statsRes.value.data);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    load();
  }, [load]);

  const remove = async (kb) => {
    if (!window.confirm(`Delete "${kb.name}"?`)) return;
    try {
      await api.delete(`/knowledge-bases/${kb.id}`);
      toast.success("Knowledge base deleted");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const kpis = useMemo(
    () => [
      {
        key: "kbs",
        icon: BookOpen,
        color: "#2563EB",
        label: "Knowledge Bases",
        value: stats.total_knowledge_bases,
      },
      {
        key: "docs",
        icon: FileText,
        color: "#0891B2",
        label: "Documents",
        value: stats.total_documents,
      },
      {
        key: "chunks",
        icon: Layers,
        color: "#0EA5E9",
        label: "Total Chunks",
        value: stats.total_chunks,
      },
      {
        key: "embeddings",
        icon: Sparkles,
        color: "#059669",
        label: "Embeddings",
        value: stats.total_embeddings,
      },
    ],
    [stats]
  );

  return (
    <div className="space-y-6" data-testid="kb-page">
      {/* Header */}
      <PageHeader
        eyebrow="Knowledge"
        icon={BookOpen}
        title="Knowledge Base"
        subtitle="Train your agents with documents, manuals, and policies."
      />

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((k) => (
          <div
            key={k.key}
            className="p-5 rounded-2xl bg-white border border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)]"
            data-testid={`kb-kpi-${k.key}`}
          >
            <div className="flex items-center gap-3">
              <div
                className="size-11 rounded-2xl grid place-items-center shrink-0"
                style={{ background: `${k.color}1A` }}
              >
                <k.icon size={18} style={{ color: k.color }} />
              </div>
              <div className="min-w-0">
                <p className="text-[12px] text-[#64748B]">{k.label}</p>
                <p className="text-[26px] font-bold tracking-tight text-[#0F172A] leading-none mt-1">
                  {k.value.toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white border border-[#E2E8F0]">
        <Search size={16} className="text-[#94A3B8]" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search knowledge bases…"
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-[#94A3B8]"
          data-testid="kb-search-input"
        />
      </div>

      {/* List */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 rounded-2xl skeleton" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div
          className="p-8 rounded-2xl border-2 border-dashed border-[#E2E8F0] text-center bg-white"
          data-testid="kb-empty-state"
        >
          <div className="mx-auto size-14 rounded-full grid place-items-center bg-[#EFF6FF]">
            <BookOpen size={26} className="text-[#2563EB]" />
          </div>
          <p className="mt-4 text-[16px] font-semibold text-[#0F172A]">
            No knowledge bases yet
          </p>
          <p className="text-sm text-[#475569] mt-1">
            Create one to start uploading documents your agents can reference.
          </p>
          <button
            onClick={() => setCreating(true)}
            data-testid="kb-empty-create-btn"
            className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#2563EB] text-white text-sm font-semibold shadow-sm transition-colors hover:bg-[#1D4ED8]"
          >
            <Plus size={16} /> New Knowledge Base
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((kb) => (
            <motion.div
              key={kb.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-5 rounded-2xl bg-white border border-[#E7EAF1] shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)] hover:shadow-premium hover:-translate-y-0.5 transition-all flex flex-col"
              data-testid={`kb-card-${kb.id}`}
            >
              <div className="flex items-start gap-3">
                <div className="size-11 rounded-xl grid place-items-center bg-[#EFF6FF]">
                  <BookOpen size={18} className="text-[#2563EB]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-[#0F172A] truncate">
                      {kb.name}
                    </h3>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold capitalize ${
                        STATUS_BADGE[kb.status] || STATUS_BADGE.draft
                      }`}
                    >
                      {kb.status}
                    </span>
                  </div>
                  <p className="text-xs text-[#64748B] mt-0.5 line-clamp-2 min-h-[2rem]">
                    {kb.description || "—"}
                  </p>
                </div>
              </div>

              <div className="mt-4 flex items-center gap-4 text-sm">
                <div>
                  <p className="text-xs text-[#64748B]">Documents</p>
                  <p className="font-semibold text-[#0F172A]">
                    {(kb.document_count || 0).toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="mt-auto pt-4 flex items-center gap-2">
                <Link
                  to={`/app/knowledge-base/${kb.id}`}
                  className="flex-1 text-center px-3 py-2 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] text-sm font-medium text-[#0F172A]"
                  data-testid={`kb-open-${kb.id}`}
                >
                  Open
                </Link>
                <button
                  onClick={() => remove(kb)}
                  className="size-9 rounded-xl border border-[#E2E8F0] hover:bg-red-50 hover:border-red-200 grid place-items-center text-red-500"
                  aria-label="Delete"
                  data-testid={`kb-delete-${kb.id}`}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {creating && (
        <CreateKnowledgeBaseModal
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            load();
          }}
        />
      )}
    </div>
  );
}

function CreateKnowledgeBaseModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("active");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    try {
      await api.post("/knowledge-bases", {
        name: name.trim(),
        description: description.trim() || null,
        status,
      });
      toast.success("Knowledge base created");
      onCreated();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 grid place-items-center p-4"
      role="dialog"
      data-testid="kb-create-modal"
    >
      <form
        onSubmit={submit}
        className="w-full max-w-md bg-white rounded-2xl shadow-xl p-6 space-y-4"
      >
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-[#0F172A]">
            New Knowledge Base
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[#F1F5F9]"
            aria-label="Close"
            data-testid="kb-create-close"
          >
            <X size={18} />
          </button>
        </div>

        <div>
          <label className="block text-sm font-medium text-[#0F172A] mb-1.5">
            Name
          </label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Product Docs"
            className="w-full rounded-xl border border-[#E2E8F0] px-4 py-2.5 text-sm"
            data-testid="kb-create-name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[#0F172A] mb-1.5">
            Description
          </label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What's in this knowledge base?"
            className="w-full rounded-xl border border-[#E2E8F0] px-4 py-2.5 text-sm"
            data-testid="kb-create-desc"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[#0F172A] mb-1.5">
            Status
          </label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full rounded-xl border border-[#E2E8F0] px-4 py-2.5 text-sm bg-white"
            data-testid="kb-create-status"
          >
            <option value="draft">Draft</option>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] text-sm font-semibold"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy || !name.trim()}
            className="px-5 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold disabled:opacity-60"
            data-testid="kb-create-submit"
          >
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}
