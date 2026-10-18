// Super-admin configuration console API. Every call is authorized by the server
// (platform role super_admin); the browser holds no secret and never receives one in full.
// Saving writes a draft. Only publish makes drafts active.

import { apiRequest } from "./client";
import type { ConfigEnvironment, ConfigList, DraftList, PublishHistory } from "@/lib/admin-config";

export type DraftSaveResult = {
  name: string;
  environment: ConfigEnvironment;
  status: "draft_saved" | "draft_removal_saved" | "unchanged";
  active: false;
  publish_required: boolean;
  restart_required: false;
};

export type DiscardResult = {
  name: string;
  environment: ConfigEnvironment;
  status: "discarded";
  active: false;
  restart_required: false;
};

export type PublishResult = {
  environment: ConfigEnvironment;
  status: "published";
  published_count: number;
  changed_keys: string[];
  active: true;
  restart_required: true;
};

export type ReloadResult = {
  status: "reloaded";
  changed_keys: string[];
  note: string;
};

export function listAdminConfig(environment: ConfigEnvironment): Promise<ConfigList> {
  return apiRequest<ConfigList>(`/admin/config?environment=${environment}`);
}

export function listAdminDrafts(environment: ConfigEnvironment): Promise<DraftList> {
  return apiRequest<DraftList>(`/admin/config/drafts?environment=${environment}`);
}

export function listAdminPublishHistory(environment: ConfigEnvironment): Promise<PublishHistory> {
  return apiRequest<PublishHistory>(`/admin/config/history?environment=${environment}`);
}

export function saveAdminConfigDraft(
  name: string,
  body: {
    environment: ConfigEnvironment;
    value: string | null;
    confirm: string;
    reason: string;
  },
): Promise<DraftSaveResult> {
  return apiRequest<DraftSaveResult>(`/admin/config/${encodeURIComponent(name)}`, {
    method: "PUT",
    body,
  });
}

export function discardAdminDraft(
  name: string,
  environment: ConfigEnvironment,
): Promise<DiscardResult> {
  return apiRequest<DiscardResult>(
    `/admin/config/drafts/${encodeURIComponent(name)}?environment=${environment}`,
    { method: "DELETE" },
  );
}

export function publishAdminDrafts(body: {
  environment: ConfigEnvironment;
  confirm: string;
  reason: string;
  reviewed: string[];
}): Promise<PublishResult> {
  return apiRequest<PublishResult>("/admin/config/publish", { method: "POST", body });
}

export function reloadAdminConfig(body: {
  confirm: string;
  reason: string;
}): Promise<ReloadResult> {
  return apiRequest<ReloadResult>("/admin/config/reload", { method: "POST", body });
}
