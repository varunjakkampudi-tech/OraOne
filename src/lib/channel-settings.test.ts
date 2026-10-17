import { describe, expect, it } from "vitest";
import { CHANNEL_SETTINGS, fieldError, validateChannelSettings } from "./channel-settings";
import { CHANNEL_PAGE_KEYS } from "./studio-os";

// The same boundary cases as backend/tests/test_channel_binding_setup.py, so the form and the
// server agree on what is valid.

describe("fieldError", () => {
  it("accepts an empty value, which clears the saved setting", () => {
    expect(fieldError("phone_number_id", "")).toBeNull();
    expect(fieldError("phone_number", "   ")).toBeNull();
  });

  it("accepts digits for WhatsApp and Instagram identifiers", () => {
    expect(fieldError("phone_number_id", "100200300400500")).toBeNull();
    expect(fieldError("instagram_account_id", "9988776655443")).toBeNull();
  });

  it.each([
    ["phone_number_id", "1002003004005x"],
    ["phone_number_id", "+100200300400"],
    ["phone_number_id", "1234"],
    ["phone_number_id", "+14155550123"],
    ["instagram_account_id", "acct-99887766"],
    ["instagram_account_id", "9".repeat(33)],
  ] as const)("refuses %s = %s", (key, value) => {
    expect(fieldError(key, value)).not.toBeNull();
  });

  it("accepts E.164 phone numbers for voice", () => {
    expect(fieldError("phone_number", "+14155550123")).toBeNull();
  });

  it.each(["4155550123", "+0123456789", "+1 415 555 0123", "+1415555012x"])(
    "refuses voice number %s",
    (value) => {
      expect(fieldError("phone_number", value)).not.toBeNull();
    },
  );
});

describe("validateChannelSettings", () => {
  it("returns the trimmed settings when the form is valid", () => {
    const result = validateChannelSettings(
      CHANNEL_SETTINGS.whatsapp,
      { phone_number_id: " 100200300400500 " },
      true,
    );
    expect(result).toEqual({ ok: true, settings: { phone_number_id: "100200300400500" } });
  });

  it("refuses to turn a channel on while its identifier is empty", () => {
    const result = validateChannelSettings(CHANNEL_SETTINGS.voice, { phone_number: "" }, true);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.phone_number).toContain("before turning this on");
    }
  });

  it("lets a channel be switched off with an empty identifier, and clears it", () => {
    const result = validateChannelSettings(
      CHANNEL_SETTINGS.instagram,
      { instagram_account_id: "" },
      false,
    );
    expect(result).toEqual({ ok: true, settings: { instagram_account_id: null } });
  });

  it("reports the field that is wrong and nothing else", () => {
    const result = validateChannelSettings(
      CHANNEL_SETTINGS.whatsapp,
      { phone_number_id: "abc" },
      false,
    );
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(Object.keys(result.errors)).toEqual(["phone_number_id"]);
      expect(result.message).toMatch(/fix the highlighted/i);
    }
  });

  it("saves only the switch for website chat, which has no identifier field", () => {
    expect(validateChannelSettings(CHANNEL_SETTINGS["website-chat"], {}, true)).toEqual({
      ok: true,
      settings: {},
    });
  });
});

describe("CHANNEL_SETTINGS", () => {
  it("covers every setup page", () => {
    expect(Object.keys(CHANNEL_SETTINGS).sort()).toEqual([...CHANNEL_PAGE_KEYS].sort());
  });

  it("never asks the user for a secret, token or key", () => {
    for (const spec of Object.values(CHANNEL_SETTINGS)) {
      for (const field of spec.fields) {
        expect(field.key).not.toMatch(/secret|token|key|password/i);
        expect(field.label).not.toMatch(/secret|token|api key|password/i);
      }
    }
  });

  it("only the website chat page offers a rotatable secret", () => {
    expect(CHANNEL_SETTINGS["website-chat"].hasSecret).toBe(true);
    expect(CHANNEL_SETTINGS.whatsapp.hasSecret).toBe(false);
  });
});
