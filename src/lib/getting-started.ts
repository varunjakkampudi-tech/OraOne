// Getting started: what each kind of customer does first, and how far along they are.
// Pure data and functions. No network calls, no browser storage.
//
// A step is done only when its completion source key is in the completed set. A source that the
// caller never checked is "unknown" and is never counted as done. Unknown keys are ignored.

export const USE_CASE_IDS = [
  "small_business",
  "website_owner",
  "whatsapp_business",
  "instagram_seller",
  "marketing",
  "call_centre",
] as const;

export type UseCaseId = (typeof USE_CASE_IDS)[number];

export type GettingStartedChannel = "website-chat" | "whatsapp" | "instagram" | "voice";

export type GettingStartedRoute =
  | {
      kind: "page";
      to:
        | "/studio/assistants"
        | "/studio/knowledge"
        | "/studio/leads"
        | "/studio/marketing"
        | "/studio/calls"
        | "/studio/inbox";
    }
  | { kind: "channel"; channel: GettingStartedChannel };

export type GettingStartedStep = {
  id: string;
  title: string;
  /** One plain sentence telling the customer what to do. */
  instruction: string;
  route: GettingStartedRoute;
  /**
   * The completion source key. Keys used here:
   * - "assistant_created"
   * - "knowledge_added"
   * - "channel_connected:<channel>"
   * - "widget_installed"
   * - "leads_imported"
   * - "campaign_created"
   * - "call_campaign_created"
   * - "inbox_reviewed" (no API reports it yet, so it stays "Not checked yet")
   * - "consent_confirmed" (no API reports it, so it stays "Not checked yet")
   */
  source: string;
};

export type GettingStartedUseCase = {
  id: UseCaseId;
  title: string;
  /** One sentence on who this is for. */
  forWho: string;
  steps: readonly GettingStartedStep[];
  /** Honest limits of the product for this use case. Always present. */
  limits: string;
};

const ASSISTANT_STEP: GettingStartedStep = {
  id: "create-assistant",
  title: "Create your assistant",
  instruction: "Give it a name, and write what it should help customers with.",
  route: { kind: "page", to: "/studio/assistants" },
  source: "assistant_created",
};

const KNOWLEDGE_STEP: GettingStartedStep = {
  id: "add-knowledge",
  title: "Add your business details",
  instruction: "Upload a document with your prices, opening hours and common questions.",
  route: { kind: "page", to: "/studio/knowledge" },
  source: "knowledge_added",
};

const WEBSITE_CHAT_STEP: GettingStartedStep = {
  id: "connect-website-chat",
  title: "Turn on website chat",
  instruction: "Turn on website chat for your assistant so visitors can ask questions.",
  route: { kind: "channel", channel: "website-chat" },
  source: "channel_connected:website-chat",
};

const WIDGET_STEP: GettingStartedStep = {
  id: "install-widget",
  title: "Add the chat to your website",
  instruction:
    "Paste the one line of code on your site, then load a page to check that a visit shows up.",
  route: { kind: "page", to: "/studio/assistants" },
  source: "widget_installed",
};

/** The six use cases, in the order they are shown. */
export const USE_CASES: readonly GettingStartedUseCase[] = [
  {
    id: "small_business",
    title: "Small business",
    forWho: "Shops, clinics and service businesses that want help with common customer questions.",
    steps: [ASSISTANT_STEP, KNOWLEDGE_STEP, WEBSITE_CHAT_STEP, WIDGET_STEP],
    limits:
      "The assistant answers only from the documents you add. It will not answer questions those documents do not cover, and money or legal questions still need a person.",
  },
  {
    id: "website_owner",
    title: "Website owner",
    forWho: "Businesses that want answers on their own website and nowhere else.",
    steps: [ASSISTANT_STEP, KNOWLEDGE_STEP, WEBSITE_CHAT_STEP, WIDGET_STEP],
    limits:
      "The chat knows only what is in your documents. It will not answer unrelated questions, so keep your contact details easy to find on the site.",
  },
  {
    id: "whatsapp_business",
    title: "WhatsApp business",
    forWho: "Businesses that get most of their customer messages on WhatsApp.",
    steps: [
      ASSISTANT_STEP,
      KNOWLEDGE_STEP,
      {
        id: "connect-whatsapp",
        title: "Turn on WhatsApp",
        instruction:
          "Connect your WhatsApp Business number. The WhatsApp page lists what you need first.",
        route: { kind: "channel", channel: "whatsapp" },
        source: "channel_connected:whatsapp",
      },
      {
        id: "review-inbox",
        title: "Check replies in the inbox",
        instruction: "Open the inbox and read a few replies to make sure they are right.",
        route: { kind: "page", to: "/studio/inbox" },
        source: "inbox_reviewed",
      },
    ],
    limits:
      "Meta, not OraOne, approves your WhatsApp Business number and business name. The assistant replies only from your documents and will not answer unrelated questions.",
  },
  {
    id: "instagram_seller",
    title: "Instagram seller",
    forWho: "Sellers who take product questions in Instagram direct messages.",
    steps: [
      ASSISTANT_STEP,
      {
        id: "add-product-details",
        title: "Add your product list and shipping policy",
        instruction:
          "Upload a document with your products, prices, stock rules and shipping terms.",
        route: { kind: "page", to: "/studio/knowledge" },
        source: "knowledge_added",
      },
      {
        id: "connect-instagram",
        title: "Turn on Instagram",
        instruction:
          "Connect your Instagram professional account. The Instagram page lists the Meta steps first.",
        route: { kind: "channel", channel: "instagram" },
        source: "channel_connected:instagram",
      },
      {
        id: "review-inbox",
        title: "Check replies in the inbox",
        instruction: "Open the inbox and read a few replies to make sure they are right.",
        route: { kind: "page", to: "/studio/inbox" },
        source: "inbox_reviewed",
      },
    ],
    limits:
      "Instagram needs a professional account linked to a Facebook Page, and Meta decides whether that works. The assistant answers only from your product information and will not guess prices or stock.",
  },
  {
    id: "marketing",
    title: "Marketing",
    forWho: "Teams that send campaigns to contacts who have agreed to hear from them.",
    steps: [
      {
        id: "confirm-consent",
        title: "Confirm your contacts agreed to hear from you",
        instruction:
          "Check that every contact you plan to message agreed to receive marketing from you.",
        route: { kind: "page", to: "/studio/leads" },
        source: "consent_confirmed",
      },
      {
        id: "import-leads",
        title: "Import your contacts",
        instruction: "Upload a file of the contacts you want to reach.",
        route: { kind: "page", to: "/studio/leads" },
        source: "leads_imported",
      },
      {
        id: "create-campaign",
        title: "Create your first campaign",
        instruction:
          "Write the message, choose the contacts, and save it as a draft before you send.",
        route: { kind: "page", to: "/studio/marketing" },
        source: "campaign_created",
      },
    ],
    limits:
      "Campaigns go only to the contacts you import. OraOne does not check consent for you, and one campaign reaches at most 500 people.",
  },
  {
    id: "call_centre",
    title: "Call centre",
    forWho: "Teams that want an assistant to answer calls or work through a call list.",
    steps: [
      ASSISTANT_STEP,
      KNOWLEDGE_STEP,
      {
        id: "connect-voice",
        title: "Turn on AI Voice",
        instruction:
          "Connect your phone account and number. The AI Voice page lists what you need first.",
        route: { kind: "channel", channel: "voice" },
        source: "channel_connected:voice",
      },
      {
        id: "create-call-campaign",
        title: "Create a call campaign",
        instruction: "Pick the leads to call and save the campaign before you start it.",
        route: { kind: "page", to: "/studio/calls" },
        source: "call_campaign_created",
      },
    ],
    limits:
      "AI Voice needs your own telephony account and phone number. The assistant answers only from your documents and does not replace a person for emergencies or complaints.",
  },
];

export function isUseCaseId(value: unknown): value is UseCaseId {
  return typeof value === "string" && (USE_CASE_IDS as readonly string[]).includes(value);
}

export function getUseCase(id: UseCaseId): GettingStartedUseCase {
  const found = USE_CASES.find((useCase) => useCase.id === id);
  if (!found) throw new Error(`Unknown use case: ${id}`);
  return found;
}

export type StepStatus = "done" | "not_done" | "unknown";

export type StepProgress = {
  step: GettingStartedStep;
  status: StepStatus;
};

export type UseCaseProgress = {
  steps: readonly StepProgress[];
  doneCount: number;
  total: number;
  /** Whole percent of steps done, 0 to 100. Unknown steps count as not done. */
  percent: number;
};

/**
 * Progress for one use case.
 * - `completed`: source keys known to be done. Keys that match no step are ignored.
 * - `checked`: source keys the caller actually looked up. A step whose source is not completed
 *   and not checked is "unknown". When omitted, every source counts as checked.
 */
export function useCaseProgress(
  useCase: GettingStartedUseCase,
  completed: ReadonlySet<string>,
  checked?: ReadonlySet<string>,
): UseCaseProgress {
  const steps: StepProgress[] = useCase.steps.map((step) => {
    if (completed.has(step.source)) return { step, status: "done" };
    const wasChecked = checked === undefined || checked.has(step.source);
    return { step, status: wasChecked ? "not_done" : "unknown" };
  });
  const doneCount = steps.filter((item) => item.status === "done").length;
  const total = steps.length;
  const percent = total === 0 ? 0 : Math.round((doneCount / total) * 100);
  return { steps, doneCount, total, percent };
}

/** The first step that is not done. Unknown steps count as not done. Null when all are done. */
export function nextUndoneStep(progress: UseCaseProgress): GettingStartedStep | null {
  return progress.steps.find((item) => item.status !== "done")?.step ?? null;
}
