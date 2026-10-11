import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Lightbulb,
  Bug,
  MessageSquare,
  LifeBuoy,
  ChevronUp,
  Plus,
  Loader2,
  X,
  Trash2,
  Send,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  PageHeader,
  Card,
  Badge,
  PrimaryButton,
  GhostButton,
  EmptyState,
} from "@/components/dashboard/kit";

const TYPES = {
  bug: { label: "Bug", icon: Bug, tone: "red" },
  help: { label: "Help", icon: LifeBuoy, tone: "blue" },
  feature: { label: "Feature", icon: Lightbulb, tone: "indigo" },
  feedback: { label: "Feedback", icon: MessageSquare, tone: "slate" },
};

const PRIORITIES = {
  low: { label: "Low", tone: "slate" },
  medium: { label: "Medium", tone: "blue" },
  high: { label: "High", tone: "amber" },
  urgent: { label: "Urgent", tone: "red" },
};
const PRIORITY_ORDER = ["low", "medium", "high", "urgent"];

const STATUSES = {
  open: { label: "Open", tone: "slate" },
  planned: { label: "Planned", tone: "indigo" },
  in_progress: { label: "In progress", tone: "amber" },
  completed: { label: "Resolved", tone: "green" },
  declined: { label: "Closed", tone: "red" },
};

const TYPE_TABS = [
  { value: "all", label: "All" },
  { value: "bug", label: "Bugs" },
  { value: "help", label: "Help" },
  { value: "feature", label: "Features" },
  { value: "feedback", label: "Feedback" },
];

function SubmitDialog({ open, onClose, onCreated, authorName }) {
  const [type, setType] = useState("help");
  const [priority, setPriority] = useState("medium");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setType("help");
      setPriority("medium");
      setTitle("");
      setDescription("");
    }
  }, [open]);

  const submit = async (e) => {
    e.preventDefault();
    if (title.trim().length < 3) {
      toast.error("Please add a short title (at least 3 characters).");
      return;
    }
    setSaving(true);
    try {
      const { data } = await api.post("/feature-requests", {
        type,
        priority,
        title: title.trim(),
        description: description.trim() || null,
        author_name: authorName || null,
      });
      toast.success("Ticket created — we'll follow up soon.");
      onCreated(data);
      onClose();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[70] flex items-center justify-center bg-black/30 p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.form
            onClick={(e) => e.stopPropagation()}
            onSubmit={submit}
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }}
            data-testid="feature-request-dialog"
            className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-[#F1F5F9] px-5 py-4">
              <h3 className="text-[15px] font-bold text-[#0F172A]">Create a support ticket</h3>
              <button type="button" onClick={onClose} aria-label="Close dialog" className="text-[#94A3B8] hover:text-[#475569]">
                <X size={18} />
              </button>
            </div>
            <div className="space-y-4 p-5">
              <div>
                <label className="mb-1.5 block text-[12.5px] font-semibold text-[#334155]">Type</label>
                <div className="grid grid-cols-4 gap-2">
                  {Object.entries(TYPES).map(([k, t]) => {
                    const Icon = t.icon;
                    const sel = type === k;
                    return (
                      <button
                        key={k}
                        type="button"
                        onClick={() => setType(k)}
                        data-testid={`feature-request-type-${k}`}
                        className={`flex flex-col items-center gap-1.5 rounded-xl border px-2 py-3 text-[12px] font-semibold transition ${
                          sel
                            ? "border-[#2563EB] bg-[#EFF6FF] text-[#1D4ED8]"
                            : "border-[#E2E8F0] text-[#64748B] hover:border-[#BFD3F5]"
                        }`}
                      >
                        <Icon size={17} />
                        {t.label}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-[12.5px] font-semibold text-[#334155]">Priority</label>
                <div className="grid grid-cols-4 gap-2">
                  {PRIORITY_ORDER.map((k) => {
                    const p = PRIORITIES[k];
                    const sel = priority === k;
                    return (
                      <button
                        key={k}
                        type="button"
                        onClick={() => setPriority(k)}
                        data-testid={`ticket-priority-${k}`}
                        className={`rounded-xl border px-2 py-2 text-[12px] font-semibold transition ${
                          sel
                            ? "border-[#2563EB] bg-[#EFF6FF] text-[#1D4ED8]"
                            : "border-[#E2E8F0] text-[#64748B] hover:border-[#BFD3F5]"
                        }`}
                      >
                        {p.label}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div>
                <label className="mb-1 block text-[12.5px] font-semibold text-[#334155]">Title</label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={255}
                  placeholder="Summarize it in one line"
                  data-testid="feature-request-title"
                  className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
                />
              </div>
              <div>
                <label className="mb-1 block text-[12.5px] font-semibold text-[#334155]">Details (optional)</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  maxLength={5000}
                  placeholder="What problem would this solve? Add steps to reproduce for bugs."
                  data-testid="feature-request-description"
                  className="w-full resize-none rounded-xl border border-[#E2E8F0] px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-[#F1F5F9] px-5 py-4">
              <GhostButton type="button" onClick={onClose}>Cancel</GhostButton>
              <PrimaryButton type="submit" disabled={saving} data-testid="feature-request-submit">
                {saving ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                Submit ticket
              </PrimaryButton>
            </div>
          </motion.form>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function RequestRow({ item, onVote, onDelete }) {
  const t = TYPES[item.type] || TYPES.feature;
  const s = STATUSES[item.status] || STATUSES.open;
  const p = PRIORITIES[item.priority];
  const TIcon = t.icon;
  return (
    <div className="flex items-start gap-4 px-5 py-4" data-testid={`feature-request-${item.id}`}>
      <button
        type="button"
        onClick={() => onVote(item)}
        data-testid={`feature-request-vote-${item.id}`}
        className={`flex w-14 shrink-0 flex-col items-center gap-0.5 rounded-xl border py-2 transition ${
          item.has_voted
            ? "border-[#2563EB] bg-[#EFF6FF] text-[#1D4ED8]"
            : "border-[#E2E8F0] text-[#64748B] hover:border-[#BFD3F5] hover:bg-[#F8FAFC]"
        }`}
        aria-pressed={item.has_voted}
      >
        <ChevronUp size={16} />
        <span className="text-[13px] font-bold">{item.votes}</span>
      </button>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={t.tone} className="inline-flex items-center gap-1">
            <TIcon size={11} />
            {t.label}
          </Badge>
          {p && <Badge tone={p.tone}>{p.label} priority</Badge>}
          <Badge tone={s.tone}>{s.label}</Badge>
        </div>
        <p className="mt-1.5 text-[14px] font-semibold text-[#0F172A]">{item.title}</p>
        {item.description && (
          <p className="mt-1 whitespace-pre-wrap text-[13px] leading-relaxed text-[#64748B]">{item.description}</p>
        )}
        <p className="mt-1.5 text-[11.5px] text-[#94A3B8]">
          {item.author_name ? `${item.author_name} · ` : ""}
          {new Date(item.created_at).toLocaleDateString()}
        </p>
      </div>
      {item.is_author && (
        <button
          type="button"
          onClick={() => onDelete(item)}
          data-testid={`feature-request-delete-${item.id}`}
          className="shrink-0 rounded-lg p-1.5 text-[#94A3B8] transition hover:bg-[#FEF2F2] hover:text-[#DC2626]"
          aria-label="Delete"
        >
          <Trash2 size={15} />
        </button>
      )}
    </div>
  );
}

export default function FeatureRequests() {
  const { user } = useAuth();
  const authorName = user?.name || user?.full_name || user?.email || null;
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("all");
  const [sort, setSort] = useState("top");
  const [dialogOpen, setDialogOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { sort };
      if (tab !== "all") params.type = tab;
      const { data } = await api.get("/feature-requests", { params });
      setItems(data.items || []);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [tab, sort]);

  useEffect(() => {
    load();
  }, [load]);

  const onVote = async (item) => {
    // optimistic
    setItems((prev) =>
      prev.map((r) =>
        r.id === item.id
          ? { ...r, has_voted: !r.has_voted, votes: r.votes + (r.has_voted ? -1 : 1) }
          : r
      )
    );
    try {
      const { data } = await api.post(`/feature-requests/${item.id}/vote`);
      setItems((prev) => prev.map((r) => (r.id === item.id ? data : r)));
    } catch (err) {
      toast.error(formatApiError(err));
      load();
    }
  };

  const onDelete = async (item) => {
    setItems((prev) => prev.filter((r) => r.id !== item.id));
    try {
      await api.delete(`/feature-requests/${item.id}`);
      toast.success("Removed.");
    } catch (err) {
      toast.error(formatApiError(err));
      load();
    }
  };

  const onCreated = (created) => {
    if (tab === "all" || tab === created.type) {
      setItems((prev) => [created, ...prev]);
    }
  };

  const sorted = useMemo(() => items, [items]);

  return (
    <div className="space-y-6">
      <PageHeader
        icon={LifeBuoy}
        eyebrow="Support"
        title="Support Tickets"
        subtitle="Report a bug, ask for help, or suggest an idea — set a priority and we'll follow up."
        actions={
          <PrimaryButton onClick={() => setDialogOpen(true)} data-testid="feature-request-new">
            <Plus size={15} />
            New ticket
          </PrimaryButton>
        }
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-xl bg-[#F1F5F9] p-1">
          {TYPE_TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              data-testid={`feature-request-tab-${t.value}`}
              className={`rounded-lg px-3.5 py-1.5 text-[13px] font-semibold transition ${
                tab === t.value ? "bg-white text-[#0F172A] shadow-sm" : "text-[#64748B] hover:text-[#0F172A]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="inline-flex rounded-xl bg-[#F1F5F9] p-1">
          {["top", "new"].map((s) => (
            <button
              key={s}
              onClick={() => setSort(s)}
              className={`rounded-lg px-3.5 py-1.5 text-[13px] font-semibold capitalize transition ${
                sort === s ? "bg-white text-[#0F172A] shadow-sm" : "text-[#64748B] hover:text-[#0F172A]"
              }`}
            >
              {s === "top" ? "Top voted" : "Newest"}
            </button>
          ))}
        </div>
      </div>

      <Card className="overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-[#94A3B8]">
            <Loader2 className="animate-spin" size={22} />
          </div>
        ) : sorted.length === 0 ? (
          <div className="p-6">
            <EmptyState
              icon={LifeBuoy}
              title="No tickets yet"
              hint="Create a ticket for a bug, a question, or an idea and we'll take it from there."
              action={
                <PrimaryButton onClick={() => setDialogOpen(true)}>
                  <Plus size={15} />
                  New ticket
                </PrimaryButton>
              }
            />
          </div>
        ) : (
          <div className="divide-y divide-[#F1F5F9]">
            {sorted.map((item) => (
              <RequestRow key={item.id} item={item} onVote={onVote} onDelete={onDelete} />
            ))}
          </div>
        )}
      </Card>

      <SubmitDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onCreated={onCreated}
        authorName={authorName}
      />
    </div>
  );
}
