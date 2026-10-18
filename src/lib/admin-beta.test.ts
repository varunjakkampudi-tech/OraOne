import { describe, expect, it } from "vitest";
import { cohortEmailProblem, organizationIdProblem, overrideValue } from "@/lib/admin-beta";
import { channelRows, formatCount, seriesMax } from "@/lib/admin-analytics";

describe("beta flag console rules", () => {
  it("maps choices to the API values", () => {
    expect(overrideValue("enable")).toBe(true);
    expect(overrideValue("disable")).toBe(false);
    expect(overrideValue("remove")).toBeNull();
  });

  it("requires a UUID organisation id", () => {
    expect(organizationIdProblem("")).not.toBeNull();
    expect(organizationIdProblem("not-a-uuid")).not.toBeNull();
    expect(organizationIdProblem("11111111-1111-4111-8111-111111111111")).toBeNull();
  });

  it("requires a plausible tester email", () => {
    expect(cohortEmailProblem("")).not.toBeNull();
    expect(cohortEmailProblem("tester")).not.toBeNull();
    expect(cohortEmailProblem("tester@example.com")).toBeNull();
  });
});

describe("analytics helpers", () => {
  it("sorts channel counts largest first with shares", () => {
    const rows = channelRows({ chat: 3, voice: 1, whatsapp: 0 });
    expect(rows.map((r) => r.channel)).toEqual(["chat", "voice"]);
    expect(rows[0]).toMatchObject({ label: "Web chat", count: 3, share: 75 });
  });

  it("keeps the bar scale defined for empty series", () => {
    expect(seriesMax([])).toBe(1);
    expect(seriesMax([{ date: "2026-10-01", count: 4 }])).toBe(4);
  });

  it("formats counts with separators", () => {
    expect(formatCount(1234567)).toBe("1,234,567");
  });
});
