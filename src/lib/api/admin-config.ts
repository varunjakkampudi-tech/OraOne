// Super-admin configuration console API. Every call is authorized by the server
// (platform role super_admin); the browser holds no secret and never receives one in full.

import { apiRequest } from "./client";
import type { ConfigEnvironment, ConfigList } from "@/lib/admin-config";

export type SaveResult = {
  name: string;
  environment: ConfigEnvironment;
  status: "saved" | "cleared" | "unchanged";
  restart_required: boolean;
};

export type ReloadResult = {
  status: "reloaded";
  changed_keys: string[];
  note: string;
};

export function listAdminConfig(environment: ConfigEnvironment): Promise<ConfigList> {
  return apiRequest<ConfigList>(`/admin/config?environment=${environment}`);
}

export function saveAdminConfig(
  name: string,
  body: {
    environment: ConfigEnvironment;
    value: string | null;
    confirm: string;
    reason: string;
  },
): Promise<SaveResult> {
  return apiRequest<SaveResult>(`/admin/config/${encodeURIComponent(name)}`, {
    method: "PUT",
    body,
  });
}

export function reloadAdminConfig(body: {
  confirm: string;
  reason: string;
}): Promise<ReloadResult> {
  return apiRequest<ReloadResult>("/admin/config/reload", { method: "POST", body });
}
