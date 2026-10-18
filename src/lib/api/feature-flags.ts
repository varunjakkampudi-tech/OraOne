// Beta feature flag API. GET /api/feature-flags is available to any signed-in user.
// The /api/admin/feature-flags calls require a super-admin; the server enforces that.
// Emails are sent only on the cohort write and never come back in a response.

import { apiRequest } from "./client";

export type EnabledFlagsResponse = {
  enabled: string[];
  cache_ttl_seconds: number;
};

export type AdminFlagOverride = {
  organization_id: string;
  enabled: boolean;
};

export type AdminFlag = {
  key: string;
  description: string;
  default_enabled: boolean;
  code_rollout: { organization_count: number; member_count: number };
  organization_overrides: AdminFlagOverride[];
  cohort: { member_count: number; enabled_count: number; disabled_count: number };
};

export type FlagWriteResult = {
  flag_key: string;
  scope: "organization" | "cohort_member";
  enabled: boolean | null;
};

export function getEnabledFeatureFlags(organizationId?: string): Promise<EnabledFlagsResponse> {
  const query = organizationId ? `?organization_id=${encodeURIComponent(organizationId)}` : "";
  return apiRequest<EnabledFlagsResponse>(`/feature-flags${query}`);
}

export function listAdminFeatureFlags(): Promise<{ flags: AdminFlag[] }> {
  return apiRequest<{ flags: AdminFlag[] }>("/admin/feature-flags");
}

/** ``enabled: null`` removes the organisation override. */
export function setOrganizationFlagOverride(
  flagKey: string,
  organizationId: string,
  enabled: boolean | null,
): Promise<FlagWriteResult> {
  return apiRequest<FlagWriteResult>(
    `/admin/feature-flags/${encodeURIComponent(flagKey)}/organizations/${encodeURIComponent(organizationId)}`,
    { method: "PUT", body: { enabled } },
  );
}

/** ``enabled: null`` removes the cohort membership override for this email. */
export function setCohortFlagMember(
  flagKey: string,
  email: string,
  enabled: boolean | null,
): Promise<FlagWriteResult> {
  return apiRequest<FlagWriteResult>(
    `/admin/feature-flags/${encodeURIComponent(flagKey)}/cohort/members`,
    { method: "PUT", body: { email, enabled } },
  );
}
