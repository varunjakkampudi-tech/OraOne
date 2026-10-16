import { apiRequest } from "./client";

// Passwordless sign-in: an emailed one-time code is exchanged for a session
// cookie. The backend never reveals whether an address already has an account.

export type Me = {
  userId: string;
  email: string;
  name: string;
  role: string;
  platform_role: string;
  plan: string;
  status: string;
};

export type Identity = {
  user: { id: string; email: string; full_name: string | null };
  organization: { id: string; name: string; slug: string; plan: string };
  membership: { organization_id: string; role: string; status: string };
  is_new_user: boolean;
};

export function requestEmailCode(input: { email: string; name?: string }) {
  return apiRequest<{ message: string }>("/auth/email-code/request", {
    method: "POST",
    body: input,
  });
}

export function verifyEmailCode(input: { email: string; code: string }) {
  return apiRequest<{ token_type: string; expires_in: number }>("/auth/email-code/verify", {
    method: "POST",
    body: input,
  });
}

/**
 * Development-only password sign-in. The backend answers 404 outside development,
 * so this is only ever usable on a local machine with the seeded accounts.
 */
export function devLogin(input: { email: string; password: string }) {
  return apiRequest<{ token_type: string; expires_in: number }>("/auth/dev-login", {
    method: "POST",
    body: input,
  });
}

export function getMe() {
  return apiRequest<Me>("/auth/me");
}

/** Idempotent: provisions the user's organization and default workspace on first call. */
export function getIdentity() {
  return apiRequest<Identity>("/auth/identity");
}

export function logout() {
  return apiRequest<{ message: string }>("/auth/logout", { method: "POST", body: {} });
}
