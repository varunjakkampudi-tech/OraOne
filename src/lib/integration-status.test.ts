import { describe, expect, it } from "vitest";
import type { IntegrationCatalogEntry } from "@/lib/api/integrations";
import {
  canSync,
  primaryAction,
  rowStatusLabel,
  setupStatusLabel,
  setupStatusTone,
} from "@/lib/integration-status";

function entry(
  overrides: Partial<IntegrationCatalogEntry> & {
    auth?: string;
    sync_available?: boolean;
  } = {},
): IntegrationCatalogEntry {
  const { auth = "oauth", sync_available = false, ...rest } = overrides;
  return {
    catalog: {
      provider: "slack",
      name: "Slack",
      category: "communication",
      type: "other",
      auth,
      description: "",
      available: true,
      sync_available,
      required_settings: ["SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET"],
    },
    integration: null,
    setup_status: "requires_account_setup",
    setup_message: "",
    ...rest,
  };
}

const liveRow = {
  id: "00000000-0000-0000-0000-000000000001",
  provider: "slack",
  category: "communication",
  type: "other",
  status: "connected",
  connection_type: "oauth",
  external_account: "team",
  sync_schedule: "manual",
  last_synced_at: null,
  last_error: null,
  created_at: "2026-10-01T00:00:00Z",
  updated_at: "2026-10-01T00:00:00Z",
};

describe("integration setup status", () => {
  it("labels every server status in plain language", () => {
    expect(setupStatusLabel("connected")).toBe("Connected");
    expect(setupStatusLabel("not_connected")).toBe("Not connected");
    expect(setupStatusLabel("requires_account_setup")).toBe("Needs setup");
    expect(setupStatusLabel("planned")).toBe("Planned");
  });

  it("warns only when account setup is required", () => {
    expect(setupStatusTone("requires_account_setup")).toBe("warn");
    expect(setupStatusTone("connected")).toBe("ok");
    expect(setupStatusTone("not_connected")).toBe("muted");
    expect(setupStatusTone("planned")).toBe("muted");
  });

  it("offers Connect only for a configured, not-yet-connected OAuth provider", () => {
    expect(primaryAction(entry({ setup_status: "not_connected" }))).toBe("connect");
    expect(primaryAction(entry({ setup_status: "requires_account_setup" }))).toBe("needs_setup");
    expect(primaryAction(entry({ setup_status: "planned" }))).toBe("planned");
  });

  it("never offers Connect for a webhook-only provider", () => {
    expect(primaryAction(entry({ setup_status: "not_connected", auth: "webhook" }))).toBe(
      "set_up_on_webhooks",
    );
  });

  it("shows a stored row's own status when it is not live", () => {
    const disconnected = entry({
      setup_status: "not_connected",
      integration: { ...liveRow, status: "error" },
    });
    expect(rowStatusLabel(disconnected)).toBe("error");
    const live = entry({ setup_status: "connected", integration: liveRow });
    expect(rowStatusLabel(live)).toBe("Connected");
  });

  it("refuses sync for planned sync and for accounts that are not live", () => {
    expect(canSync(entry({ integration: liveRow, setup_status: "connected" }))).toBe(false);
    expect(
      canSync(
        entry({
          sync_available: true,
          integration: liveRow,
          setup_status: "connected",
        }),
      ),
    ).toBe(true);
    expect(
      canSync(
        entry({
          sync_available: true,
          integration: { ...liveRow, status: "disconnected" },
          setup_status: "not_connected",
        }),
      ),
    ).toBe(false);
  });

  it("never reports a connection that the server did not return", () => {
    const planned = entry({ setup_status: "planned" });
    expect(planned.integration).toBeNull();
    expect(primaryAction(planned)).not.toBe("disconnect");
    expect(rowStatusLabel(planned)).toBe("Planned");
  });
});
