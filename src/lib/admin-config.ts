// Pure helpers for the admin configuration console. The server is the only source of
// truth: these functions only describe what the server returned, and never reveal more
// than it sent.

export type ConfigEnvironment = "local" | "production";

export type ConfigItem = {
  name: string;
  group: string;
  kind: "secret" | "plain";
  required: boolean;
  description: string;
  console_managed: boolean;
  is_set: boolean;
  source: "console" | "deployment" | "not_set" | "unknown";
  overridden: boolean;
  draft_pending?: boolean;
  masked_tail: string | null;
  value: string | null;
};

export type ConfigList = {
  environment: ConfigEnvironment;
  runtime_environment: ConfigEnvironment;
  deployment_visible: boolean;
  restart_required: boolean;
  draft_count?: number;
  groups: string[];
  items: ConfigItem[];
};

/** One side of a draft diff, as the server returned it. Secrets carry only a masked tail. */
export type DraftSide = {
  is_set: boolean;
  masked_tail: string | null;
  value: string | null;
};

export type DraftEntry = {
  name: string;
  group: string;
  kind: "secret" | "plain";
  action: "set" | "clear";
  readable: boolean;
  changed: boolean;
  before: DraftSide;
  after: DraftSide;
  updated_at: string | null;
};

export type DraftList = {
  environment: ConfigEnvironment;
  runtime_environment: ConfigEnvironment;
  deployment_visible: boolean;
  publish_required: boolean;
  drafts: DraftEntry[];
};

export type PublishChange = { name: string; change: "set" | "clear" };

export type PublishEvent = {
  id: string;
  published_at: string;
  published_by_email: string;
  reason: string;
  changes: PublishChange[];
};

export type PublishHistory = {
  environment: ConfigEnvironment;
  items: PublishEvent[];
};

export const REASON_MIN_LENGTH = 10;
export const REASON_MAX_LENGTH = 500;

/** What a row shows as its value. Secrets never show more than a masked tail. */
export function maskedDisplay(
  item: Pick<ConfigItem, "kind" | "is_set" | "masked_tail" | "value">,
): string {
  if (item.kind === "secret") {
    if (!item.is_set) return "Not set";
    return item.masked_tail ? `Set, ends in ${item.masked_tail}` : "Set";
  }
  if (!item.is_set) return "Not set";
  if (item.value === null || item.value === undefined) return "Hidden for this environment";
  return item.value;
}

export function sourceLabel(item: Pick<ConfigItem, "source" | "is_set">): string {
  switch (item.source) {
    case "console":
      return "Saved in console";
    case "deployment":
      return "Set in deployment";
    case "unknown":
      return "Not visible from this server";
    default:
      return item.is_set ? "Set" : "Not set";
  }
}

export function statusLabel(item: Pick<ConfigItem, "is_set" | "required">): {
  label: string;
  tone: "ok" | "missing" | "optional";
} {
  if (item.is_set) return { label: "Set", tone: "ok" };
  if (item.required) return { label: "Required, not set", tone: "missing" };
  return { label: "Not set", tone: "optional" };
}

export function matchesQuery(item: ConfigItem, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return (
    item.name.toLowerCase().includes(needle) ||
    item.group.toLowerCase().includes(needle) ||
    item.description.toLowerCase().includes(needle)
  );
}

export function groupItems(
  list: Pick<ConfigList, "groups" | "items">,
  query: string,
): { group: string; items: ConfigItem[] }[] {
  return list.groups
    .map((group) => ({
      group,
      items: list.items.filter((item) => item.group === group && matchesQuery(item, query)),
    }))
    .filter((section) => section.items.length > 0);
}

export type DiffRow = {
  name: string;
  kind: "secret" | "plain";
  action: "set" | "clear";
  actionLabel: string;
  before: string;
  after: string;
  changed: boolean;
  readable: boolean;
};

/**
 * Rows for the publish diff. Each side is rendered with the same masking rules as the
 * read model, so a secret shows a masked tail or "Set" and nothing longer.
 */
export function draftDiffRows(entries: DraftEntry[]): DiffRow[] {
  return entries.map((entry) => ({
    name: entry.name,
    kind: entry.kind,
    action: entry.action,
    actionLabel: entry.action === "clear" ? "Remove saved value" : "Change value",
    before: maskedDisplay({ kind: entry.kind, ...entry.before }),
    after:
      entry.action === "clear"
        ? "Removed (deployment value applies)"
        : entry.readable
          ? maskedDisplay({ kind: entry.kind, ...entry.after })
          : "Cannot be read. Discard and save again.",
    changed: entry.changed,
    readable: entry.readable,
  }));
}

/** Number of drafts whose value would actually change when published. */
export function changedDraftCount(entries: DraftEntry[]): number {
  return entries.filter((entry) => entry.changed).length;
}

/** Reasons a publish cannot be sent yet. An empty list means it can be sent. */
export function publishProblems(input: {
  environment: ConfigEnvironment;
  confirm: string;
  reason: string;
  draftCount: number;
}): string[] {
  const problems: string[] = [];
  if (input.draftCount === 0) problems.push("There are no draft changes to publish.");
  if (input.confirm !== input.environment)
    problems.push(`Type ${input.environment} exactly to confirm.`);
  const reason = input.reason.trim();
  if (reason.length < REASON_MIN_LENGTH)
    problems.push(`Give a reason of at least ${REASON_MIN_LENGTH} characters.`);
  if (reason.length > REASON_MAX_LENGTH)
    problems.push(`The reason must be ${REASON_MAX_LENGTH} characters or fewer.`);
  return problems;
}

export function publishChangeLabel(change: PublishChange): string {
  return change.change === "clear" ? `${change.name} (removed)` : change.name;
}

/** Returns the reasons a write cannot be sent yet. An empty list means it can be sent. */
export function writeProblems(input: {
  name: string;
  kind: ConfigItem["kind"];
  value: string;
  confirm: string;
  reason: string;
}): string[] {
  const problems: string[] = [];
  const value = input.value.trim();
  if (!value) problems.push("Enter a value, or remove the saved console value instead.");
  if (/[\r\n]/.test(input.value)) problems.push("The value must be on one line.");
  if (input.confirm !== input.name) problems.push(`Type ${input.name} exactly to confirm.`);
  const reason = input.reason.trim();
  if (reason.length < REASON_MIN_LENGTH)
    problems.push(`Give a reason of at least ${REASON_MIN_LENGTH} characters.`);
  if (reason.length > REASON_MAX_LENGTH)
    problems.push(`The reason must be ${REASON_MAX_LENGTH} characters or fewer.`);
  return problems;
}

export function removeProblems(input: { name: string; confirm: string; reason: string }): string[] {
  const problems: string[] = [];
  if (input.confirm !== input.name) problems.push(`Type ${input.name} exactly to confirm.`);
  const reason = input.reason.trim();
  if (reason.length < REASON_MIN_LENGTH)
    problems.push(`Give a reason of at least ${REASON_MIN_LENGTH} characters.`);
  if (reason.length > REASON_MAX_LENGTH)
    problems.push(`The reason must be ${REASON_MAX_LENGTH} characters or fewer.`);
  return problems;
}
