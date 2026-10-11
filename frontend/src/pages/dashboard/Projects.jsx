import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FolderKanban,
  Plus,
  X,
  Loader2,
  Check,
  Trash2,
  Pencil,
  Bot,
  BookOpen,
  MessagesSquare,
  Globe,
  Star,
  Archive,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { useProjects } from "@/lib/projects";

const SWATCHES = ["#2563EB", "#06B6D4", "#0EA5E9", "#F59E0B", "#10B981", "#EF4444", "#EC4899", "#0F172A"];

const COUNT_META = [
  { key: "agents", label: "Agents", icon: Bot },
  { key: "knowledge_bases", label: "Knowledge", icon: BookOpen },
  { key: "conversations", label: "Chats", icon: MessagesSquare },
  { key: "websites", label: "Websites", icon: Globe },
];

function emptyForm() {
  return { name: "", description: "", color: SWATCHES[0] };
}

function ProjectModal({ open, mode, initial, onClose, onSaved }) {
  const [form, setForm] = useState(initial || emptyForm());
  const [saving, setSaving] = useState(false);

  React.useEffect(() => {
    if (open) setForm(initial || emptyForm());
  }, [open, initial]);

  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.error("Project name is required");
      return;
    }
    setSaving(true);
    try {
      if (mode === "edit") {
        await api.patch(`/projects/${initial.id}`, {
          name: form.name.trim(),
          description: form.description?.trim() || null,
          color: form.color,
        });
        toast.success("Project updated");
      } else {
        await api.post("/projects", {
          name: form.name.trim(),
          description: form.description?.trim() || null,
          color: form.color,
        });
        toast.success("Project created");
      }
      onSaved();
      onClose();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <div className="absolute inset-0 bg-[#0F172A]/50 backdrop-blur-sm" onClick={onClose} />
      <motion.form
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        onSubmit={submit}
        className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"
        data-testid="project-modal"
      >
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-bold text-[#0F172A]">
            {mode === "edit" ? "Edit project" : "New project"}
          </h2>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-[#64748B] hover:bg-[#F1F5F9]">
            <X size={18} />
          </button>
        </div>

        <label className="mb-1.5 block text-sm font-medium text-[#334155]">Name</label>
        <input
          autoFocus
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="e.g. Acme Storefront"
          maxLength={160}
          className="mb-4 w-full rounded-xl border border-[#E2E8F0] px-3.5 py-2.5 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20"
          data-testid="project-name-input"
        />

        <label className="mb-1.5 block text-sm font-medium text-[#334155]">Description</label>
        <textarea
          value={form.description}
          onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          placeholder="What is this project for?"
          rows={3}
          className="mb-4 w-full resize-none rounded-xl border border-[#E2E8F0] px-3.5 py-2.5 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20"
        />

        <label className="mb-2 block text-sm font-medium text-[#334155]">Color</label>
        <div className="mb-6 flex flex-wrap gap-2">
          {SWATCHES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setForm((f) => ({ ...f, color: c }))}
              className={`size-8 rounded-lg transition-transform ${
                form.color === c ? "ring-2 ring-offset-2 ring-[#0F172A] scale-105" : ""
              }`}
              style={{ background: c }}
              aria-label={`Color ${c}`}
            >
              {form.color === c && <Check size={16} className="mx-auto text-white" />}
            </button>
          ))}
        </div>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl px-4 py-2.5 text-sm font-medium text-[#475569] hover:bg-[#F1F5F9]"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-full bg-[#2563EB] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#1D4ED8] disabled:opacity-60"
            data-testid="project-save-btn"
          >
            {saving && <Loader2 size={16} className="animate-spin" />}
            {mode === "edit" ? "Save changes" : "Create project"}
          </button>
        </div>
      </motion.form>
    </div>
  );
}

export default function Projects() {
  const { projects, activeProjectId, loading, refreshProjects, switchProject } = useProjects();
  const [modal, setModal] = useState({ open: false, mode: "create", initial: null });
  const [busyId, setBusyId] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Open the create modal automatically when arriving via the project
  // switcher's "New project" action (passes location state).
  useEffect(() => {
    if (location.state?.openCreate) {
      setModal({ open: true, mode: "create", initial: null });
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, location.pathname, navigate]);

  const totalProjects = projects.length;
  const totalResources = useMemo(
    () =>
      projects.reduce((sum, p) => {
        const c = p.resource_counts || {};
        return sum + Object.values(c).reduce((a, b) => a + (Number(b) || 0), 0);
      }, 0),
    [projects]
  );

  const openCreate = () => setModal({ open: true, mode: "create", initial: null });
  const openEdit = (p) =>
    setModal({
      open: true,
      mode: "edit",
      initial: { id: p.id, name: p.name, description: p.description || "", color: p.color || SWATCHES[0] },
    });

  const handleDelete = async (p) => {
    if (p.is_default) {
      toast.error("The default project can't be deleted");
      return;
    }
    const counts = p.resource_counts || {};
    const used = Object.values(counts).reduce((a, b) => a + (Number(b) || 0), 0);
    if (used > 0) {
      toast.error("Move or remove this project's resources before deleting it");
      return;
    }
    if (!window.confirm(`Delete project "${p.name}"? This can't be undone.`)) return;
    setBusyId(p.id);
    try {
      await api.delete(`/projects/${p.id}`);
      toast.success("Project deleted");
      refreshProjects();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setBusyId(null);
    }
  };

  const handleArchiveToggle = async (p) => {
    if (p.is_default) {
      toast.error("The default project can't be archived");
      return;
    }
    const next = p.status === "archived" ? "active" : "archived";
    setBusyId(p.id);
    try {
      await api.patch(`/projects/${p.id}`, { status: next });
      toast.success(next === "archived" ? "Project archived" : "Project restored");
      refreshProjects();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div data-testid="projects-page">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2.5 text-2xl font-bold text-[#0F172A]">
            <FolderKanban className="text-[#2563EB]" size={26} />
            Projects
          </h1>
          <p className="mt-1 text-sm text-[#64748B]">
            Organize your workspace into projects. Each project keeps its own agents, knowledge, and conversations.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="inline-flex items-center gap-2 rounded-full bg-[#2563EB] px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#1D4ED8]"
          data-testid="new-project-btn"
        >
          <Plus size={18} />
          New project
        </button>
      </div>

      {!loading && totalProjects > 0 && (
        <div className="mb-6 flex gap-3 text-sm">
          <span className="rounded-full bg-white px-3 py-1.5 font-medium text-[#475569] shadow-sm ring-1 ring-[#E2E8F0]">
            {totalProjects} {totalProjects === 1 ? "project" : "projects"}
          </span>
          <span className="rounded-full bg-white px-3 py-1.5 font-medium text-[#475569] shadow-sm ring-1 ring-[#E2E8F0]">
            {totalResources} total resources
          </span>
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-44 animate-pulse rounded-2xl bg-[#F1F5F9]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence>
            {projects.map((p) => {
              const active = p.id === activeProjectId;
              const archived = p.status === "archived";
              const counts = p.resource_counts || {};
              return (
                <motion.div
                  key={p.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.97 }}
                  className={`flex flex-col rounded-2xl border bg-white p-5 shadow-sm transition-shadow hover:shadow-md ${
                    active ? "border-[#2563EB] ring-1 ring-[#2563EB]" : "border-[#E2E8F0]"
                  } ${archived ? "opacity-70" : ""}`}
                  data-testid="project-card"
                >
                  <div className="mb-3 flex items-start gap-3">
                    <span
                      className="grid size-10 flex-shrink-0 place-items-center rounded-xl text-white"
                      style={{ background: p.color || SWATCHES[0] }}
                    >
                      <FolderKanban size={20} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="truncate font-semibold text-[#0F172A]">{p.name}</h3>
                        {p.is_default && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-[#EFF6FF] px-2 py-0.5 text-[11px] font-semibold text-[#2563EB]">
                            <Star size={10} /> Default
                          </span>
                        )}
                        {archived && (
                          <span className="rounded-full bg-[#F1F5F9] px-2 py-0.5 text-[11px] font-semibold text-[#64748B]">
                            Archived
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 line-clamp-2 text-xs text-[#64748B]">
                        {p.description || "No description"}
                      </p>
                    </div>
                  </div>

                  <div className="mb-4 grid grid-cols-4 gap-2">
                    {COUNT_META.map(({ key, label, icon: Icon }) => (
                      <div key={key} className="rounded-lg bg-[#F8FAFC] p-2 text-center">
                        <Icon size={14} className="mx-auto text-[#94A3B8]" />
                        <div className="mt-1 text-sm font-bold text-[#0F172A]">{counts[key] ?? 0}</div>
                        <div className="text-[10px] text-[#94A3B8]">{label}</div>
                      </div>
                    ))}
                  </div>

                  <div className="mt-auto flex items-center gap-2">
                    {active ? (
                      <span className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-[#EFF6FF] px-3 py-2 text-sm font-semibold text-[#2563EB]">
                        <Check size={15} /> Active
                      </span>
                    ) : (
                      <button
                        onClick={() => switchProject(p.id)}
                        disabled={archived}
                        className="flex-1 rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm font-medium text-[#334155] hover:bg-[#F8FAFC] disabled:opacity-50"
                        data-testid="switch-project-btn"
                      >
                        Switch to
                      </button>
                    )}
                    <button
                      onClick={() => openEdit(p)}
                      className="rounded-xl border border-[#E2E8F0] p-2 text-[#475569] hover:bg-[#F8FAFC]"
                      aria-label="Edit project"
                    >
                      <Pencil size={15} />
                    </button>
                    {!p.is_default && (
                      <button
                        onClick={() => handleArchiveToggle(p)}
                        disabled={busyId === p.id}
                        className="rounded-xl border border-[#E2E8F0] p-2 text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-50"
                        aria-label={archived ? "Restore project" : "Archive project"}
                      >
                        <Archive size={15} />
                      </button>
                    )}
                    {!p.is_default && (
                      <button
                        onClick={() => handleDelete(p)}
                        disabled={busyId === p.id}
                        className="rounded-xl border border-[#E2E8F0] p-2 text-[#EF4444] hover:bg-red-50 disabled:opacity-50"
                        aria-label="Delete project"
                      >
                        {busyId === p.id ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
                      </button>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {/* Add-project tile */}
          <button
            onClick={openCreate}
            className="flex min-h-44 flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#CBD5E1] p-5 text-[#64748B] transition-colors hover:border-[#2563EB] hover:text-[#2563EB]"
            data-testid="add-project-tile"
          >
            <Plus size={24} />
            <span className="text-sm font-medium">New project</span>
          </button>
        </div>
      )}

      <ProjectModal
        open={modal.open}
        mode={modal.mode}
        initial={modal.initial}
        onClose={() => setModal((m) => ({ ...m, open: false }))}
        onSaved={refreshProjects}
      />
    </div>
  );
}
