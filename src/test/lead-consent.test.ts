import { describe, expect, it } from "vitest";
import { importConsentLine } from "@/lib/lead-consent";

describe("importConsentLine", () => {
  it("returns the consent value and note for a CSV-imported lead", () => {
    expect(
      importConsentLine({
        consent: "granted",
        consent_source: "import_csv",
        consent_note: "Imported consent, confirm the source",
      }),
    ).toEqual({ value: "granted", note: "Imported consent, confirm the source" });
  });

  it("does not show the note for leads from other sources", () => {
    expect(
      importConsentLine({
        consent: "granted",
        consent_source: "widget",
        consent_note: "Imported consent, confirm the source",
      }),
    ).toBeNull();
    expect(importConsentLine({ consent: "granted" })).toBeNull();
  });

  it("returns null when the import has no usable note", () => {
    expect(importConsentLine({ consent_source: "import_csv" })).toBeNull();
    expect(importConsentLine({ consent_source: "import_csv", consent_note: "   " })).toBeNull();
    expect(importConsentLine(null)).toBeNull();
    expect(importConsentLine(undefined)).toBeNull();
  });

  it("falls back to unknown when the consent value is missing", () => {
    expect(
      importConsentLine({ consent_source: "import_csv", consent_note: "Confirm the source" }),
    ).toEqual({ value: "unknown", note: "Confirm the source" });
  });
});
