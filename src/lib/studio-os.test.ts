import { describe, expect, it } from "vitest";
import type { ChannelRead } from "@/lib/api/channels";
import {
  areaAction,
  areaStatus,
  channelPageStatus,
  channelStatus,
  channelSteps,
  CHANNEL_SETUP,
  nextStep,
  OS_AREAS,
  type ChannelLoad,
  type SetupFacts,
} from "./studio-os";

const row = (channel: string, enabled: boolean, status: string): ChannelRead => ({
  channel,
  label: channel,
  description: "",
  icon: "",
  enabled,
  status,
  embeddable: false,
  phone_number: null,
  provider: null,
  configuration: {},
  masked_secrets: {},
});

const area = (id: string) => {
  const found = OS_AREAS.find((a) => a.id === id);
  if (!found) throw new Error(`missing area ${id}`);
  return found;
};

const READY_CHAT: ChannelLoad = {
  state: "ready",
  items: [row("chat", true, "active"), row("widget", true, "active")],
};

describe("channelStatus", () => {
  it("reads a missing row as not connected", () => {
    expect(channelStatus(undefined)).toEqual({ label: "Not connected yet", tone: "not-connected" });
  });

  it("reads an enabled active row as connected", () => {
    expect(channelStatus(row("chat", true, "active"))).toEqual({
      label: "Connected",
      tone: "connected",
    });
  });

  it("reads a paused row as paused and a disabled row as not connected", () => {
    expect(channelStatus(row("chat", true, "paused")).label).toBe("Paused");
    expect(channelStatus(row("chat", false, "disabled")).label).toBe("Not connected yet");
    expect(channelStatus(row("chat", false, "active")).label).toBe("Not connected yet");
  });
});

describe("channelPageStatus", () => {
  it("maps website chat to the chat channel row", () => {
    expect(
      channelPageStatus("website-chat", READY_CHAT.state === "ready" ? READY_CHAT.items : []).label,
    ).toBe("Connected");
  });

  it("reports WhatsApp, Instagram and Voice connected only when their API row is on and active", () => {
    const items = [
      row("chat", true, "active"),
      row("whatsapp", true, "active"),
      row("instagram", false, "disabled"),
      row("voice", true, "paused"),
    ];
    expect(channelPageStatus("whatsapp", items).label).toBe("Connected");
    expect(channelPageStatus("instagram", items).label).toBe("Not connected yet");
    expect(channelPageStatus("voice", items).label).toBe("Paused");
  });

  it("reports WhatsApp, Instagram and Voice not connected when they have no row", () => {
    for (const key of ["whatsapp", "instagram", "voice"] as const) {
      expect(channelPageStatus(key, [row("chat", true, "active")]).label).toBe("Not connected yet");
    }
  });
});

describe("areaStatus", () => {
  it("shows Checking while the channel load is still running", () => {
    expect(areaStatus(area("website-chat"), { state: "loading" }).label).toBe("Checking…");
  });

  it("shows Not connected yet when there is no assistant or the channels request failed", () => {
    expect(areaStatus(area("website-chat"), { state: "unavailable" }).label).toBe(
      "Not connected yet",
    );
  });

  it("uses the loaded website chat channel", () => {
    expect(areaStatus(area("website-chat"), READY_CHAT).label).toBe("Connected");
    expect(areaStatus(area("website-chat"), { state: "ready", items: [] }).label).toBe(
      "Not connected yet",
    );
  });

  it("uses the site STATUS vocabulary for areas that have a roadmap status", () => {
    expect(areaStatus(area("omnichannel-inbox"), READY_CHAT)).toEqual({
      label: "Planned",
      tone: "planned",
    });
    expect(areaStatus(area("ai-studio"), READY_CHAT)).toEqual({
      label: "Available in demo",
      tone: "available",
    });
    expect(areaStatus(area("marketplace"), READY_CHAT).label).toBe("Planned");
  });

  it("shows Not connected yet for an area with no known status", () => {
    expect(areaStatus(area("marketing"), READY_CHAT).label).toBe("Not connected yet");
    expect(areaStatus(area("integrations"), READY_CHAT).label).toBe("Not connected yet");
  });

  it("never shows Live for any area in any load state", () => {
    const loads: ChannelLoad[] = [{ state: "loading" }, { state: "unavailable" }, READY_CHAT];
    for (const load of loads) {
      for (const a of OS_AREAS) {
        expect(areaStatus(a, load).label).not.toMatch(/live/i);
      }
    }
  });
});

describe("areaAction", () => {
  it("offers Set up for a channel that is not connected and Open once it is", () => {
    const website = area("website-chat");
    expect(areaAction(website, areaStatus(website, { state: "unavailable" }))).toEqual({
      label: "Set up",
      kind: "channel",
      channel: "website-chat",
    });
    expect(areaAction(website, areaStatus(website, READY_CHAT)).label).toBe("Open");
  });

  it("opens the existing screen for page areas", () => {
    expect(areaAction(area("calls"), { label: "Planned", tone: "planned" })).toEqual({
      label: "Open",
      kind: "page",
      to: "/studio/calls",
    });
  });

  it("offers no destination for marketing, because its screen does not exist yet", () => {
    expect(
      areaAction(area("marketing"), { label: "Not connected yet", tone: "not-connected" }),
    ).toEqual({
      label: "Set up",
      kind: "none",
    });
  });
});

describe("OS_AREAS", () => {
  it("lists the ten product areas once each", () => {
    expect(OS_AREAS).toHaveLength(10);
    expect(new Set(OS_AREAS.map((a) => a.id)).size).toBe(10);
  });
});

describe("channelSteps", () => {
  const ready = (overrides: Partial<Extract<SetupFacts, { state: "ready" }>> = {}): SetupFacts => ({
    state: "ready",
    channels: [row("chat", true, "active")],
    deploy: {
      widget_status: "published",
      domains: ["example.test"],
      verification: { installed: true, events_count: 3, loads_count: 3, last_seen: null },
    },
    ...overrides,
  });

  it("leaves every website chat step unknown while loading", () => {
    const steps = channelSteps("website-chat", { state: "loading" });
    expect(steps.map((s) => s.done)).toEqual([null, null, null, null, null]);
    expect(nextStep(steps)?.label).toBe("An assistant is created");
  });

  it("marks every website chat step not done when there is no assistant", () => {
    const steps = channelSteps("website-chat", { state: "no-assistant" });
    expect(steps.map((s) => s.done)).toEqual([false, false, false, false, false]);
  });

  it("reports all website chat steps done and nothing next when the data shows a live setup", () => {
    const steps = channelSteps("website-chat", ready());
    expect(steps.map((s) => s.done)).toEqual([true, true, true, true, true]);
    expect(nextStep(steps)).toBeNull();
  });

  it("keeps install steps unknown, not done, when the deploy record could not load", () => {
    const steps = channelSteps("website-chat", ready({ deploy: null }));
    expect(steps.map((s) => s.done)).toEqual([true, true, null, null, null]);
    expect(nextStep(steps)?.label).toBe("Your website domain is allowed");
  });

  it("marks website chat not done when the chat channel is off", () => {
    const steps = channelSteps(
      "website-chat",
      ready({ channels: [row("chat", false, "disabled")] }),
    );
    expect(steps[1]?.done).toBe(false);
    expect(nextStep(steps)?.label).toBe("Website chat is turned on");
  });

  it("keeps the channel step unknown when the channels request failed", () => {
    const steps = channelSteps("whatsapp", ready({ channels: null }));
    expect(steps[1]?.done).toBeNull();
  });

  it("marks WhatsApp, Instagram and Voice not connected until their row is on", () => {
    for (const key of ["whatsapp", "instagram", "voice"] as const) {
      const steps = channelSteps(key, ready());
      const channelStep = steps[steps.length - 1];
      expect(channelStep?.done).toBe(false);
      expect(channelStep?.detail).toContain("is not turned on for this assistant");
    }
  });

  it("adds a saved-setting step for each identifier page, and marks it done from the API row", () => {
    const whatsappSaved = channelSteps(
      "whatsapp",
      ready({
        channels: [
          {
            ...row("whatsapp", true, "active"),
            configuration: { phone_number_id: "100200300400500" },
          },
        ],
      }),
    );
    const saved = whatsappSaved.find((step) => step.label === "Phone number ID is saved");
    expect(saved?.done).toBe(true);
    expect(whatsappSaved[whatsappSaved.length - 1]?.done).toBe(true);

    const voiceUnsaved = channelSteps(
      "voice",
      ready({ channels: [row("voice", false, "disabled")] }),
    );
    expect(voiceUnsaved.find((step) => step.label === "Business phone number is saved")?.done).toBe(
      false,
    );

    const voiceSaved = channelSteps(
      "voice",
      ready({ channels: [{ ...row("voice", true, "active"), phone_number: "+14155550123" }] }),
    );
    expect(voiceSaved.find((step) => step.label === "Business phone number is saved")?.done).toBe(
      true,
    );
  });

  it("does not add a saved-setting step to website chat, which has no identifier to save", () => {
    const steps = channelSteps("website-chat", ready());
    expect(steps.some((step) => step.label.endsWith("is saved"))).toBe(false);
  });

  it("lists needs by name for every channel setup page", () => {
    for (const setup of Object.values(CHANNEL_SETUP)) {
      expect(setup.needs.length).toBeGreaterThan(0);
      for (const need of setup.needs) {
        expect(need).not.toMatch(/sk_|tok_|token|secret|@/i);
      }
    }
  });
});
