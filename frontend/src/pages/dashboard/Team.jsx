import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  UserPlus,
  Search,
  Users,
  ShieldCheck,
  UserCog,
  Eye,
  Crown,
  Check,
  X,
  Clock,
  Activity,
  Send,
  Lock,
  CheckCircle2,
  Trash2,
  Mail,
  Copy,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { usePermissions } from "@/hooks/usePermissions";

/* ── Role display config (keyed by backend role values) ── */
const ROLE_META = {
  owner: { label: "Owner", cls: "bg-amber-50 text-amber-700 border-amber-200", icon: Crown },
  admin: { label: "Admin", cls: "bg-blue-50 text-blue-700 border-blue-200", icon: ShieldCheck },
  member: { label: "Member", cls: "bg-purple-50 text-purple-700 border-purple-200", icon: UserCog },
  viewer: { label: "Viewer", cls: "bg-slate-100 text-slate-700 border-slate-200", icon: Eye },
};
const ASSIGNABLE = ["admin", "member", "viewer"];

const AVATAR_COLORS = ["#2563EB", "#7C3AED", "#16A34A", "#DC2626", "#EA580C", "#0891B2"];

function initialsOf(name, email) {
  const base = (name || email || "?").trim();
  const parts = base.split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return base.slice(0, 2).toUpperCase();
}

function colorFor(id) {
  let h = 0;
  for (const c of String(id)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

function timeAgo(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return d.toLocaleDateString();
}

export default function Team() {
  const { can } = usePermissions();
  const canManage = can("team.manage");

  const [members, setMembers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const [m, i, x] = await Promise.allSettled([
      api.get("/team/members"),
      api.get("/team/invitations"),
      api.get("/rbac/matrix"),
    ]);
    if (m.status === "fulfilled") setMembers(m.value.data.items || []);
    if (i.status === "fulfilled") setInvitations(i.value.data.items || []);
    if (x.status === "fulfilled") setMatrix(x.value.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return members;
    return members.filter(
      (m) =>
        (m.full_name || "").toLowerCase().includes(s) ||
        (m.email || "").toLowerCase().includes(s)
    );
  }, [q, members]);

  const pendingInvites = invitations.filter((i) => i.status === "pending");
  const stats = [
    { key: "total", label: "Total Members", value: members.length, icon: Users, tone: "#2563EB", bg: "#EFF6FF" },
    { key: "active", label: "Active Members", value: members.filter((m) => m.status === "active").length, icon: Activity, tone: "#16A34A", bg: "#DCFCE7" },
    { key: "pending", label: "Pending Invitations", value: pendingInvites.length, icon: Clock, tone: "#F59E0B", bg: "#FEF3C7" },
    { key: "admins", label: "Owners & Admins", value: members.filter((m) => m.role === "owner" || m.role === "admin").length, icon: ShieldCheck, tone: "#7C3AED", bg: "#EDE9FE" },
  ];

  const sendInvite = async () => {
    if (!inviteEmail.trim()) {
      toast.error("Enter an email address.");
      return;
    }
    setSending(true);
    try {
      const { data } = await api.post("/team/invitations", {
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      const url = data.invitation?.invite_url;
      if (url) {
        try {
          await navigator.clipboard.writeText(url);
          toast.success("Invitation created — link copied to clipboard.");
        } catch {
          toast.success("Invitation created.");
        }
      }
      setShowInvite(false);
      setInviteEmail("");
      setInviteRole("member");
      await load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSending(false);
    }
  };

  const changeRole = async (member, role) => {
    try {
      await api.patch(`/team/members/${member.id}`, { role });
      toast.success(`${member.full_name || member.email} is now ${ROLE_META[role]?.label || role}.`);
      await load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const removeMember = async (member) => {
    if (!window.confirm(`Remove ${member.full_name || member.email} from the team?`)) return;
    try {
      await api.delete(`/team/members/${member.id}`);
      toast.success("Member removed.");
      await load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const revokeInvite = async (inv) => {
    try {
      await api.delete(`/team/invitations/${inv.id}`);
      toast.success("Invitation revoked.");
      await load();
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const copyInvite = async (inv) => {
    if (!inv.invite_url) return;
    try {
      await navigator.clipboard.writeText(inv.invite_url);
      toast.success("Invite link copied.");
    } catch {
      toast.error("Could not copy link.");
    }
  };

  return (
    <div className="space-y-8" data-testid="team-page">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[12px] font-semibold tracking-[0.18em] text-[#2563EB] uppercase">
            Team &amp; Permissions
          </p>
          <h1 className="mt-1 text-2xl sm:text-3xl font-black text-[#0F172A]">
            Manage who can do what.
          </h1>
          <p className="mt-1 text-sm text-[#64748B]">
            Role-based access control, invitations and member management.
          </p>
        </div>
        {canManage && (
          <button
            onClick={() => setShowInvite(true)}
            data-testid="invite-cta"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_8px_20px_-6px_rgba(37,99,235,0.5)] transition-colors"
          >
            <UserPlus size={15} /> Invite Member
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="team-stats">
        {stats.map((s, i) => (
          <motion.div
            key={s.key}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className="p-5 rounded-2xl border border-[#E2E8F0] bg-white hover:shadow-premium transition-all"
            data-testid={`team-stat-${s.key}`}
          >
            <div className="flex items-center justify-between">
              <span className="size-10 rounded-xl grid place-items-center" style={{ background: s.bg }}>
                <s.icon size={17} style={{ color: s.tone }} />
              </span>
            </div>
            <p className="mt-3 text-3xl font-black text-[#0F172A] tabular-nums">{s.value}</p>
            <p className="text-[12.5px] text-[#0F172A] font-semibold mt-1">{s.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Members table */}
      <Section title="Team Members" subtitle="Everyone with access to your workspace" icon={Users}>
        <div className="rounded-2xl border border-[#E2E8F0] bg-white overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-2 px-5 py-3.5 border-b border-[#E2E8F0] bg-[#F8FAFC]">
            <div className="relative max-w-xs w-full">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
              <input
                type="text"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search by name or email…"
                data-testid="team-search"
                className="w-full pl-8 pr-3 py-2 rounded-lg border border-[#E2E8F0] bg-white text-sm placeholder:text-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10"
              />
            </div>
            <p className="text-[11.5px] text-[#64748B]">
              {filtered.length} of {members.length} members
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b border-[#E2E8F0]">
                <tr>
                  <Th>Member</Th>
                  <Th>Role</Th>
                  <Th>Status</Th>
                  <Th>Joined</Th>
                  <Th />
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0]">
                {loading && (
                  <tr>
                    <td colSpan={5} className="px-5 py-10 text-center">
                      <Loader2 className="w-5 h-5 animate-spin text-[#2563EB] inline" />
                    </td>
                  </tr>
                )}
                {!loading && filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-5 py-10 text-center text-[13px] text-[#64748B]">
                      No members match your search.
                    </td>
                  </tr>
                )}
                {!loading &&
                  filtered.map((m) => {
                    const meta = ROLE_META[m.role] || ROLE_META.viewer;
                    const RoleIcon = meta.icon;
                    const editable = canManage && m.role !== "owner" && !m.is_you;
                    return (
                      <tr key={m.id} className="hover:bg-[#F8FAFC] transition-colors" data-testid={`member-${m.id}`}>
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <span
                              className="size-9 rounded-full grid place-items-center text-white text-[12px] font-bold"
                              style={{ background: colorFor(m.user_id) }}
                            >
                              {initialsOf(m.full_name, m.email)}
                            </span>
                            <div className="min-w-0">
                              <p className="text-[13.5px] font-semibold text-[#0F172A] flex items-center gap-2">
                                {m.full_name || m.email.split("@")[0]}
                                {m.is_you && (
                                  <span className="text-[10px] font-bold text-[#2563EB] bg-[#EFF6FF] px-1.5 py-0.5 rounded-full">
                                    YOU
                                  </span>
                                )}
                              </p>
                              <p className="text-[12px] text-[#64748B]">{m.email}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          {editable ? (
                            <select
                              value={m.role}
                              onChange={(e) => changeRole(m, e.target.value)}
                              data-testid={`member-role-${m.id}`}
                              className="px-2 py-1 rounded-lg border border-[#E2E8F0] text-[12.5px] font-semibold text-[#0F172A] focus:border-[#2563EB] focus:outline-none"
                            >
                              {ASSIGNABLE.map((r) => (
                                <option key={r} value={r}>
                                  {ROLE_META[r].label}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[11.5px] font-semibold ${meta.cls}`}>
                              <RoleIcon size={11} />
                              {meta.label}
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-4">
                          <span className="inline-flex items-center gap-1.5 text-[12.5px] capitalize">
                            <span className={`size-1.5 rounded-full ${m.status === "active" ? "bg-[#16A34A]" : "bg-[#94A3B8]"}`} />
                            {m.status}
                          </span>
                        </td>
                        <td className="px-5 py-4 text-[12.5px] text-[#64748B]">{timeAgo(m.joined_at)}</td>
                        <td className="px-5 py-4 text-right">
                          {editable && (
                            <button
                              onClick={() => removeMember(m)}
                              data-testid={`member-remove-${m.id}`}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11.5px] font-semibold text-[#DC2626] hover:bg-[#FEE2E2]"
                            >
                              <Trash2 size={12} /> Remove
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* Invitations */}
      <Section title="Invitations" subtitle="Share invite links to add teammates" icon={Mail}>
        <div className="rounded-2xl border border-[#E2E8F0] bg-white overflow-x-auto" data-testid="invitations">
          <table className="w-full">
            <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0]">
              <tr>
                <Th>Email</Th>
                <Th>Role</Th>
                <Th>Invited By</Th>
                <Th>Sent</Th>
                <Th>Status</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0]">
              {invitations.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-[13px] text-[#64748B]">
                    No invitations yet.
                  </td>
                </tr>
              )}
              {invitations.map((i) => {
                const meta = ROLE_META[i.role] || ROLE_META.viewer;
                return (
                  <tr key={i.id} className="hover:bg-[#F8FAFC] transition-colors" data-testid={`invite-${i.id}`}>
                    <td className="px-5 py-3.5 text-[13px] font-semibold text-[#0F172A]">{i.email}</td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11.5px] font-semibold ${meta.cls}`}>
                        {meta.label}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-[12.5px] text-[#64748B]">{i.invited_by || "—"}</td>
                    <td className="px-5 py-3.5 text-[12.5px] text-[#64748B]">{timeAgo(i.created_at)}</td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={i.status} />
                    </td>
                    <td className="px-5 py-3.5">
                      {i.status === "pending" ? (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => copyInvite(i)}
                            data-testid={`invite-copy-${i.id}`}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11.5px] font-semibold text-[#2563EB] hover:bg-[#EFF6FF]"
                          >
                            <Copy size={11} /> Copy link
                          </button>
                          {canManage && (
                            <button
                              onClick={() => revokeInvite(i)}
                              data-testid={`invite-revoke-${i.id}`}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11.5px] font-semibold text-[#DC2626] hover:bg-[#FEE2E2]"
                            >
                              <Trash2 size={11} /> Revoke
                            </button>
                          )}
                        </div>
                      ) : (
                        <span className="text-[11.5px] text-[#94A3B8]">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Section>

      {/* Permission Matrix (live from RBAC) */}
      <Section title="Permission Matrix" subtitle="What each role can do across OraOne" icon={Lock}>
        <div className="rounded-2xl border border-[#E2E8F0] bg-white overflow-x-auto" data-testid="permission-matrix">
          {matrix ? (
            <table className="w-full">
              <thead className="bg-[#F8FAFC] border-b border-[#E2E8F0]">
                <tr>
                  <Th>Permission</Th>
                  {Object.keys(matrix.roles).map((r) => {
                    const meta = ROLE_META[r] || { label: r, icon: Eye };
                    const I = meta.icon;
                    return (
                      <th key={r} className="px-5 py-3 text-center text-[11px] font-bold tracking-wider text-[#64748B] uppercase">
                        <span className="inline-flex items-center gap-1.5 justify-center">
                          <I size={12} />
                          {meta.label}
                        </span>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0]">
                {matrix.permissions.map((perm) => (
                  <tr key={perm}>
                    <td className="px-5 py-3 text-[13px] font-mono text-[#0F172A]">{perm}</td>
                    {Object.keys(matrix.roles).map((r) => (
                      <td key={r} className="px-5 py-3 text-center">
                        <PermCell on={matrix.roles[r].includes(perm)} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-5 py-8 text-center text-[13px] text-[#64748B]">Loading permissions…</div>
          )}
        </div>
      </Section>

      {/* Invite modal */}
      <AnimatePresence>
        {showInvite && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-[#0F172A]/50 backdrop-blur-sm grid place-items-center px-4"
            onClick={() => setShowInvite(false)}
            data-testid="invite-modal"
          >
            <motion.div
              initial={{ y: 16, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 16, opacity: 0 }}
              className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="px-6 py-5 border-b border-[#E2E8F0] flex items-center justify-between">
                <h3 className="text-lg font-bold text-[#0F172A]">Invite a teammate</h3>
                <button onClick={() => setShowInvite(false)} className="text-[#94A3B8] hover:text-[#0F172A]">
                  <X size={18} />
                </button>
              </div>
              <div className="px-6 py-5 space-y-4">
                <div>
                  <label className="text-[12px] font-semibold text-[#0F172A]">Email</label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="teammate@company.com"
                    data-testid="invite-input-email"
                    className="mt-1 w-full px-3 py-2.5 rounded-lg border border-[#E2E8F0] text-sm focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10"
                  />
                </div>
                <div>
                  <label className="text-[12px] font-semibold text-[#0F172A]">Role</label>
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    {ASSIGNABLE.map((r) => {
                      const meta = ROLE_META[r];
                      const I = meta.icon;
                      const active = inviteRole === r;
                      return (
                        <button
                          key={r}
                          onClick={() => setInviteRole(r)}
                          data-testid={`invite-role-${r}`}
                          className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border text-[13px] font-semibold transition-colors justify-center ${
                            active
                              ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]"
                              : "border-[#E2E8F0] text-[#475569] hover:border-[#2563EB]"
                          }`}
                        >
                          <I size={13} /> {meta.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <p className="text-[12px] text-[#64748B] flex items-start gap-1.5">
                  <Mail size={13} className="mt-0.5 flex-shrink-0" />
                  We'll generate a secure invite link — copy and share it with your teammate to let them join.
                </p>
              </div>
              <div className="px-6 py-4 bg-[#F8FAFC] border-t border-[#E2E8F0] flex justify-end gap-2">
                <button
                  onClick={() => setShowInvite(false)}
                  className="px-4 py-2 rounded-lg text-sm font-semibold text-[#475569] hover:bg-[#E2E8F0]"
                >
                  Cancel
                </button>
                <button
                  onClick={sendInvite}
                  disabled={sending}
                  data-testid="invite-submit"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-60 text-white text-sm font-semibold"
                >
                  {sending ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                  Create Invite
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Helpers ── */
function StatusBadge({ status }) {
  const map = {
    pending: { cls: "text-[#92400E] bg-[#FEF3C7]", icon: Clock, label: "Pending" },
    accepted: { cls: "text-[#15803D] bg-[#DCFCE7]", icon: CheckCircle2, label: "Accepted" },
    revoked: { cls: "text-[#94A3B8] bg-[#F1F5F9]", icon: X, label: "Revoked" },
    expired: { cls: "text-[#94A3B8] bg-[#F1F5F9]", icon: Clock, label: "Expired" },
  };
  const m = map[status] || map.pending;
  const I = m.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-[12px] font-semibold px-2 py-0.5 rounded-full ${m.cls}`}>
      <I size={11} /> {m.label}
    </span>
  );
}

function PermCell({ on }) {
  if (on) {
    return (
      <span className="inline-flex size-6 rounded-full bg-[#DCFCE7] items-center justify-center">
        <Check size={13} className="text-[#15803D]" strokeWidth={3} />
      </span>
    );
  }
  return (
    <span className="inline-flex size-6 rounded-full bg-[#F1F5F9] items-center justify-center">
      <X size={13} className="text-[#94A3B8]" strokeWidth={3} />
    </span>
  );
}

function Section({ title, subtitle, icon: Icon, children }) {
  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <span className="size-7 rounded-lg bg-[#EFF6FF] grid place-items-center">
          <Icon size={14} className="text-[#2563EB]" />
        </span>
        <div>
          <h2 className="text-[15px] font-bold text-[#0F172A]">{title}</h2>
          {subtitle && <p className="text-[11.5px] text-[#64748B]">{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function Th({ children }) {
  return (
    <th className="px-5 py-3 text-left text-[11px] font-bold tracking-wider text-[#64748B] uppercase whitespace-nowrap">
      {children}
    </th>
  );
}
