import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  CheckSquare,
  Plus,
  Loader2,
  X,
  Circle,
  CircleDot,
  CheckCircle2,
  XCircle,
  User as UserIcon,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

const COLUMNS = [
  { key: "open", label: "Open", icon: Circle, tint: "text-[#64748B]", accent: "bg-[#F1F5F9]" },
  { key: "in_progress", label: "In Progress", icon: CircleDot, tint: "text-[#4F46E5]", accent: "bg-[#EEF2FF]" },
  { key: "done", label: "Done", icon: CheckCircle2, tint: "text-[#16A34A]", accent: "bg-[#F0FDF4]" },
  { key: "cancelled", label: "Cancelled", icon: XCircle, tint: "text-[#94A3B8]", accent: "bg-[#F8FAFC]" },
];

const NEXT_STATUS = { open: "in_progress", in_progress: "done", done: "open", cancelled: "open" };

function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

function CreateTaskModal({ members, onClose, onCreated }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assignee, setAssignee] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!title.trim()) {
      toast.error("Enter a task title.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/tasks", {
        title: title.trim(),
        description: description.trim() || null,
        assignee_user_id: assignee || null,
      });
      toast.success("Task created");
      onCreated();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-bold text-[#0F172A]">New task</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-[#94A3B8] hover:bg-[#F1F5F9]">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-5 space-y-4">
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Title</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What needs to be done?"
              className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Add details…"
              className="w-full resize-none rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Assignee</label>
            <select
              value={assignee}
              onChange={(e) => setAssignee(e.target.value)}
              className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            >
              <option value="">Unassigned</option>
              {members.map((m) => (
                <option key={m.user_id} value={m.user_id}>
                  {m.name} ({m.email})
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl px-4 py-2 text-sm font-semibold text-[#475569] hover:bg-[#F1F5F9]">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Create task
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export default function Tasks() {
  const [tasks, setTasks] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [mineOnly, setMineOnly] = useState(false);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, m] = await Promise.all([
        api.get("/tasks", { params: mineOnly ? { mine: true } : {} }),
        api.get("/collab/members"),
      ]);
      setTasks(Array.isArray(t.data?.tasks) ? t.data.tasks : []);
      setMembers(Array.isArray(m.data?.members) ? m.data.members : []);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, [mineOnly]);

  useEffect(() => {
    load();
  }, [load]);

  const advance = async (task) => {
    const next = NEXT_STATUS[task.status] || "open";
    setBusyId(task.id);
    try {
      await api.put(`/tasks/${task.id}`, { status: next });
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyId(null);
    }
  };

  const setStatus = async (task, status) => {
    setBusyId(task.id);
    try {
      await api.put(`/tasks/${task.id}`, { status });
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyId(null);
    }
  };

  const grouped = useMemo(() => {
    const g = { open: [], in_progress: [], done: [], cancelled: [] };
    for (const t of tasks) (g[t.status] || g.open).push(t);
    return g;
  }, [tasks]);

  if (loading) {
    return (
      <div className="grid h-[60vh] place-items-center">
        <Loader2 className="h-6 w-6 animate-spin text-[#4F46E5]" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-6xl space-y-6 p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#FEF3C7] text-[#B45309]">
            <CheckSquare className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#0F172A]">Tasks</h1>
            <p className="text-sm text-[#64748B]">Track and assign work across your workspace.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMineOnly((v) => !v)}
            className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-semibold transition ${
              mineOnly
                ? "border-[#4F46E5] bg-[#EEF2FF] text-[#4F46E5]"
                : "border-[#E2E8F0] bg-white text-[#475569] hover:bg-[#F8FAFC]"
            }`}
          >
            <UserIcon className="h-4 w-4" /> Assigned to me
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]"
          >
            <Plus className="h-4 w-4" /> New task
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {COLUMNS.map((col) => (
          <div key={col.key} className="rounded-2xl border border-[#E2E8F0] bg-[#FBFCFE]">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] px-4 py-3">
              <div className="flex items-center gap-2">
                <col.icon className={`h-4 w-4 ${col.tint}`} />
                <span className="text-sm font-bold text-[#0F172A]">{col.label}</span>
              </div>
              <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-[#64748B]">
                {grouped[col.key].length}
              </span>
            </div>
            <div className="space-y-2 p-3">
              {grouped[col.key].length === 0 ? (
                <p className="py-6 text-center text-[12px] text-[#94A3B8]">No tasks</p>
              ) : (
                grouped[col.key].map((task) => (
                  <div key={task.id} className="rounded-xl border border-[#E2E8F0] bg-white p-3 shadow-sm">
                    <p className="text-sm font-semibold text-[#0F172A]">{task.title}</p>
                    {task.description && (
                      <p className="mt-1 line-clamp-2 text-[12px] text-[#64748B]">{task.description}</p>
                    )}
                    <div className="mt-3 flex items-center justify-between">
                      {task.assignee ? (
                        <span className="inline-flex items-center gap-1.5 text-[11px] text-[#64748B]">
                          <span className="grid h-5 w-5 place-items-center rounded-full bg-[#EEF2FF] text-[9px] font-bold text-[#4F46E5]">
                            {initials(task.assignee.name) || "•"}
                          </span>
                          {task.assignee.name}
                        </span>
                      ) : (
                        <span className="text-[11px] text-[#94A3B8]">Unassigned</span>
                      )}
                      <div className="flex items-center gap-1">
                        {task.status !== "done" && task.status !== "cancelled" && (
                          <button
                            onClick={() => advance(task)}
                            disabled={busyId === task.id}
                            className="rounded-lg bg-[#EEF2FF] px-2 py-1 text-[11px] font-semibold text-[#4F46E5] hover:bg-[#E0E7FF] disabled:opacity-50"
                          >
                            {task.status === "open" ? "Start" : "Complete"}
                          </button>
                        )}
                        {task.status !== "cancelled" && task.status !== "done" && (
                          <button
                            onClick={() => setStatus(task, "cancelled")}
                            disabled={busyId === task.id}
                            className="rounded-lg p-1 text-[#94A3B8] hover:bg-[#F1F5F9] hover:text-[#DC2626] disabled:opacity-50"
                            aria-label="Cancel task"
                          >
                            <XCircle className="h-4 w-4" />
                          </button>
                        )}
                        {(task.status === "done" || task.status === "cancelled") && (
                          <button
                            onClick={() => setStatus(task, "open")}
                            disabled={busyId === task.id}
                            className="rounded-lg px-2 py-1 text-[11px] font-semibold text-[#64748B] hover:bg-[#F1F5F9] disabled:opacity-50"
                          >
                            Reopen
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      {showCreate && (
        <CreateTaskModal
          members={members}
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}
    </motion.div>
  );
}
