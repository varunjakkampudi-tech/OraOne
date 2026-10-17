import { describe, expect, it } from "vitest";
import {
  groupItems,
  maskedDisplay,
  removeProblems,
  sourceLabel,
  writeProblems,
  type ConfigItem,
} from "@/lib/admin-config";

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
