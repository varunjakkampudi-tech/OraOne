import type { Status } from "@/content/site/types";
import { STATUS_LABEL } from "@/content/site/navigation";
import type { ChannelRead, DeployInfo } from "@/lib/api/channels";
import { CHANNEL_SETTINGS } from "@/lib/channel-settings";

// OraOne OS: the product areas shown on the /studio hub and the setup pages for channels.
// Status comes only from data the app already has:
// - channel rows from GET /api/agents/{id}/channels (website chat);
// - the STATUS_LABEL vocabulary for areas that have a roadmap status (site content);
// - anything else reads "Not connected yet", never "Live".

export const NOT_CONNECTED = "Not connected yet";
export const CHECKING = "Checking…";

export type ChannelPageKey = "website-chat" | "whatsapp" | "instagram" | "voice";

export const CHANNEL_PAGE_KEYS: readonly ChannelPageKey[] = [
  "website-chat",
  "whatsapp",
  "instagram",
  "voice",
];

export function isChannelPageKey(value: string): value is ChannelPageKey {
  return (CHANNEL_PAGE_KEYS as readonly string[]).includes(value);
}

export const CHANNEL_PAGE_LABEL: Record<ChannelPageKey, string> = {
  "website-chat": "Website chat",
  whatsapp: "WhatsApp",
  instagram: "Instagram",
  voice: "AI Voice",
};

// The channel key the channels API uses for each setup page. A page reads as connected only when
// its API row is turned on and active. A missing row reads as not connected.
export const CHANNEL_API_KEY: Record<ChannelPageKey, string> = {
  "website-chat": "chat",
  whatsapp: "whatsapp",
  instagram: "instagram",
  voice: "voice",
};

export type OsStatus = {
  label: string;
  tone: "connected" | "paused" | "available" | "planned" | "not-connected" | "checking";
};

/** Connection state of one channel row. A missing row means not connected. */
export function channelStatus(item: Pick<ChannelRead, "enabled" | "status"> | undefined): OsStatus {
  if (!item) return { label: NOT_CONNECTED, tone: "not-connected" };
  if (item.enabled && item.status === "active") return { label: "Connected", tone: "connected" };
  if (item.status === "paused") return { label: "Paused", tone: "paused" };
  return { label: NOT_CONNECTED, tone: "not-connected" };
}

/** A roadmap status from the site vocabulary, with the same label the marketing pages use. */
export function constantStatus(status: Status): OsStatus {
  return {
    label: STATUS_LABEL[status],
    tone: status === "available" ? "available" : "planned",
  };
}

/** The channel state of one setup page, from the channels rows that were loaded. */
export function channelPageStatus(key: ChannelPageKey, items: readonly ChannelRead[]): OsStatus {
  const apiKey = CHANNEL_API_KEY[key];
  return channelStatus(apiKey ? items.find((item) => item.channel === apiKey) : undefined);
}

export type AreaTarget =
  | { kind: "channel"; channel: ChannelPageKey }
  | { kind: "page"; to: StudioPagePath }
  | { kind: "none" };

export type StudioPagePath =
  | "/studio/inbox"
  | "/studio/calls"
  | "/studio/assistants"
  | "/studio/marketplace"
  | "/studio/integrations";

export type OsArea = {
  id: string;
  name: string;
  summary: string;
  target: AreaTarget;
  /** Roadmap status for areas without channel data. Omitted means no status is known. */
  status?: Status;
};

/** The ten product areas on the hub, in the order they are shown. */
export const OS_AREAS: readonly OsArea[] = [
  {
    id: "website-chat",
    name: "Website chat",
    summary: "Answers visitors on your website from your assistant and its documents.",
    target: { kind: "channel", channel: "website-chat" },
  },
  {
    id: "ai-voice",
    name: "AI Voice",
    summary: "Answers phone calls with your assistant.",
    target: { kind: "channel", channel: "voice" },
  },
  {
    id: "whatsapp",
    name: "WhatsApp",
    summary: "Chat with customers on WhatsApp, in the same inbox as your website chat.",
    target: { kind: "channel", channel: "whatsapp" },
  },
  {
    id: "instagram",
    name: "Instagram",
    summary: "Reply to Instagram messages, in the same inbox as your other channels.",
    target: { kind: "channel", channel: "instagram" },
  },
  {
    id: "omnichannel-inbox",
    name: "Omnichannel inbox",
    summary: "Every channel's conversations in one place, with staff replies.",
    target: { kind: "page", to: "/studio/inbox" },
    status: "planned",
  },
  {
    id: "ai-studio",
    name: "AI Studio",
    summary: "Build assistants and agents, add knowledge and test answers before publishing.",
    target: { kind: "page", to: "/studio/assistants" },
    status: "available",
  },
  {
    id: "marketing",
    name: "Marketing",
    summary: "Campaigns and content for the people you want to reach.",
    target: { kind: "none" },
  },
  {
    id: "marketplace",
    name: "Marketplace",
    summary: "Ready-made assistants and connectors you can add to your workspace.",
    target: { kind: "page", to: "/studio/marketplace" },
    status: "planned",
  },
  {
    id: "integrations",
    name: "Integrations",
    summary: "Connect the tools your team already uses to your assistants.",
    target: { kind: "page", to: "/studio/integrations" },
  },
  {
    id: "calls",
    name: "Calls",
    summary: "Plan call campaigns from your imported leads.",
    target: { kind: "page", to: "/studio/calls" },
    status: "planned",
  },
];

export type ChannelLoad =
  | { state: "loading" }
  /** No assistant, or the channels request failed: nothing is connected as far as the app knows. */
  | { state: "unavailable" }
  | { state: "ready"; items: readonly ChannelRead[] };

/** The status an area card shows. Channel areas read the loaded channel rows. */
export function areaStatus(area: OsArea, load: ChannelLoad): OsStatus {
  if (area.target.kind === "channel") {
    if (load.state === "loading") return { label: CHECKING, tone: "checking" };
    if (load.state === "unavailable") return { label: NOT_CONNECTED, tone: "not-connected" };
    return channelPageStatus(area.target.channel, load.items);
  }
  if (area.status) return constantStatus(area.status);
  return { label: NOT_CONNECTED, tone: "not-connected" };
}

/** Where an area's one primary action goes, and what it says. Null target means no screen yet. */
export type AreaAction =
  | { label: "Set up" | "Open"; kind: "channel"; channel: ChannelPageKey }
  | { label: "Open"; kind: "page"; to: StudioPagePath }
  | { label: "Set up"; kind: "none" };

export function areaAction(area: OsArea, status: OsStatus): AreaAction {
  if (area.target.kind === "channel") {
    const label = status.tone === "connected" ? "Open" : "Set up";
    return { label, kind: "channel", channel: area.target.channel };
  }
  if (area.target.kind === "page") return { label: "Open", kind: "page", to: area.target.to };
  return { label: "Set up", kind: "none" };
}

export type ChecklistStep = {
  label: string;
  /** true when the data shows it done, false when it shows it is not, null while unknown. */
  done: boolean | null;
  detail: string;
  /** What the user does next if this step is not done. */
  action: string;
};

export type ChannelSetup = {
  title: string;
  intro: string;
  /** Accounts and settings the user needs, by name only. Never values or secrets. */
  needs: string[];
};

export const CHANNEL_SETUP: Record<ChannelPageKey, ChannelSetup> = {
  "website-chat": {
    title: "Website chat",
    intro:
      "Put your assistant on your website. Visitors can ask questions in a chat bubble that answers from your documents.",
    needs: [
      "An assistant in AI Studio, with its instructions saved",
      "A website you can edit, to paste one line of code",
      "Your website's domain, to allow the chat to load there",
    ],
  },
  whatsapp: {
    title: "WhatsApp",
    intro: "Answer WhatsApp messages with your assistant and hand them to your team when needed.",
    needs: [
      "A Meta Business account, with WhatsApp Business in Meta Business Manager",
      "A WhatsApp Business phone number that is not used by another WhatsApp account",
      "A verified business name in Meta Business Manager",
    ],
  },
  instagram: {
    title: "Instagram",
    intro:
      "Reply to Instagram direct messages with your assistant, in the same inbox as your other channels.",
    needs: [
      "An Instagram professional account (Business or Creator)",
      "A Facebook Page linked to that Instagram account",
      "Access to that Page in Meta Business Manager",
    ],
  },
  voice: {
    title: "AI Voice",
    intro: "Let your assistant answer phone calls, with the same knowledge as your website chat.",
    needs: [
      "A telephony account with a phone number, for example a Twilio account",
      "The phone number you want callers to dial",
      "Call hours that match your team's availability",
    ],
  },
};

export type DeployFacts = Pick<DeployInfo, "widget_status" | "domains" | "verification">;

/**
 * Facts the setup pages read from data. `loading` until the first request settles.
 * `channels` and `deploy` are null when their request failed, which keeps those steps unknown.
 */
export type SetupFacts =
  | { state: "loading" }
  /** The workspace or assistant lookup failed, so nothing can be said about the setup. */
  | { state: "unknown" }
  | { state: "no-assistant" }
  | {
      state: "ready";
      channels: readonly ChannelRead[] | null;
      deploy: DeployFacts | null;
    };

const CONNECT_ACTION = (key: ChannelPageKey) =>
  `Turn on ${CHANNEL_PAGE_LABEL[key]} for your assistant.`;

function assistantStep(facts: SetupFacts): ChecklistStep {
  const done =
    facts.state === "loading" || facts.state === "unknown" ? null : facts.state === "ready";
  return {
    label: "An assistant is created",
    done,
    detail:
      done === null
        ? "Checking your workspace."
        : done
          ? "Your first assistant is in place."
          : "No assistant exists in this workspace yet.",
    action: "Create an assistant in AI Studio.",
  };
}

function channelStep(key: ChannelPageKey, facts: SetupFacts): ChecklistStep {
  const label = `${CHANNEL_PAGE_LABEL[key]} is turned on`;
  const action = CONNECT_ACTION(key);
  if (facts.state === "loading" || facts.state === "unknown") {
    return { label, done: null, detail: "Checking the channel.", action };
  }
  if (facts.state === "no-assistant") {
    return { label, done: false, detail: "Create an assistant first.", action };
  }
  if (facts.channels === null) {
    return { label, done: null, detail: "Could not load the channel state.", action };
  }
  const done = channelPageStatus(key, facts.channels).tone === "connected";
  const detail = done
    ? `${CHANNEL_PAGE_LABEL[key]} is connected.`
    : `${CHANNEL_PAGE_LABEL[key]} is not turned on for this assistant.`;
  return { label, done, detail, action };
}

/** The identifier a page saves (for example the WhatsApp phone number ID), read from the API row. */
function settingStep(key: ChannelPageKey, facts: SetupFacts): ChecklistStep | null {
  const field = CHANNEL_SETTINGS[key].fields[0];
  if (!field) return null;
  const label = `${field.label} is saved`;
  const action = `Enter your ${field.label.toLowerCase()} in the form below, then save.`;
  if (facts.state === "loading" || facts.state === "unknown") {
    return { label, done: null, detail: "Checking the saved settings.", action };
  }
  if (facts.state === "no-assistant") {
    return { label, done: false, detail: "Create an assistant first.", action };
  }
  if (facts.channels === null) {
    return { label, done: null, detail: "Could not load the saved settings.", action };
  }
  const apiRow = facts.channels.find((item) => item.channel === CHANNEL_API_KEY[key]);
  const saved =
    field.key === "phone_number" ? apiRow?.phone_number : apiRow?.configuration?.[field.key];
  const done = Boolean(saved);
  return {
    label,
    done,
    detail: done ? `${field.label} is saved.` : `${field.label} is not saved yet.`,
    action,
  };
}

function websiteSteps(facts: SetupFacts): ChecklistStep[] {
  // Install steps need the assistant's deploy record. Without it they stay unknown, never "not done".
  const deploy = facts.state === "ready" ? facts.deploy : null;
  const noAssistant = facts.state === "no-assistant";
  const deployUnknown = facts.state === "ready" && deploy === null;
  const unknown = facts.state === "loading" || facts.state === "unknown" || deployUnknown;

  const install = (done: (d: DeployFacts) => boolean): boolean | null => {
    if (noAssistant) return false;
    if (unknown || deploy === null) return null;
    return done(deploy);
  };
  const detail = (describe: (d: DeployFacts) => string): string => {
    if (noAssistant) return "Create an assistant first.";
    if (deploy === null) {
      return deployUnknown
        ? "Could not load the install settings."
        : "Checking the install settings.";
    }
    return describe(deploy);
  };

  return [
    assistantStep(facts),
    channelStep("website-chat", facts),
    {
      label: "Your website domain is allowed",
      done: install((d) => d.domains.length > 0),
      detail: detail((d) =>
        d.domains.length > 0
          ? `${d.domains.length} domain(s) allowed.`
          : "No domain is allowed yet.",
      ),
      action: "Add your website domain on the assistant's Add to website page.",
    },
    {
      label: "The widget is published",
      done: install((d) => d.widget_status === "published"),
      detail: detail((d) =>
        d.widget_status === "published"
          ? "The widget is published."
          : "The widget is not published yet.",
      ),
      action: "Publish the widget on the assistant's Add to website page.",
    },
    {
      label: "A visit on your site is confirmed",
      done: install((d) => d.verification.installed),
      detail: detail((d) =>
        d.verification.installed
          ? "A visit from your website has been seen."
          : "No visit from your website has been seen yet.",
      ),
      action: "Paste the one-line code on your site and load a page that has it.",
    },
  ];
}

/** The checklist for one channel page, built from the facts that were loaded. */
export function channelSteps(key: ChannelPageKey, facts: SetupFacts): ChecklistStep[] {
  if (key === "website-chat") return websiteSteps(facts);
  const setting = settingStep(key, facts);
  return [assistantStep(facts), ...(setting ? [setting] : []), channelStep(key, facts)];
}

/** The first step that is not done yet. Null when every step is done. */
export function nextStep(steps: readonly ChecklistStep[]): ChecklistStep | null {
  return steps.find((step) => step.done !== true) ?? null;
}
