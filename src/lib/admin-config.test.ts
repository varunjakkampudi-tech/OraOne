import { describe, expect, it } from "vitest";
import {
  changedDraftCount,
  draftDiffRows,
  groupItems,
  maskedDisplay,
  publishChangeLabel,
  publishProblems,
  removeProblems,
  sourceLabel,
  writeProblems,
  type ConfigItem,
  type DiffRow,
  type DraftEntry,
} from "@/lib/admin-config";

function firstRow(entries: DraftEntry[]): DiffRow {
  const [row] = draftDiffRows(entries);
  if (row === undefined) throw new Error("expected one diff row");
  return row;
}

function draft(overrides: Partial<DraftEntry>): DraftEntry {
  return {
    name: "EXAMPLE_KEY",
    group: "Core",
    kind: "plain",
    action: "set",
    readable: true,
    changed: true,
    before: { is_set: false, masked_tail: null, value: null },
    after: { is_set: true, masked_tail: null, value: "DEBUG" },
    updated_at: null,
    ...overrides,
  };
}

function item(overrides: Partial<ConfigItem>): ConfigItem {
  return {
    name: "EXAMPLE_KEY",
    group: "Core",
    kind: "plain",
    required: false,
    description: "An example setting",
    console_managed: true,
    is_set: false,
    source: "not_set",
    overridden: false,
    masked_tail: null,
    value: null,
    ...overrides,
  };
}

describe("maskedDisplay", () => {
  it("shows only the masked tail for a set secret", () => {
    const text = maskedDisplay(
      item({ kind: "secret", is_set: true, masked_tail: "9876", value: null }),
    );
    expect(text).toBe("Set, ends in 9876");
    expect(text).not.toContain("sk-");
  });

  it("shows plain Set for a secret too short for a tail", () => {
    expect(maskedDisplay(item({ kind: "secret", is_set: true, masked_tail: null }))).toBe("Set");
  });

  it("shows Not set when nothing is configured", () => {
    expect(maskedDisplay(item({ kind: "secret", is_set: false }))).toBe("Not set");
    expect(maskedDisplay(item({ kind: "plain", is_set: false }))).toBe("Not set");
  });

  it("shows plain values only when the server returned them", () => {
    expect(maskedDisplay(item({ is_set: true, value: "DEBUG" }))).toBe("DEBUG");
    expect(maskedDisplay(item({ is_set: true, value: null }))).toBe("Hidden for this environment");
  });
});

describe("sourceLabel", () => {
  it("names where a value comes from without implying more", () => {
    expect(sourceLabel({ source: "console", is_set: true })).toBe("Saved in console");
    expect(sourceLabel({ source: "deployment", is_set: true })).toBe("Set in deployment");
    expect(sourceLabel({ source: "unknown", is_set: false })).toBe("Not visible from this server");
  });
});

describe("groupItems", () => {
  it("filters by name, group or description and drops empty groups", () => {
    const list = {
      groups: ["Core", "Widget"],
      items: [
        item({ name: "LOG_LEVEL", group: "Core", description: "Log detail" }),
        item({ name: "WIDGET_CDN_BASE", group: "Widget", description: "Script host" }),
      ],
    };
    expect(groupItems(list, "widget").map((g) => g.group)).toEqual(["Widget"]);
    expect(groupItems(list, "log").map((g) => g.group)).toEqual(["Core"]);
    expect(groupItems(list, "").map((g) => g.group)).toEqual(["Core", "Widget"]);
  });
});

describe("write validation", () => {
  it("requires an exact confirm and a reason of at least ten characters", () => {
    const problems = writeProblems({
      name: "LOG_LEVEL",
      kind: "plain",
      value: "DEBUG",
      confirm: "log_level",
      reason: "short",
    });
    expect(problems.some((p) => p.includes("LOG_LEVEL exactly"))).toBe(true);
    expect(problems.some((p) => p.includes("at least 10"))).toBe(true);
  });

  it("accepts a complete write", () => {
    expect(
      writeProblems({
        name: "LOG_LEVEL",
        kind: "plain",
        value: "DEBUG",
        confirm: "LOG_LEVEL",
        reason: "Investigating a sign-in issue",
      }),
    ).toEqual([]);
  });

  it("refuses multi-line values and empty values", () => {
    expect(
      writeProblems({
        name: "X_KEY",
        kind: "secret",
        value: "a\nb",
        confirm: "X_KEY",
        reason: "long enough reason",
      }),
    ).toContain("The value must be on one line.");
    expect(
      writeProblems({
        name: "X_KEY",
        kind: "secret",
        value: "   ",
        confirm: "X_KEY",
        reason: "long enough reason",
      }),
    ).toContain("Enter a value, or remove the saved console value instead.");
  });

  it("checks removal without a value", () => {
    expect(
      removeProblems({
        name: "LOG_LEVEL",
        confirm: "LOG_LEVEL",
        reason: "Clearing an old override",
      }),
    ).toEqual([]);
    expect(
      removeProblems({ name: "LOG_LEVEL", confirm: "", reason: "Clearing an old override" }),
    ).toHaveLength(1);
  });
});

describe("draftDiffRows", () => {
  it("masks a secret on both sides to a tail and never shows the full value", () => {
    const row = firstRow([
      draft({
        name: "OPENROUTER_API_KEY",
        kind: "secret",
        before: { is_set: true, masked_tail: "9876", value: null },
        after: { is_set: true, masked_tail: "5555", value: null },
      }),
    ]);
    expect(row.before).toBe("Set, ends in 9876");
    expect(row.after).toBe("Set, ends in 5555");
    expect(JSON.stringify(row)).not.toMatch(/sk-or/);
  });

  it("shows a short secret as plain Set, without any tail", () => {
    const row = firstRow([
      draft({
        kind: "secret",
        before: { is_set: false, masked_tail: null, value: null },
        after: { is_set: true, masked_tail: null, value: null },
      }),
    ]);
    expect(row.before).toBe("Not set");
    expect(row.after).toBe("Set");
  });

  it("shows plain values for local and a hidden note where the server withheld them", () => {
    const local = firstRow([
      draft({
        before: { is_set: true, masked_tail: null, value: "INFO" },
        after: { is_set: true, masked_tail: null, value: "DEBUG" },
      }),
    ]);
    expect(local.before).toBe("INFO");
    expect(local.after).toBe("DEBUG");

    const production = firstRow([
      draft({
        after: { is_set: true, masked_tail: null, value: null },
      }),
    ]);
    expect(production.after).toBe("Hidden for this environment");
  });

  it("describes a removal and a draft that cannot be read", () => {
    const removal = firstRow([
      draft({
        action: "clear",
        before: { is_set: true, masked_tail: null, value: "INFO" },
        after: { is_set: false, masked_tail: null, value: null },
      }),
    ]);
    expect(removal.actionLabel).toBe("Remove saved value");
    expect(removal.after).toBe("Removed (deployment value applies)");

    const unreadable = firstRow([draft({ readable: false })]);
    expect(unreadable.after).toBe("Cannot be read. Discard and save again.");
  });
});

describe("changedDraftCount", () => {
  it("counts only drafts whose value would actually change", () => {
    expect(
      changedDraftCount([draft({ changed: true }), draft({ name: "B", changed: false })]),
    ).toBe(1);
    expect(changedDraftCount([])).toBe(0);
  });
});

describe("publishProblems", () => {
  it("requires the typed environment name, a reason of ten characters and at least one draft", () => {
    const problems = publishProblems({
      environment: "production",
      confirm: "local",
      reason: "short",
      draftCount: 0,
    });
    expect(problems).toContain("There are no draft changes to publish.");
    expect(problems).toContain("Type production exactly to confirm.");
    expect(problems).toContain("Give a reason of at least 10 characters.");
  });

  it("accepts a complete publish, with surrounding spaces ignored in the reason", () => {
    expect(
      publishProblems({
        environment: "local",
        confirm: "local",
        reason: "  Rotating the key after review  ",
        draftCount: 2,
      }),
    ).toEqual([]);
  });

  it("refuses a reason that is too long", () => {
    const problems = publishProblems({
      environment: "local",
      confirm: "local",
      reason: "x".repeat(501),
      draftCount: 1,
    });
    expect(problems).toEqual(["The reason must be 500 characters or fewer."]);
  });
});

describe("publishChangeLabel", () => {
  it("names key changes without any value", () => {
    expect(publishChangeLabel({ name: "LOG_LEVEL", change: "set" })).toBe("LOG_LEVEL");
    expect(publishChangeLabel({ name: "LOG_LEVEL", change: "clear" })).toBe("LOG_LEVEL (removed)");
  });
});
