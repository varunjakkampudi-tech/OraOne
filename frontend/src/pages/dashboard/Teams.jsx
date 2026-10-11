import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Users2,
  Plus,
  Loader2,
  Trash2,
  X,
  UserPlus,
  Crown,
  Pencil,
  ChevronRight,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { usePermissions } from "@/hooks/usePermissions";

const ROLE_STYLES = {
  lead: "bg-[#FEF3C7] text-[#B45309]",
  editor: "bg-[#EEF2FF] text-[#4F46E5]",
  contributor: "bg-[#ECFEFF] text-[#0891B2]",
  viewer: "bg-[#F1F5F9] text-[#475569]",
};

const TEAM_COLORS = ["#6366F1", "#0891B2", "#16A34A", "#B45309", "#A21CAF", "#DC2626"];

function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

function RoleBadge({ role }) {
  const cls = ROLE_STYLES[role] || ROLE_STYLES.viewer;
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-semibold capitalize ${cls}`}>
      {role === "lead" && <Crown className="h-3 w-3" />}
      {role}
    </span>
  );
}

function CreateTeamModal({ onClose, onCreated }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState(TEAM_COLORS[0]);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!name.trim()) {
      toast.error("Enter a team name.");
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post("/teams", {
        name: name.trim(),
        description: description.trim() || null,
        color,
      });
      toast.success("Team created");
      onCreated(data);
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
          <h2 className="text-lg font-bold text-[#0F172A]">New team</h2>
          <button onClick={onClose} className="rounded-lg p-1 text-[#94A3B8] hover:bg-[#F1F5F9]">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-5 space-y-4">
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Engineering"
              className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
          <div>
            <label className="mb-1 block text-[12px] font-semibold text-[#334155]">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="What does this team work on?"
              className="w-full resize-none rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-[12px] font-semibold text-[#334155]">Color</label>
            <div className="flex gap-2">
              {TEAM_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`h-7 w-7 rounded-full ring-2 ring-offset-2 transition ${
                    color === c ? "ring-[#0F172A]" : "ring-transparent"
                  }`}
                  style={{ backgroundColor: c }}
                  aria-label={`Color ${c}`}
                />
              ))}
            </div>
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
            Create team
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function TeamDetailDrawer({ teamId, members, canManage, onClose, onChanged }) {
  const [team, setTeam] = useState(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [pickUser, setPickUser] = useState("");
  const [pickRole, setPickRole] = useState("contributor");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/teams/${teamId}`);
      setTeam(data);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    load();
  }, [load]);

  const memberUserIds = useMemo(
    () => new Set((team?.members || []).map((m) => m.user_id)),
    [team]
  );
  const candidates = useMemo(
    () => members.filter((m) => !memberUserIds.has(m.user_id)),
    [members, memberUserIds]
  );

  const addMember = async () => {
    if (!pickUser) {
      toast.error("Pick a member to add.");
      return;
    }
    setBusy(true);
    try {
      await api.post(`/teams/${teamId}/members`, { user_id: pickUser, role: pickRole });
      toast.success("Member added");
      setAdding(false);
      setPickUser("");
      setPickRole("contributor");
      await load();
      onChanged?.();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  const removeMember = async (memberId) => {
    if (!window.confirm("Remove this member from the team?")) return;
    setBusy(true);
    try {
      await api.delete(`/teams/${teamId}/members/${memberId}`);
      toast.success("Member removed");
      await load();
      onChanged?.();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40">
      <motion.div
        initial={{ x: 40, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        className="flex h-full w-full max-w-md flex-col bg-white shadow-xl"
      >
        <div className="flex items-center justify-between border-b border-[#E2E8F0] px-5 py-4">
          <div className="flex items-center gap-3">
            <div
              className="grid h-9 w-9 place-items-center rounded-xl text-white"
              style={{ backgroundColor: team?.color || "#6366F1" }}
            >
              <Users2 className="h-4.5 w-4.5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#0F172A]">{team?.name || "Team"}</h2>
              <p className="text-[12px] text-[#94A3B8]">{team?.members?.length || 0} members</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-[#94A3B8] hover:bg-[#F1F5F9]">
            <X className="h-5 w-5" />
          </button>
        </div>

        {loading ? (
          <div className="grid flex-1 place-items-center">
            <Loader2 className="h-5 w-5 animate-spin text-[#4F46E5]" />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-5">
            {team?.description && (
              <p className="mb-4 rounded-xl bg-[#F8FAFC] px-3 py-2.5 text-sm text-[#475569]">{team.description}</p>
            )}

            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-[12px] font-bold uppercase tracking-wide text-[#94A3B8]">Members</h3>
              {canManage && !adding && (
                <button
                  onClick={() => setAdding(true)}
                  className="inline-flex items-center gap-1 text-[12px] font-semibold text-[#4F46E5] hover:underline"
                >
                  <UserPlus className="h-3.5 w-3.5" /> Add
                </button>
              )}
            </div>

            {adding && (
              <div className="mb-4 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <select
                  value={pickUser}
                  onChange={(e) => setPickUser(e.target.value)}
                  className="mb-2 w-full rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
                >
                  <option value="">Select a member…</option>
                  {candidates.map((m) => (
                    <option key={m.user_id} value={m.user_id}>
                      {m.name} ({m.email})
                    </option>
                  ))}
                </select>
                <div className="flex gap-2">
                  <select
                    value={pickRole}
                    onChange={(e) => setPickRole(e.target.value)}
                    className="flex-1 rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
                  >
                    <option value="lead">Lead</option>
                    <option value="editor">Editor</option>
                    <option value="contributor">Contributor</option>
                    <option value="viewer">Viewer</option>
                  </select>
                  <button
                    onClick={addMember}
                    disabled={busy}
                    className="rounded-lg bg-[#4F46E5] px-3 py-2 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60"
                  >
                    Add
                  </button>
                  <button
                    onClick={() => setAdding(false)}
                    className="rounded-lg px-2 py-2 text-sm text-[#475569] hover:bg-[#F1F5F9]"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            )}

            <ul className="space-y-2">
              {(team?.members || []).map((m) => (
                <li
                  key={m.id}
                  className="flex items-center gap-3 rounded-xl border border-[#E2E8F0] px-3 py-2.5"
                >
                  <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#EEF2FF] text-[11px] font-bold text-[#4F46E5]">
                    {initials(m.user?.name) || "•"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-[#0F172A]">{m.user?.name || "Member"}</p>
                    <p className="truncate text-[11px] text-[#94A3B8]">{m.user?.email}</p>
                  </div>
                  <RoleBadge role={m.role} />
                  {canManage && (
                    <button
                      onClick={() => removeMember(m.id)}
                      disabled={busy}
                      className="rounded-lg p-1.5 text-[#94A3B8] hover:bg-[#FEE2E2] hover:text-[#DC2626] disabled:opacity-50"
                      aria-label="Remove member"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </motion.div>
    </div>
  );
}

export default function Teams() {
  const { can } = usePermissions();
  const canManage = can("team.manage");
  const [teams, setTeams] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [openTeam, setOpenTeam] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, m] = await Promise.all([api.get("/teams"), api.get("/collab/members")]);
      setTeams(Array.isArray(t.data) ? t.data : t.data?.teams || []);
      setMembers(Array.isArray(m.data?.members) ? m.data.members : []);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const remove = async (team) => {
    if (!window.confirm(`Delete team "${team.name}"? This cannot be undone.`)) return;
    setBusyId(team.id);
    try {
      await api.delete(`/teams/${team.id}`);
      toast.success("Team deleted");
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyId(null);
    }
  };

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
      className="mx-auto max-w-5xl space-y-8 p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#EEF2FF] text-[#4F46E5]">
            <Users2 className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#0F172A]">Teams</h1>
            <p className="text-sm text-[#64748B]">
              Group members into departments and share resources with the whole team at once.
            </p>
          </div>
        </div>
        {canManage && (
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]"
          >
            <Plus className="h-4 w-4" /> New team
          </button>
        )}
      </div>

      {teams.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#CBD5E1] bg-white py-16 text-center">
          <Users2 className="mx-auto h-8 w-8 text-[#CBD5E1]" />
          <p className="mt-3 text-sm font-medium text-[#475569]">No teams yet</p>
          <p className="text-[13px] text-[#94A3B8]">Create your first team to start collaborating.</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((team) => (
            <div
              key={team.id}
              className="group relative rounded-2xl border border-[#E2E8F0] bg-white p-4 transition hover:border-[#C7D2FE] hover:shadow-sm"
            >
              <button onClick={() => setOpenTeam(team.id)} className="block w-full text-left">
                <div className="flex items-center gap-3">
                  <div
                    className="grid h-10 w-10 place-items-center rounded-xl text-white"
                    style={{ backgroundColor: team.color || "#6366F1" }}
                  >
                    <Users2 className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-bold text-[#0F172A]">{team.name}</p>
                    <p className="text-[12px] text-[#94A3B8]">{team.member_count ?? team.members?.length ?? 0} members</p>
                  </div>
                </div>
                {team.description && (
                  <p className="mt-3 line-clamp-2 text-[13px] text-[#64748B]">{team.description}</p>
                )}
              </button>
              <div className="mt-3 flex items-center justify-between">
                <button
                  onClick={() => setOpenTeam(team.id)}
                  className="inline-flex items-center gap-1 text-[12px] font-semibold text-[#4F46E5] hover:underline"
                >
                  Manage <ChevronRight className="h-3.5 w-3.5" />
                </button>
                {canManage && (
                  <button
                    onClick={() => remove(team)}
                    disabled={busyId === team.id}
                    className="rounded-lg p-1.5 text-[#94A3B8] opacity-0 transition group-hover:opacity-100 hover:bg-[#FEE2E2] hover:text-[#DC2626] disabled:opacity-50"
                    aria-label="Delete team"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <CreateTeamModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
        />
      )}
      {openTeam && (
        <TeamDetailDrawer
          teamId={openTeam}
          members={members}
          canManage={canManage}
          onClose={() => setOpenTeam(null)}
          onChanged={load}
        />
      )}
    </motion.div>
  );
}
