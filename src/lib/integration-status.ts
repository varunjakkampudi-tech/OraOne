import type { IntegrationCatalogEntry, IntegrationSetupStatus } from "@/lib/api/integrations";

// Plain-language status and the one action a catalog row may offer. Everything here
// is derived from the server's setup_status and the saved integration row, so the
// screen never shows a connection the API did not report.

export type IntegrationTone = "ok" | "muted" | "warn";

export type IntegrationAction =
  "disconnect" | "connect" | "set_up_on_webhooks" | "needs_setup" | "planned";

export const SETUP_STATUS_LABELS: Record<IntegrationSetupStatus, string> = {
  connected: "Connected",
  not_connected: "Not connected",
  requires_account_setup: "Needs setup",
  planned: "Planned",
};

export function setupStatusLabel(status: IntegrationSetupStatus): string {
  return SETUP_STATUS_LABELS[status] ?? "Planned";
}

export function setupStatusTone(status: IntegrationSetupStatus): IntegrationTone {
  if (status === "connected") return "ok";
  if (status === "requires_account_setup") return "warn";
  return "muted";
}

/** Label for the status pill. A saved row that is not live shows its own status. */
export function rowStatusLabel(entry: IntegrationCatalogEntry): string {
  if (entry.integration && entry.integration.status !== "connected") {
    return entry.integration.status;
  }
  return setupStatusLabel(entry.setup_status);
}

export function primaryAction(entry: IntegrationCatalogEntry): IntegrationAction {
  if (entry.integration) return "disconnect";
  if (entry.setup_status === "connected") return "disconnect";
  if (entry.setup_status === "not_connected") {
    return entry.catalog.auth === "webhook" ? "set_up_on_webhooks" : "connect";
  }
  if (entry.setup_status === "requires_account_setup") return "needs_setup";
  return "planned";
}

/** Sync is offered only when the provider implements it and the account is live. */
export function canSync(entry: IntegrationCatalogEntry): boolean {
  return (
    entry.catalog.sync_available === true &&
    entry.integration !== null &&
    entry.integration.status === "connected"
  );
}
