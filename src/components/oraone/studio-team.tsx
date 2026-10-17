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
import { EmptyState, ErrorNotice, ListSkeleton, Notice, PageHeader } from "./studio-ui";
import { when } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";

// Live team screen under /studio. Members and invitations belong to the
// organization. Role changes and removals are enforced by the API; a refused
// change is shown as the API's own message.

const ROLE_NAME: Record<TeamRole, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
  viewer: "Viewer",
};

// Known roles get a plain name; anything the API adds later is shown as sent.
const roleName = (role: string) => (ROLE_NAME as Record<string, string>)[role] ?? role;

// Only one change can be awaiting confirmation at a time.
type PendingChange = { kind: "role"; id: string; role: TeamRole } | { kind: "remove"; id: string };

export function TeamPage() {
  const [members, setMembers] = useState<TeamMember[] | null>(null);
  const [invites, setInvites] = useState<Invitation[] | null>(null);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingChange | null>(null);

  const [email, setEmail] = useState("");
  const [role, setRole] = useState<TeamRole>("member");
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState("");
  const [created, setCreated] = useState<Invitation | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadError("");
    Promise.all([listMembers(), listInvitations()])
      .then(([m, i]) => {
        if (cancelled) return;
        setMembers(m.items);
        setInvites(i.items);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(messageOf(err, "Couldn't load your team."));
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
    setActionError("");
    try {
      await changeMemberRole(member.id, next);
      setPending(null);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setActionError(messageOf(err, "Couldn't change this role. It was not changed."));
    } finally {
      setBusyId(null);
    }
  }

  async function remove(member: TeamMember) {
    setBusyId(member.id);
    setActionError("");
    try {
      await removeMember(member.id);
      setPending(null);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setActionError(messageOf(err, "Couldn't remove this member. They are still in your team."));
    } finally {
      setBusyId(null);
    }
  }

  async function cancelInvite(invite: Invitation) {
    setBusyId(invite.id);
    setActionError("");
    try {
      await revokeInvitation(invite.id);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setActionError(messageOf(err, "Couldn't cancel this invitation."));
    } finally {
      setBusyId(null);
    }
  }

  const pendingInvites = invites?.filter((i) => i.status === "pending") ?? [];
  const live = members !== null && loadError === "";

  return (
    <StudioFrame>
      <PageHeader
        title="Team"
        description="People in your organization and the invitations waiting for a response."
        live={live}
      />
      {loadError && (
        <div className="mt-4">
          <ErrorNotice
            message={`${loadError} Check your connection and try again.`}
            onRetry={() => setReloadKey((k) => k + 1)}
          />
        </div>
      )}
      {actionError && (
        <div className="mt-4">
          <Notice kind="error">{actionError}</Notice>
        </div>
      )}

      <section className="mt-8" aria-labelledby="invite-heading">
        <h2 id="invite-heading" className="text-xl font-semibold">
          Invite a teammate
        </h2>
        <form
          onSubmit={sendInvite}
          className="mt-3 grid max-w-2xl gap-3 sm:flex sm:flex-wrap sm:items-end"
        >
          <label className="grid min-w-0 gap-1 text-sm sm:flex-1">
            Email address
            <input
              type="email"
              required
              placeholder="teammate@company.com"
              className="rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="grid gap-1 text-sm">
            Role
            <select
              className="rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm"
              value={role}
              onChange={(e) => setRole(e.target.value as TeamRole)}
            >
              {TEAM_ROLES.filter((r) => r !== "owner").map((r) => (
                <option key={r} value={r}>
                  {ROLE_NAME[r]}
                </option>
              ))}
            </select>
          </label>
          <Button type="submit" disabled={inviting || !email.trim()} className="w-full sm:w-auto">
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
          {members === null && !loadError ? (
            <ListSkeleton rows={2} label="Loading members…" />
          ) : members && members.length === 0 ? (
            <EmptyState title="No members yet." />
          ) : members ? (
            <ul className="grid gap-3" aria-labelledby="members-heading">
              {members.map((m) => {
                const who = m.full_name || m.email;
                const isPending = pending?.id === m.id;
                const busy = busyId === m.id;
                return (
                  <li
                    key={m.id}
                    className="grid gap-3 rounded-xl border border-border bg-card p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-start"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">
                        {who}
                        {m.is_you && (
                          <span className="font-normal text-muted-foreground"> (you)</span>
                        )}
                      </p>
                      {m.full_name && (
                        <p className="truncate text-sm text-muted-foreground">{m.email}</p>
                      )}
                      <p className="mt-1 text-sm text-muted-foreground">
                        Joined {when(m.joined_at)} · Last sign-in {when(m.last_login_at)}
                      </p>
                    </div>
                    <div className="grid gap-2 sm:justify-items-end">
                      <div className="flex flex-wrap items-center gap-2">
                        <label htmlFor={`role-${m.id}`} className="text-sm text-muted-foreground">
                          Role
                        </label>
                        <select
                          id={`role-${m.id}`}
                          className="rounded-md border border-input bg-background px-2 py-1.5 text-base sm:text-sm"
                          value={m.role}
                          disabled={busy}
                          onChange={(e) => {
                            const next = e.target.value as TeamRole;
                            if (next !== m.role) setPending({ kind: "role", id: m.id, role: next });
                          }}
                        >
                          {TEAM_ROLES.map((r) => (
                            <option key={r} value={r}>
                              {ROLE_NAME[r]}
                            </option>
                          ))}
                        </select>
                        {!m.is_you && !isPending && (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={busy}
                            aria-label={`Remove ${who} from your team`}
                            onClick={() => setPending({ kind: "remove", id: m.id })}
                          >
                            Remove
                          </Button>
                        )}
                      </div>
                      {isPending && pending?.kind === "role" && (
                        <div className="flex flex-wrap items-center gap-2 text-sm">
                          <span>
                            Change {who} to {ROLE_NAME[pending.role]}?
                          </span>
                          <Button
                            size="sm"
                            disabled={busy}
                            onClick={() => changeRole(m, pending.role)}
                          >
                            Change to {ROLE_NAME[pending.role]}
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => setPending(null)}>
                            Keep as {roleName(m.role)}
                          </Button>
                        </div>
                      )}
                      {isPending && pending?.kind === "remove" && (
                        <div className="flex flex-wrap items-center gap-2 text-sm">
                          <span>Remove {who} from your organization?</span>
                          <Button
                            variant="destructive"
                            size="sm"
                            disabled={busy}
                            onClick={() => remove(m)}
                          >
                            Remove member
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => setPending(null)}>
                            Keep member
                          </Button>
                        </div>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
      </section>

      <section className="mt-10" aria-labelledby="pending-heading">
        <h2 id="pending-heading" className="text-xl font-semibold">
          Pending invitations
        </h2>
        <div className="mt-3">
          {invites === null && !loadError ? (
            <ListSkeleton rows={1} label="Loading invitations…" />
          ) : pendingInvites.length === 0 ? (
            <p className="text-muted-foreground">No pending invitations.</p>
          ) : (
            <ul className="grid gap-2" aria-label="Pending invitations">
              {pendingInvites.map((inv) => (
                <li
                  key={inv.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card px-4 py-3"
                >
                  <span className="min-w-0 break-all">
                    <span className="font-medium">{inv.email}</span>
                    <span className="block text-sm text-muted-foreground">
                      {roleName(inv.role)} · expires {when(inv.expires_at)}
                    </span>
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={busyId === inv.id}
                    aria-label={`Cancel invitation for ${inv.email}`}
                    onClick={() => cancelInvite(inv)}
                  >
                    Cancel invitation
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
