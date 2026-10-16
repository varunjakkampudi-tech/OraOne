import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/client";
import {
  TEAM_ROLES,
  changeMemberRole,
  createInvitation,
  listInvitations,
  listMembers,
  removeMember,
  revokeInvitation,
  type Invitation,
  type TeamMember,
  type TeamRole,
} from "@/lib/api/team";
import { Loading, Notice } from "./studio-ui";
import { when } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";

// Live team screen under /studio. Members and invitations belong to the
// organization. Role changes and removals are enforced by the API; a refused
// change is shown as the API's own message.

export function TeamPage() {
  const [members, setMembers] = useState<TeamMember[] | null>(null);
  const [invites, setInvites] = useState<Invitation[] | null>(null);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<TeamRole>("member");
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState("");
  const [created, setCreated] = useState<Invitation | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError("");
    Promise.all([listMembers(), listInvitations()])
      .then(([m, i]) => {
        if (cancelled) return;
        setMembers(m.items);
        setInvites(i.items);
      })
      .catch((err) => {
        if (!cancelled) setError(messageOf(err, "Couldn't load your team."));
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  async function sendInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setInviting(true);
    setInviteError("");
    setCreated(null);
    try {
      const res = await createInvitation({ email: email.trim(), role });
      setCreated(res.invitation);
      setEmail("");
      setReloadKey((k) => k + 1);
    } catch (err) {
      setInviteError(messageOf(err, "Couldn't send this invitation."));
    } finally {
      setInviting(false);
    }
  }

  async function changeRole(member: TeamMember, next: TeamRole) {
    setBusyId(member.id);
    setError("");
    try {
      await changeMemberRole(member.id, next);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(messageOf(err, "Couldn't change this role."));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(member: TeamMember) {
    setBusyId(member.id);
    setError("");
    try {
      await removeMember(member.id);
      setConfirmId(null);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(messageOf(err, "Couldn't remove this member."));
    } finally {
      setBusyId(null);
    }
  }

  async function revoke(invite: Invitation) {
    setBusyId(invite.id);
    setError("");
    try {
      await revokeInvitation(invite.id);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(messageOf(err, "Couldn't revoke this invitation."));
    } finally {
      setBusyId(null);
    }
  }

  const pending = invites?.filter((i) => i.status === "pending") ?? [];

  return (
    <StudioFrame>
      <span className="marketing-eyebrow">LIVE · TEAM</span>
      <h1 className="mt-2 text-3xl font-semibold">Team</h1>
      <p className="mt-2 text-muted-foreground">
        People in your organization and the invitations waiting for a response.
      </p>
      {error && (
        <div className="mt-4">
          <Notice kind="error">{error}</Notice>
        </div>
      )}

      <section className="mt-8" aria-labelledby="invite-heading">
        <h2 id="invite-heading" className="text-xl font-semibold">
          Invite a teammate
        </h2>
        <form onSubmit={sendInvite} className="mt-3 flex max-w-2xl flex-wrap items-end gap-3">
          <label className="grid min-w-0 flex-1 gap-1 text-sm">
            Email address
            <input
              type="email"
              required
              placeholder="teammate@company.com"
              className="rounded-md border border-input bg-background px-3 py-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="grid gap-1 text-sm">
            Role
            <select
              className="rounded-md border border-input bg-background px-3 py-2"
              value={role}
              onChange={(e) => setRole(e.target.value as TeamRole)}
            >
              {TEAM_ROLES.filter((r) => r !== "owner").map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <Button type="submit" disabled={inviting || !email.trim()}>
            {inviting ? "Sending…" : "Send invitation"}
          </Button>
        </form>
        {inviteError && (
          <div className="mt-3 max-w-2xl">
            <Notice kind="error">{inviteError}</Notice>
          </div>
        )}
        {created && (
          <div className="mt-3 max-w-2xl" role="status">
            <Notice>
              Invitation created for {created.email}.
              {created.invite_url ? (
                <>
                  {" "}
                  Share this link: <code className="break-all">{created.invite_url}</code>
                </>
              ) : null}
            </Notice>
          </div>
        )}
      </section>

      <section className="mt-10" aria-labelledby="members-heading">
        <h2 id="members-heading" className="text-xl font-semibold">
          Members
        </h2>
        <div className="mt-3">
          {members === null && !error ? (
            <Loading label="Loading members…" />
          ) : members && members.length === 0 ? (
            <p className="text-muted-foreground">No members yet.</p>
          ) : members ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Member</th>
                    <th className="py-2 pr-4 font-medium">Role</th>
                    <th className="hidden py-2 pr-4 font-medium md:table-cell">Joined</th>
                    <th className="hidden py-2 pr-4 font-medium md:table-cell">Last sign-in</th>
                    <th className="py-2 font-medium">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {members.map((m) => (
                    <tr key={m.id} className="border-b border-border">
                      <td className="py-2 pr-4">
                        <span className="font-medium">{m.full_name || m.email}</span>
                        {m.full_name && (
                          <span className="block text-sm text-muted-foreground">{m.email}</span>
                        )}
                        {m.is_you && <span className="text-sm text-muted-foreground"> (you)</span>}
                      </td>
                      <td className="py-2 pr-4">
                        <label className="sr-only" htmlFor={`role-${m.id}`}>
                          Role for {m.email}
                        </label>
                        <select
                          id={`role-${m.id}`}
                          className="rounded-md border border-input bg-background px-2 py-1"
                          value={m.role}
                          disabled={busyId === m.id}
                          onChange={(e) => changeRole(m, e.target.value as TeamRole)}
                        >
                          {TEAM_ROLES.map((r) => (
                            <option key={r} value={r}>
                              {r}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="hidden py-2 pr-4 md:table-cell">{when(m.joined_at)}</td>
                      <td className="hidden py-2 pr-4 md:table-cell">{when(m.last_login_at)}</td>
                      <td className="py-2 text-right">
                        {!m.is_you &&
                          (confirmId === m.id ? (
                            <span className="inline-flex gap-2">
                              <Button
                                variant="destructive"
                                size="sm"
                                disabled={busyId === m.id}
                                onClick={() => remove(m)}
                              >
                                Confirm remove
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setConfirmId(null)}
                              >
                                Cancel
                              </Button>
                            </span>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              aria-label={`Remove ${m.email}`}
                              onClick={() => setConfirmId(m.id)}
                            >
                              Remove
                            </Button>
                          ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </section>

      <section className="mt-10" aria-labelledby="pending-heading">
        <h2 id="pending-heading" className="text-xl font-semibold">
          Pending invitations
        </h2>
        <div className="mt-3">
          {invites === null && !error ? (
            <Loading label="Loading invitations…" />
          ) : pending.length === 0 ? (
            <p className="text-muted-foreground">No pending invitations.</p>
          ) : (
            <ul className="grid gap-2" aria-label="Pending invitations">
              {pending.map((inv) => (
                <li
                  key={inv.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3"
                >
                  <span>
                    <span className="font-medium">{inv.email}</span>{" "}
                    <span className="text-sm text-muted-foreground">
                      · {inv.role} · expires {when(inv.expires_at)}
                    </span>
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyId === inv.id}
                    onClick={() => revoke(inv)}
                  >
                    Revoke
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </StudioFrame>
  );
}
