import React, { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Plus,
  MessageSquare,
  MessageCircle,
  Bot,
  Power,
  PauseCircle,
  AlertTriangle,
  Trash2,
  Sparkles,
  Users,
  Rocket,
  Copy,
  ExternalLink,
  Cpu,
  Clock,
  Code2,
} from "lucide-react";
import { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { DASH } from "@/constants/testIds";
import { StatCard, PrimaryButton, GhostButton, cx } from "@/components/dashboard/kit";
import EntityListPage from "@/components/dashboard/EntityListPage";
import { MenuItem } from "@/components/dashboard/DataTable";
import Drawer from "@/components/dashboard/Drawer";
import {
  useAgents,
  useUpdateAgent,
  useDeleteAgent,
  useDuplicateAgent,
  useBulkUpdateAgentStatus,
  useBulkDeleteAgents,
} from "@/features/agents/hooks/useAgents";

const TYPE_META = {
  chat:     { icon: MessageSquare, color: "#0891B2", label: "Chat Agent",     desc: "Chats on your website and engages visitors." },
  whatsapp: { icon: MessageCircle, color: "#22C55E", label: "WhatsApp Agent", desc: "AI that replies on WhatsApp." },
};

// Agents behave like cloud services: Draft → Active ⇄ Paused → Archived.
const STATUS_META = {
  draft:    { label: "Draft",    dot: "#94A3B8", badge: "bg-[#F1F5F9] text-[#475569]" },
  active:   { label: "Active",   dot: "#22C55E", badge: "bg-green-50 text-green-700" },
  paused:   { label: "Paused",   dot: "#F59E0B", badge: "bg-amber-50 text-amber-700" },
  archived: { label: "Archived", dot: "#64748B", badge: "bg-[#E2E8F0] text-[#475569]" },
};

const fmtRelative = (iso) => {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diff = Math.max(0, Date.now() - then);
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
};

// Stable reference so `agents` doesn't change identity on every render when
// the query has no data yet — avoids re-triggering memoized derivations.
const EMPTY_AGENTS = [];

export default function Agents() {
  const nav = useNavigate();
  const [active, setActive] = useState(null);

  const { data, isLoading } = useAgents();
  const agents = data?.items || EMPTY_AGENTS;

  const updateAgent = useUpdateAgent();
  const deleteAgent = useDeleteAgent();
  const duplicateAgent = useDuplicateAgent();
  const bulkUpdateStatus = useBulkUpdateAgentStatus();
  const bulkDeleteAgents = useBulkDeleteAgents();

  const setStatus = async (a, newStatus) => {
    try {
      await updateAgent.mutateAsync({ id: a.id, payload: { status: newStatus } });
      toast.success(newStatus === "active" ? "Agent activated" : `Agent ${newStatus}`);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  // Cloud-service toggle: Active ⇄ Paused. An agent can only switch ON once it
  // meets the minimum requirements (a system prompt).
  const toggleStatus = (a) => {
    if (a.status === "active") return setStatus(a, "paused");
    if (a.is_ready === false) {
      toast.error("Agent is incomplete — add a system prompt before activating.");
      return;
    }
    return setStatus(a, "active");
  };

  const remove = async (a) => {
    if (!window.confirm(`Delete "${a.name}"?`)) return;
    try {
      await deleteAgent.mutateAsync(a.id);
      toast.success("Agent deleted");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  // Clone an agent by reading its full config and creating a fresh draft copy.
  const duplicate = async (a) => {
    try {
      await duplicateAgent.mutateAsync(a.id);
      toast.success("Agent duplicated");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  // Bulk operations over the current selection.
  const bulkStatus = async (sel, clear, status) => {
    try {
      await bulkUpdateStatus.mutateAsync({ ids: sel.filter((a) => a.status !== status).map((a) => a.id), status });
      clear();
      toast.success(status === "active" ? "Agents activated" : `Agents ${status}`);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };
  const bulkDelete = async (sel, clear) => {
    if (!window.confirm(`Delete ${sel.length} agent${sel.length > 1 ? "s" : ""}?`)) return;
    try {
      await bulkDeleteAgents.mutateAsync(sel.map((a) => a.id));
      clear();
      toast.success("Agents deleted");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const stats = useMemo(() => {
    const total = agents.length;
    const activeCount = agents.filter((a) => a.status === "active").length;
    const paused = agents.filter((a) => a.status === "paused").length;
    const conversations = agents.reduce((sum, a) => sum + (a.conversations || 0), 0);
    const leads = agents.reduce((sum, a) => sum + (a.leads_generated || 0), 0);
    const pct = (n) => (total ? Math.round((n / total) * 100) : 0);
    return [
      { key: "total",         icon: Bot,         color: "#2563EB", label: "Total Agents",          value: total,         sub: `${activeCount} active` },
      { key: "active",        icon: Power,       color: "#22C55E", label: "Active Agents",         value: activeCount,   sub: `${pct(activeCount)}% of total` },
      { key: "paused",        icon: PauseCircle, color: "#F59E0B", label: "Paused Agents",         value: paused,        sub: `${pct(paused)}% of total` },
      { key: "conversations", icon: Sparkles,    color: "#F59E0B", label: "Total Conversations",   value: conversations, sub: "this month" },
      { key: "leads",         icon: Users,       color: "#0EA5E9", label: "Total Leads Generated", value: leads,         sub: "this month" },
    ];
  }, [agents]);

  const columns = useMemo(
    () => [
      {
        key: "name",
        header: "Agent",
        sortable: true,
        minWidth: 240,
        render: (a) => {
          const meta = TYPE_META[a.type] || TYPE_META.chat;
          const Icon = meta.icon;
          return (
            <div className="flex items-center gap-3">
              <span className="grid size-9 shrink-0 place-items-center rounded-xl" style={{ background: `${meta.color}1A` }}>
                <Icon size={16} style={{ color: meta.color }} />
              </span>
              <div className="min-w-0">
                <p className="truncate font-semibold text-[#0F172A]">{a.name}</p>
                <p className="text-[12px] text-[#64748B]">{meta.label}</p>
              </div>
            </div>
          );
        },
      },
      { key: "status", header: "Status", sortable: true, render: (a) => <StatusBadge status={a.status} /> },
      {
        key: "model",
        header: "Model",
        sortable: true,
        render: (a) => (
          <span className="inline-flex items-center gap-1 text-[12.5px] text-[#475569]">
            <Cpu size={12} className="text-[#94A3B8]" /> {a.model || "—"}
          </span>
        ),
      },
      { key: "conversations", header: "Conversations", sortable: true, accessor: (a) => a.conversations || 0, render: (a) => (a.conversations || 0).toLocaleString() },
      { key: "success_rate", header: "Success", sortable: true, accessor: (a) => a.success_rate || 0, render: (a) => `${a.success_rate || 0}%` },
      {
        key: "updated_at",
        header: "Updated",
        sortable: true,
        accessor: (a) => a.updated_at || "",
        render: (a) => (
          <span className="inline-flex items-center gap-1 text-[12.5px] text-[#64748B]">
            <Clock size={12} /> {fmtRelative(a.updated_at)}
          </span>
        ),
      },
    ],
    []
  );

  const statStrip =
    agents.length > 0 ? (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
        {stats.map((s) => (
          <StatCard
            key={s.key}
            icon={s.icon}
            label={s.label}
            value={Number(s.value).toLocaleString()}
            sub={s.sub}
            tone={s.color}
            bg={`${s.color}1A`}
          />
        ))}
      </div>
    ) : null;

  return (
    <>
      <EntityListPage
        eyebrow="Build"
        title="AI Agents"
        subtitle="Manage, customize, and monitor your AI agents."
        icon={Bot}
        loading={isLoading}
        rows={agents}
        columns={columns}
        rowKey={(a) => a.id}
        stats={statStrip}
        skeletonCols={6}
        search
        searchKeys={["name", "model"]}
        searchPlaceholder="Search agents…"
        filters={[
          { key: "type", label: "Type", options: [
            { value: "chat", label: "Chat" },
          ] },
          { key: "status", label: "Status", options: [
            { value: "draft", label: "Draft" },
            { value: "active", label: "Active" },
            { value: "paused", label: "Paused" },
            { value: "archived", label: "Archived" },
          ] },
        ]}
        onRowClick={(a) => setActive(a)}
        rowActions={(a) => (
          <>
            <MenuItem icon={ExternalLink} onClick={() => nav(`/app/agents/${a.id}`)}>
              Open
            </MenuItem>
            <MenuItem icon={Code2} onClick={() => nav(`/app/agents/${a.id}/deploy`)}>
              Channels &amp; Deploy
            </MenuItem>
            <MenuItem icon={Copy} onClick={() => duplicate(a)}>
              Duplicate
            </MenuItem>
            {a.status !== "archived" && (
              <MenuItem icon={a.status === "active" ? PauseCircle : Rocket} onClick={() => toggleStatus(a)}>
                {a.status === "active" ? "Pause" : "Activate"}
              </MenuItem>
            )}
            <MenuItem icon={Trash2} danger onClick={() => remove(a)}>
              Delete
            </MenuItem>
          </>
        )}
        bulkActions={(sel, clear) => (
          <>
            <GhostButton onClick={() => bulkStatus(sel, clear, "active")}>Activate</GhostButton>
            <GhostButton onClick={() => bulkStatus(sel, clear, "paused")}>Pause</GhostButton>
            <GhostButton onClick={() => bulkDelete(sel, clear)}>Delete</GhostButton>
          </>
        )}
        empty={{
          icon: Bot,
          title: "No agents yet",
          hint: "Create your first AI agent to start automating website chat conversations.",
          action: (
            <PrimaryButton as={Link} to="/app/agents/new" data-testid="agents-empty-create-btn">
              <Plus size={16} /> Create Agent
            </PrimaryButton>
          ),
        }}
      />

      <AgentDrawer
        agent={active}
        onClose={() => setActive(null)}
        onOpenFull={(a) => nav(`/app/agents/${a.id}`)}
        onGotoDeploy={(a) => nav(`/app/agents/${a.id}/deploy`)}
        onToggle={(a) => {
          toggleStatus(a);
          setActive(null);
        }}
        onDuplicate={(a) => {
          duplicate(a);
          setActive(null);
        }}
        onDelete={(a) => {
          remove(a);
          setActive(null);
        }}
      />
    </>
  );
}

/* ============================== Subcomponents ============================== */

function StatusBadge({ status }) {
  const meta = STATUS_META[status] || STATUS_META.draft;
  return (
    <span
      className={cx("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold", meta.badge)}
      data-testid={`agent-status-${status}`}
    >
      <span className="size-1.5 rounded-full" style={{ background: meta.dot }} />
      {meta.label}
    </span>
  );
}

function AgentDrawer({ agent, onClose, onOpenFull, onGotoDeploy, onToggle, onDuplicate, onDelete }) {
  const meta = agent ? TYPE_META[agent.type] || TYPE_META.chat : TYPE_META.chat;
  const isActive = agent?.status === "active";
  return (
    <Drawer
      open={!!agent}
      onClose={onClose}
      icon={meta.icon}
      title={agent?.name}
      description={meta.label}
      data-testid="agent-drawer"
      footer={
        agent && (
          <>
            <GhostButton onClick={() => onOpenFull(agent)}>
              <ExternalLink size={15} /> Open full editor
            </GhostButton>
            {isActive && (
              <GhostButton onClick={() => onGotoDeploy(agent)}>
                <Code2 size={15} /> Channels &amp; Deploy
              </GhostButton>
            )}
            {agent.status !== "archived" && (
              <PrimaryButton onClick={() => onToggle(agent)}>
                {isActive ? (
                  <>
                    <PauseCircle size={15} /> Pause
                  </>
                ) : (
                  <>
                    <Rocket size={15} /> Activate
                  </>
                )}
              </PrimaryButton>
            )}
          </>
        )
      }
    >
      {agent && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={agent.status} />
            <span className="inline-flex items-center gap-1 rounded-full bg-[#EFF6FF] px-2 py-0.5 text-[11px] font-semibold text-[#1D4ED8]">
              <Cpu size={11} /> {agent.model || "no model"}
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-[#F1F5F9] px-2 py-0.5 text-[11px] text-[#64748B]">
              <Clock size={11} /> {fmtRelative(agent.updated_at)}
            </span>
          </div>

          {agent.is_ready === false && agent.status !== "archived" && (
            <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[12.5px] text-amber-800">
              <AlertTriangle size={15} className="mt-0.5 shrink-0" />
              <span>Incomplete — add a system prompt before deploying.</span>
            </div>
          )}

          <p className="text-[13.5px] text-[#475569]">{agent.description || meta.desc}</p>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-[#EAF0F6] bg-[#FBFCFE] p-4">
              <p className="text-[12px] text-[#64748B]">Conversations</p>
              <p className="mt-1 text-[20px] font-bold text-[#0F172A]">{(agent.conversations || 0).toLocaleString()}</p>
            </div>
            <div className="rounded-xl border border-[#EAF0F6] bg-[#FBFCFE] p-4">
              <p className="text-[12px] text-[#64748B]">Success rate</p>
              <p className="mt-1 text-[20px] font-bold text-[#0F172A]">{agent.success_rate || 0}%</p>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <GhostButton onClick={() => onDuplicate(agent)}>
              <Copy size={15} /> Duplicate
            </GhostButton>
            <button
              onClick={() => onDelete(agent)}
              className="inline-flex items-center gap-2 rounded-full border border-[#FEE4E2] bg-white px-4 py-2 text-sm font-semibold text-[#B42318] transition-colors hover:bg-[#FEF3F2]"
            >
              <Trash2 size={15} /> Delete
            </button>
          </div>
        </div>
      )}
    </Drawer>
  );
}
