import type { ChannelSettingsBody } from "@/lib/api/channels";
import type { ChannelPageKey } from "@/lib/studio-os";

// Settings the channel setup pages can save, and the rules that check them before a request is
// sent. The rules mirror backend/app/services/channels_service.py (validate_channel_settings) so
// the form explains a problem before the server has to refuse it. The server stays the authority.
// No secret is ever a field here: the server generates secrets and shows each one once.

export type SettingField = "phone_number_id" | "instagram_account_id" | "phone_number";

export type SettingFieldSpec = {
  key: SettingField;
  label: string;
  help: string;
  placeholder: string;
  inputMode: "numeric" | "tel";
};

export type ChannelSettingsSpec = {
  /** The channel key the channels API uses for this page. */
  apiKey: string;
  /** Fields this page saves. Empty when the page only turns a channel on or off. */
  fields: SettingFieldSpec[];
  /** Plain-language name for the switch that turns the channel on. */
  enableLabel: string;
  /** Help text under the switch. */
  enableHelp: string;
  /** Whether the page shows a server-issued secret that can be rotated. */
  hasSecret: boolean;
};

export const CHANNEL_SETTINGS: Record<ChannelPageKey, ChannelSettingsSpec> = {
  "website-chat": {
    apiKey: "sdk",
    fields: [],
    enableLabel: "Turn on app access",
    enableHelp:
      "Lets your own mobile or desktop app talk to this assistant. Your app signs each request with the secret below.",
    hasSecret: true,
  },
  whatsapp: {
    apiKey: "whatsapp",
    fields: [
      {
        key: "phone_number_id",
        label: "Phone number ID",
        help: "In Meta Business Manager, open WhatsApp, then API Setup. Copy the Phone number ID. It is digits only, not the phone number itself.",
        placeholder: "for example 100200300400500",
        inputMode: "numeric",
      },
    ],
    enableLabel: "Turn on WhatsApp for this assistant",
    enableHelp: "Messages sent to this WhatsApp number are answered by your assistant.",
    hasSecret: false,
  },
  instagram: {
    apiKey: "instagram",
    fields: [
      {
        key: "instagram_account_id",
        label: "Instagram account ID",
        help: "The numeric ID of the Instagram professional account that receives direct messages. It is digits only.",
        placeholder: "for example 9988776655443",
        inputMode: "numeric",
      },
    ],
    enableLabel: "Turn on Instagram for this assistant",
    enableHelp: "Direct messages to this Instagram account are answered by your assistant.",
    hasSecret: false,
  },
  voice: {
    apiKey: "voice",
    fields: [
      {
        key: "phone_number",
        label: "Business phone number",
        help: "Callers who dial this number reach your assistant. Use international format: a plus sign, the country code and the number, for example +14155550123.",
        placeholder: "+14155550123",
        inputMode: "tel",
      },
    ],
    enableLabel: "Turn on AI Voice for this assistant",
    enableHelp: "Calls to this number are answered by your assistant.",
    hasSecret: false,
  },
};

const DIGITS_RE = /^[0-9]{5,32}$/;
const E164_RE = /^\+[1-9][0-9]{6,14}$/;

/** Error text for one field value, or null when it is acceptable (an empty value is allowed). */
export function fieldError(key: SettingField, raw: string): string | null {
  const value = raw.trim();
  if (value === "") return null;
  if (key === "phone_number_id") {
    return DIGITS_RE.test(value)
      ? null
      : "Use digits only, 5 to 32 numbers. Do not paste the phone number.";
  }
  if (key === "instagram_account_id") {
    return DIGITS_RE.test(value) ? null : "Use digits only, 5 to 32 numbers.";
  }
  return E164_RE.test(value)
    ? null
    : "Use international format: a plus sign, then the country code and number, for example +14155550123.";
}

export type SettingsValidation =
  | { ok: true; settings: ChannelSettingsBody }
  | { ok: false; errors: Partial<Record<SettingField, string>>; message: string };

/**
 * Check the form values for one page before saving. Turning a channel on needs every field the
 * page saves, so the switch cannot be saved on an empty identifier.
 */
export function validateChannelSettings(
  spec: ChannelSettingsSpec,
  values: Partial<Record<SettingField, string>>,
  enabled: boolean,
): SettingsValidation {
  const errors: Partial<Record<SettingField, string>> = {};
  const settings: ChannelSettingsBody = {};

  for (const field of spec.fields) {
    const raw = (values[field.key] ?? "").trim();
    const problem = fieldError(field.key, raw);
    if (problem) {
      errors[field.key] = problem;
      continue;
    }
    if (enabled && raw === "") {
      errors[field.key] = `Add the ${field.label.toLowerCase()} before turning this on.`;
      continue;
    }
    settings[field.key] = raw === "" ? null : raw;
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors, message: "Fix the highlighted fields, then save again." };
  }
  return { ok: true, settings };
}
