import { apiRequest } from "./client";

// Team members and invitations belong to the organization, not a workspace.
// Roles are lowercase on the wire: owner, admin, member, viewer.

export const TEAM_ROLES = ["owner", "admin", "member", "viewer"] as const;
export type TeamRole = (typeof TEAM_ROLES)[number];

export type TeamMember = {
  id: string;
  user_id: string;
  email: string;
  full_name: string | null;
  role: TeamRole | string;
  status: string;
  joined_at: string | null;
  last_login_at: string | null;
  is_you: boolean;
};

export type MemberList = { items: TeamMember[]; total: number };

export type Invitation = {
  id: string;
  email: string;
  role: TeamRole | string;
  status: string;
  invited_by: string | null;
  invite_url: string | null;
  expires_at: string;
  created_at: string;
  accepted_at: string | null;
};

export type InvitationList = { items: Invitation[]; total: number };

export function listMembers() {
  return apiRequest<MemberList>("/team/members");
}

export function changeMemberRole(memberId: string, role: TeamRole) {
  return apiRequest<TeamMember>(`/team/members/${memberId}`, {
    method: "PATCH",
    body: { role },
  });
}

export function removeMember(memberId: string) {
  return apiRequest<unknown>(`/team/members/${memberId}`, { method: "DELETE" });
}

export function listInvitations() {
  return apiRequest<InvitationList>("/team/invitations");
}

export function createInvitation(input: { email: string; role: TeamRole }) {
  return apiRequest<{ invitation: Invitation; message: string }>("/team/invitations", {
    method: "POST",
    body: input,
  });
}

export function revokeInvitation(invitationId: string) {
  return apiRequest<unknown>(`/team/invitations/${invitationId}`, { method: "DELETE" });
}
