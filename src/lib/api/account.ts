import { apiRequest } from "./client";
import type { Me } from "./auth";

/** Updates the signed-in user's display name. */
export function updateProfileName(fullName: string) {
  return apiRequest<Me>("/auth/profile", { method: "PATCH", body: { full_name: fullName } });
}
